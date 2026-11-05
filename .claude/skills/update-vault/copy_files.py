"""Copy the new version's files into the vault, after the owner said yes. Step 5 of the update skill.

WHAT IT IS FOR
  One ready way to do the update's copies, so nobody writes a shell loop for
  them. File names with spaces, and shells that split words differently
  (zsh, bash, sh), can never break it: it gets every path from Python, never
  from a shell list. It sorts the files exactly as match_known.py does (it
  uses the same code), then:
    1. saves a copy of every file it will replace, retire, or that Claude
       will merge (a merged file already the new version needs none), in the
       backup folder (.claude/ is saved as dot-claude/ and
       a CLAUDE.md as CLAUDE.old.md, so Claude never reads a backup as live
       rules). A backup that is already there is never overwritten.
    2. copies in the new files, the system files the owner never edited, the
       starter notes still exactly as an earlier version shipped them, and any
       changed file the owner chose to take (--take). Each one is written to a
       temporary file first and then swapped in, so a file is never half
       written.
    3. the merged files (CLAUDE.md, settings.json, the skills list, .gitignore,
       the folder guides, Obsidian's app.json), only where no judgment is
       needed: one the vault lacks is added; one still exactly as an earlier
       version shipped it (nothing of the owner's in it) is swapped for the
       new one; .gitignore gets every line the new version has that the
       vault's lacks, added at the end, and none removed. A merged file that
       holds the owner's text or settings is never written here: the summary
       names it, and Claude merges it by hand afterwards, starting from the
       vault's copy, never by copying the new file over it.
    4. moves each retired file and retired skill folder into the backup
       folder. Nothing is deleted.
  It never touches the owner's own notes, hooks and skills,
  settings.local.json, or a file that is a link. Running it again is safe:
  what is already done is skipped, so after a stop it carries on where it
  stopped.

HOW TO RUN IT (from the vault folder, with Python 3.9 or newer)
  python copy_files.py --template <new template folder> --backup archives/update-YYYY-MM-DD-HHMM
      Shows what it would do. Changes nothing.
  ... --apply
      Does it, then prints a short summary.
  --take PATH   a file the owner changed, where they chose the new version
                (theirs is saved in the backup first). Repeat for each one.
  --skip PATH   a file or folder (ending in /) the owner said to leave out.
  --back-up PATH  one more file Claude will change by hand afterwards (such
                as memory/taste.md or memory/claude/MEMORY.md): saved in the
                backup folder too, and not changed here.
  --vault DIR   the vault folder, if it is not the current folder.

SAFETY
  Writes only inside the vault. Never deletes, never uses the network.
  Standard library only. Exit 0 when done, 1 if a file could not be written
  (run the same command again to finish), 2 if the command is wrong.
"""

import sys
sys.dont_write_bytecode = True  # never leave a __pycache__ folder in the vault
import os
import shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import match_known as mk  # noqa: E402

PLUMBING = (".git", ".github")   # the template's own repository plumbing, never copied


def backup_rel(rel):
    """Where a vault file is saved in the backup folder: .claude/ becomes dot-claude/, CLAUDE.md becomes CLAUDE.old.md."""
    parts = rel.split("/")
    if parts[0] == ".claude":
        parts[0] = "dot-claude"
    if parts[-1] == "CLAUDE.md":
        parts[-1] = "CLAUDE.old.md"
    return "/".join(parts)


def is_plumbing(rel):
    return rel.split("/", 1)[0] in PLUMBING


def norm(path):
    """A path as the checker writes it: forward slashes, no leading "./"."""
    path = path.strip().replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    return path


def skipped(rel, skips):
    for s in skips:
        if rel == s.rstrip("/") or (s.endswith("/") and rel.startswith(s)):
            return True
    return False


def same_bytes(a, b):
    try:
        return mk.file_hash(a) == mk.file_hash(b)
    except OSError:
        return False


def write_copy(src, dest):
    """Copy src to dest through a temporary file and a swap, so dest is never half written."""
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".tmp"
    shutil.copyfile(src, tmp)
    shutil.copymode(src, tmp)
    os.replace(tmp, dest)


