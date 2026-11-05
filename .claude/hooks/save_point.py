"""Save point: when a Claude Code session ends, save the vault's changes in git.

WHAT IT DOES
  It is OFF until the owner turns it on. "Optimize my vault" offers to turn it
  on, by creating an empty file named .claude/save-points-on. With that file in
  place, and the vault folder being a git repository, each session end makes
  one local save (a git commit) of whatever changed, so any note can be
  brought back later as it was.
  Local only: it never pushes, never uploads, and never touches a remote.

  It leaves out:
    - files git is told to ignore (.gitignore)
    - files that look like they hold a secret: by name (.env, *.pem, *.key,
      credentials.json and the like) or by content (text shaped like an API
      key, a token or a private key)
    - files over 5 MB
  Files left out stay on disk, untouched, and are simply not saved. Their
  names (never their content) go in .claude/state/save-point.json, so the
  vault check can mention them.

  It does nothing when git is missing, when another git job is running, when
  the owner has changes staged by hand, or when nothing changed. To turn it
  off, delete .claude/save-points-on.

SAFETY
  It never pushes, never deletes a file, never rewrites history, and never
  changes git settings. If anything goes wrong it puts git's staging area
  back the way it was, prints nothing and exits normally.
  Runs on Python 3.9 or newer, standard library only, through run.sh.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

FLAG = os.path.join(".claude", "save-points-on")
MAX_BYTES = 5 * 1024 * 1024
SCAN_BYTES = 1024 * 1024
SECRET_NAME = re.compile(
    r"""(?ix)(?:^|/)(?:
        \.env | \.env\.[^/]+ | [^/]+\.env | \.envrc
      | [^/]+\.(?:pem|key|p12|pfx|keystore|jks|ppk|token)
      | id_(?:rsa|dsa|ecdsa|ed25519)(?:_sk)?
      | client_secret[^/]*\.json | [^/]*credentials[^/]*\.json | [^/]*service[-_]account[^/]*\.json | token\.json
      | \.netrc | \.pgpass | \.git-credentials | \.pypirc
      | secrets?\.(?:json|ya?ml|toml|ini|env)
    )$""")
SAFE_NAME = re.compile(r"(?i)\.(?:example|sample|template|dist|md|pub)$")
SECRET_TEXT = re.compile(
    r"GOCSPX-[A-Za-z0-9_-]{10,}|sk-ant-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{30,}|gh[ousr]_[A-Za-z0-9]{30,}"
    r"|github_pat_[A-Za-z0-9_]{30,}|glpat-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|xox[abpre]-[A-Za-z0-9-]{10,}"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----|\b[sr]k_(?:live|test)_[A-Za-z0-9]{20,}|\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}"
    r"|AIza[0-9A-Za-z_-]{35}|ya29\.[0-9A-Za-z_-]{20,}|1//0[0-9A-Za-z_-]{30,}|\bhf_[A-Za-z0-9]{30,}"
    r"|\bnpm_[A-Za-z0-9]{36}|[\"']?(?:refresh_token|client_secret|private_key)[\"']?\s*[:=]\s*[\"'][^\"'\s]{12,}")
BUSY = ("index.lock", "rebase-merge", "rebase-apply", "MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "BISECT_LOG")


def vault_root():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.dirname(here))


def find_git():
    """A git that runs without popping up an install window, or None."""
    path = shutil.which("git")
    if sys.platform == "darwin" and (not path or os.path.realpath(path) == "/usr/bin/git"):
        # /usr/bin/git on a Mac is Apple's stand-in: without the developer tools it opens an install window.
        for p in ("/Library/Developer/CommandLineTools/usr/bin/git",
                  "/Applications/Xcode.app/Contents/Developer/usr/bin/git"):
            if os.access(p, os.X_OK):
                return p
        return None
    return path


class Git(object):
    def __init__(self, exe, root):
        self.exe, self.root = exe, root

    def run(self, *args, **kw):
        env = dict(os.environ)
        env["GIT_TERMINAL_PROMPT"] = "0"
        env.pop("GIT_DIR", None)
        env.pop("GIT_WORK_TREE", None)
        return subprocess.run([self.exe, "-C", self.root] + list(args), stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=kw.get("timeout", 10), env=env)

    def out(self, *args):
        r = self.run(*args)
        return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else None


def looks_secret(root, rel):
    name = rel.replace("\\", "/")
    if SECRET_NAME.search(name) and not SAFE_NAME.search(name):
        return True
    try:
        with open(os.path.join(root, rel), "rb") as fh:
            head = fh.read(SCAN_BYTES)
    except OSError:
        return False
    return bool(SECRET_TEXT.search(head.decode("utf-8", "replace")))


def write_state(root, info):
    folder = os.environ.get("VAULT_HOOKS_STATE_DIR") or os.path.join(root, ".claude", "state")
    if not os.path.isdir(folder):
        os.makedirs(folder, mode=0o700, exist_ok=True)
        ignore = os.path.join(folder, ".gitignore")
        if not os.path.exists(ignore):
            with open(ignore, "w", encoding="utf-8") as fh:
                fh.write("# Machine state for the vault's automatic helpers. Never worth keeping in git.\n*\n")
    fd, tmp = tempfile.mkstemp(dir=folder, prefix=".save-point-")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(info, fh)
    os.replace(tmp, os.path.join(folder, "save-point.json"))


def save(root):
    """Make the save point. Returns a small record of what happened."""
    if not os.path.isfile(os.path.join(root, FLAG)):
        return None   # off: say nothing, write nothing
    exe = find_git()
    if not exe:
        return {"result": "not saved: git is not installed"}
    g = Git(exe, root)
    top = g.out("rev-parse", "--show-toplevel")
    if top is None or os.path.realpath(top.strip()) != os.path.realpath(root):
        return {"result": "not saved: this vault folder is not the top of a git repository"}
    git_dir = (g.out("rev-parse", "--absolute-git-dir") or "").strip()
    if not git_dir or any(os.path.exists(os.path.join(git_dir, x)) for x in BUSY):
        return {"result": "not saved: another git job was running"}
    if g.run("symbolic-ref", "-q", "HEAD").returncode != 0:
        return {"result": "not saved: git is not on a branch"}
    has_head = g.run("rev-parse", "--verify", "-q", "HEAD").returncode == 0
    if g.run("diff", "--cached", "--quiet").returncode != 0:
        return {"result": "not saved: some changes were already staged by hand"}
    status = g.out("status", "--porcelain")
    if status is None:
        return {"result": "not saved: git could not read the folder"}
    if not status.strip():
        return {"result": "nothing changed"}

    def unstage(paths=None):
        if has_head:
            g.run("reset", "-q", "--", *(paths or []))
        else:
            g.run("rm", "-r", "--cached", "-q", "--ignore-unmatch", "--", *(paths or ["."]))

    try:
        if g.run("add", "-A", "--", ".", timeout=30).returncode != 0:
            unstage()
            return {"result": "not saved: git could not stage the changes"}
        listed = g.out("diff", "--cached", "--name-only", "-z", "--diff-filter=ACMRT") or ""
        skipped = []
        for rel in [x for x in listed.split("\0") if x]:
            full = os.path.join(root, rel)
            too_big = os.path.isfile(full) and os.path.getsize(full) > MAX_BYTES
            # A packed save point from "optimize my vault" is already a copy; it never goes into git.
            if too_big or looks_secret(root, rel) or rel.startswith("archives/save-points/"):
                skipped.append(rel)
        for k in range(0, len(skipped), 100):
            unstage(skipped[k:k + 100])
        if g.run("diff", "--cached", "--quiet").returncode == 0:
            return {"result": "nothing to save", "left_out": skipped[:50]}
        args = []
        if not (g.out("config", "user.email") or "").strip():
            args = ["-c", "user.name=Vault save point", "-c", "user.email=save-point@vault.local"]
        msg = "Save point " + time.strftime("%Y-%m-%d %H:%M") + " (local only, made when a session ended)"
        if g.run(*(args + ["commit", "-q", "-m", msg]), timeout=30).returncode != 0:
            unstage()
            return {"result": "not saved: git refused the save", "left_out": skipped[:50]}
        return {"result": "saved", "left_out": skipped[:50]}
    except Exception:
        try:
            unstage()
        except Exception:
            pass
        raise


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return   # input it cannot read: do nothing
    if not isinstance(data, dict):
        return
    tp = str(data.get("transcript_path") or "").replace("\\", "/")
    if data.get("agent_id") or "/subagents/" in tp:
        return
    root = vault_root()
    info = save(root)
    if info is not None:
        info["time"] = time.strftime("%Y-%m-%d %H:%M")
        write_state(root, info)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
