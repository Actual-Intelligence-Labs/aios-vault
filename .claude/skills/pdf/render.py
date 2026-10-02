#!/usr/bin/env python3
"""Render a designed HTML file to a PDF using headless Chrome.

No third-party packages. If you have Chrome (or Edge, Brave, or Chromium)
installed, this works.

    python3 .claude/skills/pdf/render.py outputs/my-doc.html
    python3 .claude/skills/pdf/render.py outputs/my-doc.html -o ~/Desktop/my-doc.pdf

What it does, in order:
  1. Finds a Chrome-family browser on this machine.
  2. Copies the design system stylesheet (and any theme files) next to the
     source HTML, so a plain <link href="base.css"> resolves.
  3. Refuses to render if the HTML points at a local image that is not there,
     because a missing image renders as a silent broken box in the PDF.
  4. Prints the page to PDF with headless Chrome and reports the path.
"""

import argparse
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"

# How long to wait for the PDF to appear before giving up, in seconds.
RENDER_TIMEOUT = 120

# ----------------------------------------------------------------------------
# 1. Find a browser
# ----------------------------------------------------------------------------

MAC_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
]

LINUX_BINARIES = [
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
    "microsoft-edge",
    "microsoft-edge-stable",
    "brave-browser",
]

WINDOWS_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
]

NO_BROWSER_MESSAGE = """Could not find a Chrome-family browser to render with.

This script needs one of: Google Chrome, Chrome Canary, Chromium,
Microsoft Edge, or Brave.

Fix it by installing Google Chrome: https://www.google.com/chrome/
Then run the same command again. Nothing else needs to be installed.

If a browser IS installed somewhere unusual, point at it directly:
    CHROME_PATH="/path/to/the/browser" python3 render.py yourfile.html
"""


def find_browser():
    """Return the path to a usable Chrome-family browser, or None."""
    override = os.environ.get("CHROME_PATH")
    if override and Path(override).exists():
        return override

    for candidate in MAC_CANDIDATES + WINDOWS_CANDIDATES:
        if Path(candidate).exists():
            return candidate

    for name in LINUX_BINARIES:
        found = shutil.which(name)
        if found:
            return found

    # Last resort: some systems expose these on PATH under other names.
    for name in ("chrome", "chrome.exe", "msedge", "msedge.exe"):
        found = shutil.which(name)
        if found:
            return found

    return None


# ----------------------------------------------------------------------------
# 2. Put the stylesheet next to the HTML
# ----------------------------------------------------------------------------


def copy_assets(dest_dir: Path) -> None:
    """Copy base.css and any assets/themes/*.css next to the source HTML.

    A failure here is not fatal. A document can carry its whole design in an
    inline <style> block, so we warn and keep going.
    """
    try:
        base = ASSETS / "base.css"
        if base.exists():
            target = dest_dir / "base.css"
            if base.resolve() != target.resolve():
                shutil.copyfile(base, target)

        themes = ASSETS / "themes"
        if themes.is_dir():
            for css in sorted(themes.glob("*.css")):
                target = dest_dir / css.name
                if css.resolve() != target.resolve():
                    shutil.copyfile(css, target)
    except Exception as exc:  # noqa: BLE001 - never abort the render for this
        print(f"note: could not copy stylesheets ({exc}). "
              f"Continuing, inline styles will still apply.", file=sys.stderr)


# ----------------------------------------------------------------------------
# 3. Missing-image guard
# ----------------------------------------------------------------------------

IMG_SRC_RE = re.compile(r"""<img\b[^>]*?\bsrc\s*=\s*(?:"([^"]*)"|'([^']*)')""",
                        re.IGNORECASE | re.DOTALL)

COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)

REMOTE_PREFIXES = ("http://", "https://", "data:", "//")


def check_images(html_path: Path) -> list:
    """Return the local image paths the HTML references that do not exist.

    Remote URLs and data URIs are skipped. A local file:// URL is resolved and
    checked like any other local path. This is the only hard failure the guard
    has, because a missing image does not error at render time. It quietly
    becomes a broken grey box in the finished PDF.
    """
    try:
        html = html_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    # Commented-out example markup never renders, so it must not be checked.
    html = COMMENT_RE.sub("", html)

    missing = []
    base_dir = html_path.parent

    for match in IMG_SRC_RE.finditer(html):
        src = (match.group(1) or match.group(2) or "").strip()
        if not src:
            continue

        lowered = src.lower()
        if lowered.startswith(REMOTE_PREFIXES):
            continue

        if lowered.startswith("file://"):
            # file:///abs/path keeps its leading slash, which is what we want.
            candidate = Path(src[7:])
        else:
            candidate = Path(src)
            if not candidate.is_absolute():
                candidate = base_dir / candidate

        # Drop any ?query or #fragment the path may carry.
        cleaned = Path(str(candidate).split("?")[0].split("#")[0])

        if not cleaned.exists():
            missing.append(src)

    return missing