def append_lines(path, lines):
    """Add lines at the end of a text file, keeping every byte already in it, through a temporary file and a swap."""
    with open(path, "rb") as fh:
        old = fh.read()
    eol = b"\r\n" if b"\r\n" in old else b"\n"
    add = b""
    if old and not old.endswith(b"\n"):
        add += eol
    if old.strip() and not old.endswith(eol + eol):
        add += eol
    add += eol.join(ln.encode("utf-8") for ln in lines) + eol
    tmp = path + ".tmp"
    with open(tmp, "wb") as fh:
        fh.write(old + add)
    shutil.copymode(path, tmp)
    os.replace(tmp, path)


def save_backup(vault, backup, rel):
    """Copy one vault file into the backup folder, unless a backup of it is already there."""
    dest = os.path.join(backup, *backup_rel(rel).split("/"))
    if os.path.lexists(dest):
        return False
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".tmp"
    shutil.copy2(os.path.join(vault, *rel.split("/")), tmp)
    os.replace(tmp, dest)
    return True


def move_into_backup(vault, backup, rel):
    """Move one retired file into the backup folder. If an identical backup is already there, the vault copy goes;
    if a different one is there, this one is kept beside it with a number."""
    src = os.path.join(vault, *rel.split("/"))
    dest = os.path.join(backup, *backup_rel(rel).split("/"))
    if os.path.lexists(dest):
        if same_bytes(src, dest):
            os.remove(src)
            return dest
        n = 2
        while os.path.lexists(dest + "." + str(n)):
            n += 1
        dest = dest + "." + str(n)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.move(src, dest)
    return dest


def retired_files(vault, folder_rel):
    """Every file in a retired skill folder, including ones match_known leaves out (such as __pycache__)."""
    out = []
    base = os.path.join(vault, *folder_rel.rstrip("/").split("/"))
    for dp, dns, fns in os.walk(base):
        dns.sort()
        for f in sorted(fns):
            out.append(os.path.relpath(os.path.join(dp, f), vault).replace(os.sep, "/"))
    return out


def remove_empty_dirs(vault, folder_rel):
    base = os.path.join(vault, *folder_rel.rstrip("/").split("/"))
    for dp, dns, fns in sorted(os.walk(base, topdown=False), key=lambda x: -len(x[0])):
        try:
            os.rmdir(dp)  # only ever succeeds on an empty folder
        except OSError:
            pass


def plan(vault, template, takes, skips):
    info = mk.sort_files(vault, template, os.path.join(mk.HERE, "known-versions.json"))
    g = info["groups"]
    copy = []        # (rel, kind)
    for rel in g["new"]:
        copy.append((rel, "new"))
    for rel in g["replace"]:
        copy.append((rel, "replace"))
    for rel in g["seed_replace"]:
        copy.append((rel, "starter"))
    bad_takes = [t for t in takes if t not in g["ask"] and t not in g["replace"] and t not in g["seed_replace"]
                 and t not in g["same"]]
    for rel in g["ask"]:
        if rel in takes:
            copy.append((rel, "taken"))
    # A merged file the vault lacks holds nothing of the owner's: it is simply added.
    for rel in info["missing_merge"]:
        copy.append((rel, "new"))
    copy = [(r, k) for r, k in copy if not is_plumbing(r) and not skipped(r, skips)]
    merge = [r for r in g["merge"] if r not in info["missing_merge"] and not skipped(r, skips)]
    status = info["merge_status"]
    # A merged file still exactly as an earlier version shipped it holds nothing of the owner's either, so the
    # new version replaces it whole. .gitignore only ever gains lines. The rest Claude merges by hand.
    for rel in merge:
        if rel != ".gitignore" and status.get(rel, "").startswith("version "):
            copy.append((rel, "merged"))
    links = [r for r, _ in copy if os.path.islink(os.path.join(vault, *r.split("/")))]
    copy = [(r, k) for r, k in copy if r not in links]
    gitignore_add = []
    by_hand = [r for r in merge if r != ".gitignore" and status.get(r) == "owner"]
    if ".gitignore" in merge and status.get(".gitignore") != "same":
        gi = os.path.join(vault, ".gitignore")
        if os.path.islink(gi):
            links.append(".gitignore")
        else:
            new_gi = os.path.join(template, *info["tmpl_paths"][".gitignore"].split("/"))
            gitignore_add = mk.gitignore_missing(gi, new_gi)
            if gitignore_add is None:
                gitignore_add = []
                by_hand.append(".gitignore")
    by_hand = [r for r in by_hand if r not in links]
    retire = [r for r in g["retire"] if not skipped(r, skips)]
    return {"copy": copy, "merge": merge, "retire": retire, "links": links, "bad_takes": bad_takes,
            "kept": [r for r in g["ask"] if r not in takes], "tmpl_paths": info["tmpl_paths"],
            "gitignore_add": gitignore_add, "by_hand": by_hand,
            # A merged file already the new version changes nowhere, so it needs no backup copy. This also keeps a
            # second run from saving a copy of a file the first run added.
            "merge_backup": [r for r in merge if status.get(r) != "same"]}


