"""Make a save point before the optimize-vault skill changes anything, so every
change can be undone.

  python3 save_point.py --vault .            says what it would do, and how big
                                             the save point will be (changes nothing)
  python3 save_point.py --vault . --apply    makes the save point
  python3 save_point.py --vault . --done --apply
                                             at the end of a run: records the state
                                             of the vault (and the sizes the run could
                                             not go under), and saves the result in git

HOW IT SAVES
  If the vault folder is its own git repository (and git works on this
  computer), it makes a local git commit. It never pushes, so nothing leaves
  this computer. It refuses to commit when a file that looks like a key or a
  password, or a file over 5 MB, would go into git, or when a merge or rebase
  is in progress, or when the owner already has changes staged. In those
  cases it packs a file instead.

  Otherwise it packs the vault into one file inside the vault:
  archives/save-points/save-point-YYYY-MM-DD-HHMM.tar.gz, and checks it file
  by file. It never writes beside the vault. It leaves out archives/,
  outputs/, .git, .trash, node_modules, __pycache__, venv folders, files that
  look like a key or a password, and files over 5 MB (those are not changed
  by the skill anyway). It checks free disk space first. Over 200 MB, it asks
  for --big-ok, so the owner is asked first.

  If nothing in the vault changed since the last save point or the last
  finished run, it makes no new one.

To undo a run: in git, the owner can go back to the save point commit; with a
packed file, Claude copies the files the owner names back out of it (Python's
tarfile module, or a double click on a Mac or Windows).
"""

import sys
sys.dont_write_bytecode = True  # never leave a __pycache__ folder in the vault
import argparse
import tempfile
import datetime as dt
import json
import os
import shutil
import tarfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vaultkit as vk  # noqa: E402

BIG = 5 * 1024 * 1024
ASK_OVER = 200 * 1024 * 1024     # a save point bigger than this needs the owner's yes (--big-ok)
SAVE_DIR = "archives/save-points"
PACK_SKIP_TOP = {"archives", "outputs"}
FP_SKIP_TOP = {".git", "archives", "outputs", ".trash", "node_modules"}
FP_SKIP_NAMES = {".DS_Store", "Thumbs.db", "workspace.json", "workspace-mobile.json"}


def fingerprint(root):
    """What the vault holds right now: every file's path, size and change time."""
    import hashlib
    h = hashlib.sha256()
    for rel in vk.walk_files(root, skip_top=FP_SKIP_TOP):
        if rel == vk.STATE_REL or os.path.basename(rel) in FP_SKIP_NAMES or rel.startswith(".optimize-"):
            continue
        try:
            st = os.lstat(os.path.join(root, rel))
        except OSError:
            continue
        h.update(("%s\0%d\0%d\n" % (vk.nfc(rel), st.st_size, st.st_mtime_ns)).encode("utf-8"))
    return h.hexdigest()


def load_state(root):
    s = vk.load_json(os.path.join(root, vk.STATE_REL), {})
    return s if isinstance(s, dict) else {}