# ----------------------------------------------------------------------------
# 4. Render
# ----------------------------------------------------------------------------


def _stop(proc) -> None:
    """Shut the browser down, politely first, then firmly."""
    if proc.poll() is not None:
        return
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except Exception:
        try:
            proc.terminate()
        except Exception:
            pass
    for _ in range(20):
        if proc.poll() is not None:
            return
        time.sleep(0.1)
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def render(browser: str, html_path: Path, pdf_path: Path) -> int:
    """Print the HTML to PDF with headless Chrome. Returns an exit code.

    Some Chrome builds write the PDF and then keep running (a background
    updater or sync service holds the process open). So we do not wait for the
    browser to exit. We wait for the file to appear and stop growing, then
    shut the browser down ourselves.
    """
    profile_dir = tempfile.mkdtemp(prefix="pdf-render-profile-")
    log_file = Path(profile_dir) / "browser.log"

    if pdf_path.exists():
        try:
            pdf_path.unlink()
        except Exception:
            pass

    cmd = [
        browser,
        "--headless=new",
        "--disable-gpu",
        # A throwaway profile means this works even while Chrome is already open.
        f"--user-data-dir={profile_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        "--disable-background-networking",
        "--disable-component-update",
        "--disable-sync",
        "--hide-scrollbars",
        "--force-color-profile=srgb",
        # Give webfonts and layout time to settle before the snapshot.
        "--virtual-time-budget=8000",
        # Chrome's own header and footer (URL, page numbers, date) would print
        # over the design. Off.
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path}",
        html_path.as_uri(),
    ]

    try:
        with open(log_file, "wb") as log:
            proc = subprocess.Popen(
                cmd,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )

        deadline = time.time() + RENDER_TIMEOUT
        last_size = -1
        stable_checks = 0

        while time.time() < deadline:
            if pdf_path.exists():
                size = pdf_path.stat().st_size
                if size > 0 and size == last_size:
                    stable_checks += 1
                    if stable_checks >= 2:
                        break
                else:
                    stable_checks = 0
                last_size = size
            elif proc.poll() is not None:
                # Browser exited without producing anything.
                break
            time.sleep(0.3)

        _stop(proc)

        if pdf_path.exists() and pdf_path.stat().st_size > 0:
            return 0

        print("Render failed. No PDF was produced.", file=sys.stderr)
        try:
            tail = log_file.read_text(errors="replace").strip().splitlines()[-15:]
        except Exception:
            tail = []
        if tail:
            print("Browser output (last lines):", file=sys.stderr)
            for line in tail:
                print(f"  {line}", file=sys.stderr)
        else:
            print("The browser produced no output. Check that the HTML file "
                  "opens in a normal browser window.", file=sys.stderr)
        return 1

    finally:
        shutil.rmtree(profile_dir, ignore_errors=True)


# ----------------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render a designed HTML file to PDF using headless Chrome.")
    parser.add_argument("html", help="Path to the source HTML file.")
    parser.add_argument(
        "-o", "--output",
        help="Path for the PDF. Defaults to the HTML path with a .pdf extension.")
    args = parser.parse_args()

    html_path = Path(args.html).expanduser().resolve()
    if not html_path.exists():
        print(f"No such file: {html_path}", file=sys.stderr)
        return 1

    pdf_path = (Path(args.output).expanduser().resolve()
                if args.output else html_path.with_suffix(".pdf"))
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    browser = find_browser()
    if not browser:
        print(NO_BROWSER_MESSAGE, file=sys.stderr)
        return 1

    copy_assets(html_path.parent)

    missing = check_images(html_path)
    if missing:
        print("Stopping before render. The document points at image files "
              "that are not on disk:", file=sys.stderr)
        for src in missing:
            print(f"  missing: {src}", file=sys.stderr)
        print("\nA missing image does not throw an error, it prints as a "
              "broken grey box in the finished PDF. Fix the path (use an "
              "absolute file:/// path, or put the image next to the HTML) "
              "and run this again.", file=sys.stderr)
        return 2

    code = render(browser, html_path, pdf_path)
    if code == 0:
        print(pdf_path)
    return code


if __name__ == "__main__":
    sys.exit(main())