def main(argv):
    vault, template, backup, takes, skips, extra, apply = ".", None, None, [], [], [], False
    args = list(argv[1:])
    while args:
        a = args.pop(0)
        if a in ("--vault", "--template", "--backup", "--take", "--skip", "--back-up") and args:
            v = args.pop(0)
            if a == "--vault":
                vault = v
            elif a == "--template":
                template = v
            elif a == "--backup":
                backup = v
            elif a == "--take":
                takes.append(norm(v))
            elif a == "--skip":
                skips.append(norm(v))
            else:
                extra.append(norm(v))
        elif a == "--apply":
            apply = True
        else:
            print(__doc__)
            return 2
    vault = os.path.abspath(vault)
    if not template or not backup:
        print("Needs --template (the downloaded copy) and --backup (archives/update-YYYY-MM-DD-HHMM).")
        return 2
    template = os.path.abspath(template)
    if not os.path.isfile(os.path.join(vault, "CLAUDE.md")):
        print("No CLAUDE.md in " + vault + ". Run this from the vault folder, or give --vault.")
        return 2
    if not os.path.isdir(template):
        print("The template copy is not there: " + template)
        return 2
    backup_abs = os.path.abspath(os.path.join(vault, backup))
    archives = os.path.join(vault, "archives") + os.sep
    if not backup_abs.startswith(archives) or os.path.basename(backup_abs) in ("", "archives"):
        print("The backup folder must be a new folder inside the vault's archives/ folder, such as "
              "archives/update-2026-03-14-0930.")
        return 2

    p = plan(vault, template, takes, skips)
    if p["bad_takes"]:
        print("--take only works for a file the owner changed (the checker's ASK list). Not one: "
              + ", ".join(p["bad_takes"]) + ". Nothing was changed.")
        return 2
    backup_rel_dir = os.path.relpath(backup_abs, vault).replace(os.sep, "/")
    missing = [r for r in extra if not os.path.isfile(os.path.join(vault, *r.split("/")))
               or os.path.islink(os.path.join(vault, *r.split("/")))]
    if missing:
        print("--back-up needs a file in the vault. Not found: " + ", ".join(missing) + ". Nothing was changed.")
        return 2
    to_back_up = [r for r, k in p["copy"] if k not in ("new", "merged")] + p["merge_backup"]
    to_back_up += [r for r in extra if r not in to_back_up]
    retire_files = []
    for r in p["retire"]:
        retire_files.extend(retired_files(vault, r) if r.endswith("/") else [r])

    counts = {k: sum(1 for _, kk in p["copy"] if kk == k) for k in ("new", "replace", "starter", "taken", "merged")}
    by_hand = ", ".join(p["by_hand"])
    if not apply:
        print("Dry run: nothing changed. With --apply this would:")
        print("- save " + str(len(to_back_up) + len(retire_files)) + " old copies in " + backup_rel_dir + "/ ("
              + str(len(p["merge_backup"])) + " of them are the merged files"
              + (", plus " + ", ".join(extra) if extra else "") + ")")
        for k, label in (("new", "add"), ("replace", "replace (never edited)"),
                         ("starter", "swap (untouched starter notes)"),
                         ("taken", "replace (the owner chose the new version)"),
                         ("merged", "take the new version whole (merged files with nothing of the owner's in them)")):
            items = [r for r, kk in p["copy"] if kk == k]
            if items:
                print("- " + label + ", " + str(len(items)) + ": " + ", ".join(items))
        if p["gitignore_add"]:
            pats = [x for x in p["gitignore_add"] if not x.startswith("#")]
            print("- add " + str(len(pats)) + " new line" + ("" if len(pats) == 1 else "s")
                  + " at the end of .gitignore (none removed): " + ", ".join(pats))
        if p["retire"]:
            print("- move into the backup folder, " + str(len(p["retire"])) + ": " + ", ".join(p["retire"]))
        if p["kept"]:
            print("- keep the owner's changed copy (no --take), " + str(len(p["kept"])) + ": " + ", ".join(p["kept"]))
        if p["links"]:
            print("- leave as is (a link, not a file): " + ", ".join(p["links"]))
        if by_hand:
            print("- leave for Claude to merge by hand, starting from the vault's copy (they hold the owner's text or "
                  "settings, so never copy the new file over them), " + str(len(p["by_hand"])) + ": " + by_hand)
        return 0

    done = {"backed_up": 0, "copied": 0, "retired": 0, "merged": 0, "gitignore": 0}
    try:
        current = ""
        for rel in to_back_up + retire_files:
            current = rel
            if save_backup(vault, backup_abs, rel):
                done["backed_up"] += 1
        for rel, kind in p["copy"]:
            current = rel
            src = os.path.join(template, *p["tmpl_paths"][rel].split("/"))
            dest = os.path.join(vault, *rel.split("/"))
            if os.path.isfile(dest) and same_bytes(src, dest):
                continue
            write_copy(src, dest)
            done["merged" if kind == "merged" else "copied"] += 1
        if p["gitignore_add"]:
            current = ".gitignore"
            append_lines(os.path.join(vault, ".gitignore"), p["gitignore_add"])
            done["gitignore"] = len([x for x in p["gitignore_add"] if not x.startswith("#")])
        for rel in retire_files:
            current = rel
            if os.path.lexists(os.path.join(vault, *rel.split("/"))):
                move_into_backup(vault, backup_abs, rel)
                done["retired"] += 1
        for r in p["retire"]:
            if r.endswith("/"):
                remove_empty_dirs(vault, r)
    except OSError as e:
        print("STOPPED at " + current + ": " + (e.strerror or str(e)) + ". Done so far: "
              + str(done["copied"] + done["merged"]) + " copied, " + str(done["backed_up"]) + " old copies saved, "
              + str(done["retired"]) + " moved. Run the same command again to finish; what is done is skipped.")
        return 1

    links = (" Left as is (a link): " + ", ".join(p["links"]) + "." if p["links"] else "")
    hand = (" Merge by hand next, starting from the vault's copy (never copy the new file over it): " + by_hand + "."
            if by_hand else " No merged file is left to merge by hand.")
    if not (done["copied"] or done["backed_up"] or done["retired"] or done["merged"] or done["gitignore"]):
        print("Done. Nothing left to copy: every file is already the new version, and the old copies are in "
              + backup_rel_dir + "/." + (" If not done yet, merge by hand, starting from the vault's copy: "
                                         + by_hand + "." if by_hand else "") + links)
        return 0
    merged = []
    if done["merged"]:
        merged.append(str(done["merged"]) + " taken whole (nothing of the owner's in them)")
    if done["gitignore"]:
        merged.append(str(done["gitignore"]) + " new line" + ("" if done["gitignore"] == 1 else "s")
                      + " added to .gitignore")
    print("Done. " + str(done["copied"]) + " files copied in (" + str(counts["new"]) + " new, "
          + str(counts["replace"] + counts["taken"]) + " replaced, " + str(counts["starter"]) + " starter notes). "
          + str(done["backed_up"]) + " old copies saved in " + backup_rel_dir + "/. "
          + str(len(p["retire"])) + " retired items moved there."
          + (" Merged files: " + "; ".join(merged) + "." if merged else "") + hand + links)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