def save_state(root, updates):
    s = load_state(root)
    s.update(updates)
    vk.atomic_write(os.path.join(root, vk.STATE_REL), json.dumps(s, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


def git_busy(root):
    r = vk.git(root, "rev-parse", "--git-dir")
    if r is None or r.returncode != 0:
        return True
    gd = r.stdout.decode("utf-8", "replace").strip()
    gd = gd if os.path.isabs(gd) else os.path.join(root, gd)
    return any(os.path.exists(os.path.join(gd, x)) for x in
               ("index.lock", "rebase-merge", "rebase-apply", "MERGE_HEAD", "CHERRY_PICK_HEAD"))


def git_save(root, message):
    """(saved or already saved, message). False means: use a copy instead."""
    if git_busy(root):
        return False, "git is in the middle of something (a merge, a rebase, or another program using it)"
    st = vk.git(root, "status", "--porcelain")
    if st is None or st.returncode != 0:
        return False, "git could not read the vault's state"
    if not st.stdout.strip():
        return True, "nothing changed since the last git commit, so that commit is the save point"
    pre = vk.git(root, "diff", "--cached", "--quiet")
    if pre is None or pre.returncode != 0:
        return False, "some changes are already staged in git, and a save point would mix them in"
    if vk.git(root, "add", "-A").returncode != 0:
        vk.git(root, "reset", "-q")
        return False, "git could not stage the changes"
    names = vk.git(root, "diff", "--cached", "--name-only", "-z").stdout.decode("utf-8", "replace").split("\0")
    for f in [n for n in names if n]:
        p = os.path.join(root, f)
        if vk.SECRET_NAME.search(f) and not vk.SECRET_NAME_OK.search(f):
            vk.git(root, "reset", "-q")
            return False, "a file that looks like a key or password would go into git: " + f
        if os.path.isfile(p) and os.path.getsize(p) > BIG:
            vk.git(root, "reset", "-q")
            return False, "a file over 5 MB would go into git: " + f
    diff = vk.git(root, "diff", "--cached", "--no-color", "-U0", timeout=120)
    text = diff.stdout.decode("utf-8", "replace") if diff is not None else ""
    current = None
    for line in text.split("\n"):
        if line.startswith("+++ b/"):
            current = line[6:]
        elif line.startswith("+") and not line.startswith("+++") and vk.SECRET_TEXT.search(line):
            vk.git(root, "reset", "-q")
            return False, "text that looks like a key would go into git, in " + (current or "a file")
    ident = []
    em = vk.git(root, "config", "user.email")
    if em is None or not em.stdout.strip():
        ident = ["-c", "user.name=Vault save point", "-c", "user.email=save-point@localhost"]
    r = vk.git(root, *(ident + ["commit", "-q", "-m", message]))
    if r is None or r.returncode != 0:
        vk.git(root, "reset", "-q")
        return False, "git could not make the commit"
    sha = vk.git(root, "rev-parse", "--short", "HEAD").stdout.decode().strip()
    return True, "saved as git commit " + sha + " (local only, never pushed)"


def pack_list(root):
    """(files to pack, files left out with why). Paths are relative to the vault."""
    keep, left = [], []
    for rel in vk.walk_files(root, skip_top=PACK_SKIP_TOP):
        path = os.path.join(root, rel)
        if rel == vk.STATE_REL or rel.startswith(".optimize-"):
            continue
        if vk.SECRET_NAME.search(rel) and not vk.SECRET_NAME_OK.search(rel):
            left.append((rel, "looks like a key or password"))
            continue
        try:
            st = os.lstat(path)
        except OSError:
            left.append((rel, "could not be read"))
            continue
        if os.path.islink(path):
            keep.append((rel, 0))
            continue
        if st.st_size > BIG:
            left.append((rel, "over 5 MB"))
            continue
        if not os.access(path, os.R_OK):
            left.append((rel, "could not be read"))
            continue
        keep.append((rel, st.st_size))
    return keep, left


def pack_save(root, dest_rel, files):
    """Write the packed file through a temp file, then check every name and size in it."""
    dest = os.path.join(root, dest_rel)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(dest), prefix=".optimize-", suffix=".tmp")
    os.close(fd)
    try:
        with tarfile.open(tmp, "w:gz") as tf:
            for rel, _ in files:
                tf.add(os.path.join(root, rel), arcname=rel, recursive=False)
        want = dict((vk.nfc(rel), size) for rel, size in files)
        with tarfile.open(tmp, "r:gz") as tf:
            got = dict((vk.nfc(m.name), (m.size if m.isfile() else 0)) for m in tf.getmembers())
        if got != want:
            os.remove(tmp)
            return False
        os.replace(tmp, dest)
        return True
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def floors(root):
    """The sizes this run could not go under, and what the owner chose to leave as is. The session
    briefing stays quiet about a file until it grows clearly past its size here, so the same offer
    does not come back every session after a run that did all it was allowed to do."""
    import fixes
    import measure
    import tidy
    out = {}
    mem = vk.read_bytes(os.path.join(root, "memory", "claude", "MEMORY.md"))
    if mem is not None:
        t = mem.decode("utf-8", errors="ignore")
        out["memory_lines"] = t.count("\n")
        out["memory_chars"] = len(t)
    for key, rel in (("claude_chars", "CLAUDE.md"), ("decisions_chars", "decisions/log.md")):
        b = vk.read_bytes(os.path.join(root, rel))
        if b is not None:
            out[key] = len(b.decode("utf-8", errors="ignore"))
    t = vk.read_text(os.path.join(root, "tasks.md"))
    if t is not None:
        out["tasks_done"] = tidy.tasks_state(t)["done_items"]
    b = vk.read_bytes(os.path.join(root, "inbox.md"))
    if b is not None:
        out["inbox_lines"] = b.count(b"\n")
    out["long_skills"] = sorted(x["skill"] for x in fixes.skills_report(root) if x["chars"] > vk.DESC_WARN)
    left = measure.open_items(root)
    out["left_as_is"] = left
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Save point before (and after) an optimize run.")
    ap.add_argument("--vault", default=None)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--done", action="store_true")
    ap.add_argument("--big-ok", action="store_true")
    ap.add_argument("--now", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    root = vk.find_vault(args.vault)
    now = vk.parse_now(args.now) or dt.datetime.now()
    stamp = now.strftime("%Y-%m-%d %H:%M")
    use_git = vk.is_git_root(root)
    state = load_state(root)
    fp = fingerprint(root)
    res = {"mode": "git" if use_git else "pack", "applied": False}

    if args.done:
        if not args.apply:
            vk.emit(args, res, ["At the end of a run this records the vault's state" +
                                (" and saves the result as a git commit." if use_git else ".")])
            return 0
        if fp == state.get("fingerprint_after"):
            res["unchanged"] = True
            vk.emit(args, res, ["Nothing in the vault changed since the last finished run, so there is nothing new "
                                "to record."])
            return 0
        save_state(root, {"last_run": stamp, "fingerprint_after": fingerprint(root), "floors": floors(root)})
        msg = "The vault's state after this run is recorded in " + vk.STATE_REL + "."
        if use_git:
            ok, why = git_save(root, "After optimize-vault, " + stamp)
            msg += " " + ("Result " + why + "." if ok else "The result was not saved in git: " + why + ".")
            res["git"] = why
        res["applied"] = True
        vk.emit(args, res, [msg])
        return 0

    if fp == state.get("fingerprint_after"):
        # The vault is exactly as the last run left it. A save point is only worth
        # making if this run has something to change.
        import measure
        if not measure.measure(root, briefing=False)["to_do"]:
            res.update(applied=False, nothing_to_do=True)
            vk.emit(args, res, ["Save point: not needed. The vault is as the last run left it (" +
                                str(state.get("last_run") or "earlier") + ") and nothing needs changing."])
            return 0

    if use_git:
        if not args.apply:
            st = vk.git(root, "status", "--porcelain")
            dirty = bool(st is not None and st.stdout.strip())
            vk.emit(args, res, ["The vault is a git repository. The save point will be a local git commit"
                                + (" of the changes since the last one." if dirty else
                                   " (nothing changed since the last commit, so that commit already is one).")])
            return 0
        ok, why = git_save(root, "Save point before optimize-vault, " + stamp)
        if ok:
            res.update(applied=True, where="git", message=why)
            vk.emit(args, res, ["Save point: " + why + "."])
            return 0
        res["git_refused"] = why
        res["mode"] = "pack"

    last = state.get("save_point")
    if (fp == state.get("save_point_fingerprint") and isinstance(last, str) and last
            and os.path.exists(last if os.path.isabs(last) else os.path.join(root, last))):
        res.update(applied=True, where=last, message="unchanged since the last save point")
        vk.emit(args, res, ["Save point: nothing in the vault changed since the last one (" +
                            str(state.get("save_point_at") or "earlier") + "), so no new one is needed. It is at: "
                            + last])
        return 0

    why_arch = vk.write_problem(root, SAVE_DIR + "/x.tar.gz")
    if why_arch or os.path.islink(os.path.join(root, "archives")):
        print("Save point: " + (why_arch or "archives/ is a link to somewhere else.") +
              " No save point was made, so stop here and tell the owner.")
        return 1
    dest_rel = "%s/save-point-%s.tar.gz" % (SAVE_DIR, now.strftime("%Y-%m-%d-%H%M"))
    k = 2
    while os.path.exists(os.path.join(root, dest_rel)):
        dest_rel = "%s/save-point-%s-%d.tar.gz" % (SAVE_DIR, now.strftime("%Y-%m-%d-%H%M"), k)
        k += 1
    files, left = pack_list(root)
    total = sum(sz for _, sz in files)
    mb = total / 1048576.0
    res.update(where=dest_rel, files=len(files), bytes=total, left_out=[r for r, _ in left][:50])
    pre = ("git would not save it (" + res["git_refused"] + "), so " if res.get("git_refused") else "")
    older = []
    try:
        older = sorted(n for n in os.listdir(os.path.join(root, SAVE_DIR)) if n.endswith(".tar.gz"))
    except OSError:
        pass
    left_line = ("Left out: %d file%s (keys or passwords, files over 5 MB, unreadable files), plus archives/ and "
                 "outputs/." % (len(left), "" if len(left) == 1 else "s")) if left else \
        "Left out: archives/ and outputs/ (old copies and files that can be made again)."
    old_line = (" %d older save point%s in %s." % (len(older), "" if len(older) == 1 else "s", SAVE_DIR)) if older else ""
    if total > ASK_OVER and not args.big_ok:
        res["needs_yes"] = True
        vk.emit(args, res, ["Save point: it would hold %d files, about %.0f MB before packing. That is big, so ask "
                            "the owner first. On their yes, run this again with --big-ok. %s"
                            % (len(files), mb, left_line)])
        return 0 if not args.apply else 1
    try:
        free = shutil.disk_usage(os.path.join(root, "archives") if os.path.isdir(os.path.join(root, "archives"))
                                 else root).free
    except OSError:
        free = None
    if free is not None and free < total + 50 * 1048576:
        print("Save point: there is not enough free disk space (%.0f MB free, about %.0f MB needed). No save point "
              "was made. Stop here and tell the owner." % (free / 1048576.0, mb + 50))
        return 1
    if not args.apply:
        vk.emit(args, res, ["The save point will be one packed file inside the vault: %s (%d files, about %.1f MB "
                            "before packing). %s%s%s" % (dest_rel, len(files), mb, left_line, old_line,
                                                         (" (" + pre.rstrip(", so ") + ")") if pre else "")])
        return 0
    if not pack_save(root, dest_rel, files):
        print("The save point at " + dest_rel + " did not match the vault, so it was not kept. Stop and tell the owner.")
        return 1
    save_state(root, {"save_point": dest_rel, "save_point_at": stamp, "save_point_fingerprint": fp})
    size = os.path.getsize(os.path.join(root, dest_rel))
    res.update(applied=True)
    vk.emit(args, res, ["Save point: " + pre + "the vault is packed into " + dest_rel + " (" + vk.fmt(len(files)) +
                        " files, " + vk.fmt(max(1, size // 1024)) + " KB, checked file by file). " + left_line])
    return 0


if __name__ == "__main__":
    sys.exit(main())
