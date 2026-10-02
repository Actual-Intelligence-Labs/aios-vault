"""Vault check: a short, plain-language checklist of whether everything works.

HOW TO RUN IT
  Ask Claude "is everything working?", or run this from the vault folder:
      sh .claude/hooks/run.sh doctor.py </dev/null

WHAT IT CHECKS
  - Python: the automatic helpers need 3.9 or newer; Sheet Geek needs 3.10+
  - Sheet Geek: the spreadsheet plugin is installed, with what it needs
  - Claude's memory: pointed at memory/claude/ inside this vault
  - Settings: the settings files are valid and wire up every helper
  - Each automatic helper (hook) actually runs, and how long it takes
  - Folder trust: Claude Code is allowed to run this folder's helpers

SAFETY
  Read only and safe to run any time. It changes nothing, sends nothing, and
  never prints anything from your files beyond yes-or-no answers and paths.
  It always exits normally. It does not read anything you type.
  Runs on Python 3.9 or newer, standard library only.
"""

import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time

HOOKS = {
    "SessionStart": ["session_pulse.py"],
    "UserPromptSubmit": ["auto_capture.py", "brand_guard.py", "vault_recall.py"],
    "Stop": ["brain_log.py"],
}
PLUGIN = "sheet-geek@sheet-geek"
OLD_HOOKS = ("auto-capture.sh", "brand-guard.sh")

results = []


def say(status, line, fix=""):
    results.append((status, line, fix))


def vault_root():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.dirname(here))


def config_dir():
    return os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")


def load_json(path):
    """(data, problem). problem is "missing", "invalid" or ""."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = fh.read()
    except OSError:
        return None, "missing"
    if not raw.strip():
        return {}, ""
    try:
        return json.loads(raw), ""
    except Exception:
        return None, "invalid"


def version_of(cmd):
    try:
        out = subprocess.run(cmd + ["-c", "import sys; print('%d.%d.%d' % sys.version_info[:3])"],
                             stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=10)
        v = out.stdout.strip()
        return tuple(int(x) for x in v.split(".")) if out.returncode == 0 and v else None
    except Exception:
        return None


def check_python():
    v = sys.version_info[:3]
    shown = ".".join(str(x) for x in v)
    if v >= (3, 10):
        say("ok", "Python " + shown + " runs the automatic helpers (" + sys.executable + ").")
    else:
        say("info", "Python " + shown + " runs the automatic helpers. Sheet Geek needs 3.10 or newer (see below).")


def sheet_geek_python():
    """The Python Sheet Geek will use. Its own launcher tries python3, then python, as the PATH finds
    them first, and uses the first one that is 3.10 or newer. Returns (command, version, what it found
    first), where command is None when neither will do."""
    on_mac = platform.system() == "Darwin"
    search = os.environ.get("VAULT_ORIGINAL_PATH") or os.environ.get("PATH")
    first_found = None
    for name in ("python3", "python"):
        p = shutil.which(name, path=search)
        if not p:
            continue
        cmd = [p]
        if on_mac and p.startswith("/usr/bin/"):
            # Apple's stand-in. Never call it (it can pop an install window);
            # ask the developer tools' Python directly, if they are installed.
            clt = "/Library/Developer/CommandLineTools/usr/bin/python3"
            if not os.path.exists(clt):
                if first_found is None:
                    first_found = (p, None)
                continue
            cmd = [clt]
        v = version_of(cmd)
        if first_found is None:
            first_found = (p, v)
        if v and v >= (3, 10):
            return cmd, v, first_found
    return None, None, first_found


def newer_python_elsewhere():
    """A Python 3.10 or newer that is installed but not the one Sheet Geek finds first, if any."""
    home = os.path.expanduser("~")
    spots = ["/opt/homebrew/bin/python3", "/usr/local/bin/python3",
             "/Library/Frameworks/Python.framework/Versions/Current/bin/python3",
             os.path.join(home, ".pyenv", "shims", "python3"), os.path.join(home, ".local", "bin", "python3")]
    for minor in range(15, 9, -1):
        found = shutil.which("python3." + str(minor))
        if found:
            spots.append(found)
    spots.append(sys.executable)
    local = os.environ.get("LOCALAPPDATA")
    if local:
        base = os.path.join(local, "Programs", "Python")
        try:
            for d in sorted(os.listdir(base), reverse=True):
                spots.append(os.path.join(base, d, "python.exe"))
        except OSError:
            pass
    seen = set()
    for p in spots:
        if not p or p in seen or not os.path.isfile(p):
            continue
        seen.add(p)
        if platform.system() == "Darwin" and p.startswith("/usr/bin/"):
            continue
        v = version_of([p])
        if v and v >= (3, 10):
            return p, v
    return None, None


def check_sheet_geek(root):
    data, problem = load_json(os.path.join(config_dir(), "plugins", "installed_plugins.json"))
    plugins = data.get("plugins", {}) if isinstance(data, dict) else {}
    installed = isinstance(plugins, dict) and bool(plugins.get(PLUGIN))
    if installed:
        entry = plugins.get(PLUGIN)
        ver = ""
        if isinstance(entry, list) and entry and isinstance(entry[0], dict):
            ver = str(entry[0].get("version") or "")
        say("ok", "Sheet Geek, the spreadsheet plugin, is installed" + (" (version " + ver + ")" if ver else "") + ".")
    else:
        say("fix", "Sheet Geek, the spreadsheet plugin, is not installed yet.",
            "Say \"install Sheet Geek\" and Claude installs it on your yes. By hand in VS Code: type /plugins in "
            "the Claude Code box, add Actual-Intelligence-Labs/sheet-geek#release on the Marketplaces tab if "
            "sheet-geek is not listed, then click Install on the Plugins tab and choose this project.")
    # This folder's settings switch Sheet Geek on; only .claude/settings.local.json can switch it off here.
    local, _ = load_json(os.path.join(root, ".claude", "settings.local.json"))
    if isinstance(local, dict):
        enabled = local.get("enabledPlugins")
        if isinstance(enabled, dict) and enabled.get(PLUGIN) is False:
            say("fix", "Sheet Geek is switched off for this folder in .claude/settings.local.json.",
                "Ask Claude to remove the sheet-geek line from that file, then reload the window.")
    cmd, v, first = sheet_geek_python()
    if not cmd:
        other, other_v = newer_python_elsewhere()
        if first and first[1]:
            seen = "python3 on your PATH is " + ".".join(str(x) for x in first[1]) + " (" + first[0] + ")"
        elif first:
            seen = "python3 on your PATH is Apple's stand-in (" + first[0] + "), which is not a working Python"
        else:
            seen = "there is no python3 or python on your PATH"
        if other:
            fix = ("Nothing new needs installing: put the folder of the newer Python (" + os.path.dirname(other)
                   + ") ahead of the others on your PATH, then quit VS Code completely and open it again. ")
            for prefix in ("/opt/homebrew", "/usr/local"):
                if other.startswith(prefix + "/") and os.path.isfile(prefix + "/bin/brew"):
                    fix += ("With Homebrew on a Mac that means adding the line  eval \"$(" + prefix
                            + "/bin/brew shellenv)\"  to the file ~/.zprofile. ")
                    break
            fix += "Claude can do this for you on your yes."
            say("fix", "Sheet Geek cannot run yet: it uses the first python3 (or python) on your PATH, and "
                + seen + ". A newer Python, " + ".".join(str(x) for x in other_v) + ", is already installed at "
                + other + ".", fix)
        else:
            say("fix", "Sheet Geek cannot run yet: it needs Python 3.10 or newer, and " + seen + ".",
                "Install Python 3.10 or newer (python.org has a free installer, or on a Mac with Homebrew: "
                "brew install python), then quit VS Code completely and open it again. Claude can walk you "
                "through it.")
        return
    try:
        out = subprocess.run(cmd + ["-c", "import openpyxl"], stdin=subprocess.DEVNULL,
                             capture_output=True, text=True, timeout=20)
        has_openpyxl = out.returncode == 0
    except Exception:
        has_openpyxl = False
    shown = ".".join(str(x) for x in v)
    if has_openpyxl:
        say("ok", "Sheet Geek has what it needs: Python " + shown + " and the openpyxl library.")
    else:
        say("fix", "Sheet Geek needs the openpyxl library, which is missing for Python " + shown + ".",
            "Claude can install it on your yes, or run: \"" + cmd[0] + "\" -m pip install --user openpyxl")


def check_memory(root):
    want = os.path.join(root, "memory", "claude")
    local_path = os.path.join(root, ".claude", "settings.local.json")
    local, problem = load_json(local_path)
    fix = ("Setup does this for you. By hand: put  \"autoMemoryDirectory\": \"" + want + "\"  in "
           ".claude/settings.local.json, then reload the window (VS Code: Command Palette, Developer: Reload "
           "Window).")
    if problem == "invalid":
        say("fix", ".claude/settings.local.json is not valid JSON, so Claude Code ignores everything in it.",
            "Ask Claude to repair it, keeping the settings already in it.")
    elif os.environ.get("CLAUDE_CODE_DISABLE_AUTO_MEMORY", "").lower() in ("1", "true", "yes") or (
            isinstance(local, dict) and local.get("autoMemoryEnabled") is False):
        say("info", "Claude's own memory is switched off on purpose, so where it lives does not matter.")
    else:
        have = str(local.get("autoMemoryDirectory") or "") if isinstance(local, dict) else ""
        if not have:
            say("fix", "Claude's memory is not pointed at this vault yet, so what it learns is saved elsewhere.", fix)
        elif os.path.realpath(os.path.expanduser(have)) != os.path.realpath(want):
            say("fix", "Claude's memory points at " + have + ", not at this vault (was the folder moved?).", fix)
        else:
            say("ok", "Claude's memory lives in this vault, in memory/claude/.")
    index = os.path.join(want, "MEMORY.md")
    if not os.path.isfile(index):
        say("fix", "memory/claude/MEMORY.md, the index of Claude's memory, is missing.",
            "Say \"update my vault\" to add it.")
    else:
        try:
            size = os.path.getsize(index)
            with open(index, "r", encoding="utf-8", errors="ignore") as fh:
                lines = fh.read().count("\n")
        except OSError:
            size, lines = 0, 0
        if size > 22500 or lines > 180:
            say("fix", "Claude's memory index is near its load limit (" + str(lines) + " of 200 lines, "
                + str(size // 1000) + " of 25 KB). Anything past the limit never loads.",
                "Ask Claude to compact memory/claude/MEMORY.md: one short line per note.")


def check_settings(root):
    path = os.path.join(root, ".claude", "settings.json")
    data, problem = load_json(path)
    if problem:
        say("fix", ".claude/settings.json is " + ("missing" if problem == "missing" else "not valid JSON")
            + ", so none of the automatic helpers run.", "Say \"update my vault\" to restore it.")
        return
    hooks = data.get("hooks", {}) if isinstance(data, dict) else {}
    missing = []
    for event, scripts in HOOKS.items():
        cmds = []
        for group in hooks.get(event, []) if isinstance(hooks, dict) else []:
            for h in group.get("hooks", []) if isinstance(group, dict) else []:
                if isinstance(h, dict):
                    cmds.append(str(h.get("command") or ""))
        for s in scripts:
            if not any("run.sh" in c and s in c for c in cmds):
                missing.append(s)
    if missing:
        say("fix", "The settings do not switch on these helpers: " + ", ".join(missing) + ".",
            "Say \"update my vault\" to restore the settings file.")
    else:
        say("ok", "The settings file is valid and switches on all five automatic helpers.")
    markets = data.get("extraKnownMarketplaces", {}) if isinstance(data, dict) else {}
    enabled = data.get("enabledPlugins", {}) if isinstance(data, dict) else {}
    if not (isinstance(markets, dict) and "sheet-geek" in markets
            and isinstance(enabled, dict) and enabled.get(PLUGIN)):
        say("fix", "The settings no longer offer Sheet Geek for this folder.",
            "Say \"update my vault\" to restore the settings file.")
    if isinstance(data, dict) and "autoMemoryDirectory" in data:
        say("info", "autoMemoryDirectory in .claude/settings.json is ignored by Claude Code; it only works in "
                    ".claude/settings.local.json.")
    for name in OLD_HOOKS:
        if os.path.exists(os.path.join(root, ".claude", "hooks", name)):
            say("info", "An old helper from the first version is still here and no longer used: .claude/hooks/"
                + name + ". It is safe to delete.")


def fake_transcript(tmp):
    """A two-line transcript: the owner asks, the AI drafts an email. Nothing logged."""
    now = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(time.time() + 5))
    path = os.path.join(tmp, "check.jsonl")
    lines = [
        {"type": "user", "timestamp": now, "message": {"role": "user", "content": "email Sam the recap"}},
        {"type": "assistant", "timestamp": now, "message": {"role": "assistant", "content": [
            {"type": "tool_use", "id": "check", "name": "mcp__mail__create_draft",
             "input": {"to": "sam@example.com", "subject": "Recap"}}]}},
    ]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(json.dumps(x) for x in lines) + "\n")
    return path


def check_hooks(root):
    run_sh = os.path.join(root, ".claude", "hooks", "run.sh")
    if not os.path.isfile(run_sh):
        say("fix", ".claude/hooks/run.sh is missing, so no automatic helper can start.",
            "Say \"update my vault\" to restore it.")
        return
    tmp = tempfile.mkdtemp(prefix="vault-check-")
    try:
        transcript = fake_transcript(tmp)
        cases = [
            ("session_pulse.py", "session-start briefing",
             {"hook_event_name": "SessionStart", "session_id": "vault-check", "source": "startup"}, "context"),
            ("auto_capture.py", "loose-thought filing",
             {"hook_event_name": "UserPromptSubmit", "prompt": "capture: vault check"}, "context"),
            ("brand_guard.py", "brand and voice loading",
             {"hook_event_name": "UserPromptSubmit", "prompt": "make me a one pager"}, "context"),
            ("vault_recall.py", "name lookup",
             {"hook_event_name": "UserPromptSubmit", "prompt": "who is Zzyzx Quell?"}, "context"),
            ("brain_log.py", "end-of-reply brain log",
             {"hook_event_name": "Stop", "stop_hook_active": False, "transcript_path": transcript}, "block"),
        ]
        env = dict(os.environ)
        env["CLAUDE_PROJECT_DIR"] = root
        for script, what, payload, expect in cases:
            if not os.path.isfile(os.path.join(root, ".claude", "hooks", script)):
                say("fix", "The " + what + " helper (" + script + ") is missing.",
                    "Say \"update my vault\" to restore it.")
                continue
            start = time.time()
            try:
                out = subprocess.run(["sh", run_sh, script], input=json.dumps(payload), capture_output=True,
                                     text=True, timeout=30, env=env, cwd=root)
                took = time.time() - start
                text = out.stdout.strip()
                parsed = json.loads(text) if text else None
            except subprocess.TimeoutExpired:
                say("fix", "The " + what + " helper (" + script + ") took over 30 seconds and would be cut off.",
                    "Ask Claude to look into it: the vault may be very large.")
                continue
            except Exception:
                parsed, took, text = None, time.time() - start, "?"
            ok = False
            if isinstance(parsed, dict):
                if expect == "context":
                    ok = bool((parsed.get("hookSpecificOutput") or {}).get("additionalContext"))
                else:
                    ok = parsed.get("decision") == "block"
            if not text:
                say("fix", "The " + what + " helper (" + script + ") ran but said nothing.",
                    "Usually this means no usable Python. Check the Python line above.")
            elif not ok:
                say("fix", "The " + what + " helper (" + script + ") gave an unexpected answer.",
                    "Ask Claude to look into .claude/hooks/" + script + ".")
            elif took > 8:
                say("fix", "The " + what + " helper (" + script + ") works but is slow (" + "%.1f" % took
                    + " s; the limit is 10 s).", "Ask Claude to look into it: the vault may be very large.")
            else:
                say("ok", "The " + what + " helper (" + script + ") works (" + "%.2f" % took + " s).")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def check_trust(root):
    path = os.environ.get("CLAUDE_CONFIG_DIR")
    path = os.path.join(path, ".claude.json") if path else os.path.join(os.path.expanduser("~"), ".claude.json")
    data, problem = load_json(path)
    projects = data.get("projects", {}) if isinstance(data, dict) else {}
    if not isinstance(projects, dict):
        projects = {}
    here = os.path.realpath(root)
    while True:
        entry = projects.get(here)
        if isinstance(entry, dict) and entry.get("hasTrustDialogAccepted"):
            say("ok", "This folder is trusted, so Claude Code lets its helpers run.")
            return
        parent = os.path.dirname(here)
        if parent == here:
            break
        here = parent
    say("info", "Could not confirm that this folder is trusted.",
        "If the helpers stay quiet, close and reopen Claude Code in this folder and answer yes when it asks "
        "whether you trust the folder.")


def check_layout(root):
    for rel, what in (("context/who-and-what.md", "the index of people, companies, projects and tools"),
                      ("context/where-files-live.md", "the map of where your files go")):
        if not os.path.isfile(os.path.join(root, rel)):
            say("fix", rel + " (" + what + ") is missing.", "Say \"update my vault\" to add it.")


def main():
    root = vault_root()
    try:
        check_python()
    except Exception as exc:
        say("info", "One check could not finish (" + type(exc).__name__ + ").")
    for step in (check_sheet_geek, check_memory, check_settings, check_layout, check_hooks, check_trust):
        try:
            step(root)
        except Exception as exc:
            say("info", "One check could not finish (" + type(exc).__name__ + ").")
    print("Vault check for " + root + " (reads only, changes nothing)")
    print("")
    for status, line, fix in results:
        print("[" + status + "] " + line)
        if fix:
            print("      " + fix)
    fixes = sum(1 for s, _, _ in results if s == "fix")
    print("")
    print("All good." if not fixes else str(fixes) + " thing" + ("s" if fixes != 1 else "") + " to fix.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("[info] The vault check itself hit a problem and stopped early.")
