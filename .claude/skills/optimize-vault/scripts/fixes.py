"""The smaller fixes of the optimize-vault skill. Each one is a dry run unless
--apply is given, and each keeps a copy of any file it changes in the run
folder (archives/optimize-YYYY-MM-DD-HHMM/).

  python3 fixes.py repeats --vault .
      Only when CLAUDE.md is over its 18,000-character limit: CLAUDE.md lines
      the owner added that a memory note repeats word for word. Every one of
      them stays unless the owner names its number (the owner wrote it, and
      a line that leaves CLAUDE.md is no longer read in every chat).
      Apply: --apply --remove 2,5 --run-dir <run folder>  (--also-rules is
      the old name for --remove and still works)

  python3 fixes.py skills --vault .
      Every skill description with its length and trigger phrases. For one
      over 600 characters that says the same thing more than once, it also
      prints the text with the repeats cut, every kept word the owner's own.
      Shorten one: --skill NAME --text "new description" --apply --run-dir ...
      It refuses a new text that drops a trigger phrase, is over 500
      characters, or would break the skill's header.

  python3 fixes.py gitignore --vault . [--add PATTERN] [--apply --run-dir ...]
      Lines the template keeps in .gitignore (keys, passwords, scratch files)
      that this vault's .gitignore lacks. Only adds lines, never removes one.

  python3 fixes.py scan --vault .
      Secret files, text that looks like a key, and media files in the vault.
      Shows a path and a kind only, never what a file says.

  python3 fixes.py move-out --vault . --path REL [--path REL] [--dest DIR] --apply --run-dir ...
      Moves those files out of the vault (default: a folder beside the vault
      named "<vault> moved out YYYY-MM-DD"), checks each copy, and adds a
      .gitignore line for each secret file. Only on the owner's yes.

  python3 fixes.py save-points --vault . --apply --run-dir ...
      Switches on the save point at the end of each session (creates
      .claude/save-points-on). Only on the owner's yes, and only in a vault
      folder that is a git repository (they save nothing anywhere else).

  python3 fixes.py log --vault . --text "..." --apply --run-dir ...
      Adds one dated entry to decisions/log.md saying what this run changed.
"""

import sys
sys.dont_write_bytecode = True  # never leave a __pycache__ folder in the vault
import argparse
import datetime as dt
import fnmatch
import json
import os
import re
import shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vaultkit as vk  # noqa: E402
import memory_index as mi  # noqa: E402

DEFAULT_GITIGNORE = [
    "client_secret_*.json", "*credentials*.json", "*-service-account*.json", "*.pem", "*.key", "*.token",
    ".env", ".env.local", ".env.*.local", "outputs/*", "!outputs/.gitkeep", ".obsidian/workspace.json",
    ".obsidian/workspace-mobile.json", ".obsidian/graph.json", ".claude/settings.local.json", "HANDOFF.md",
    ".DS_Store", "*.log", "__pycache__/", "*.pyc",
]


# ---------------------------------------------------------------- repeats

def norm_line(s):
    s = vk.bare(s).strip()
    s = re.sub(r"^(?:[-*+]|\d+[.)])\s+", "", s)
    return re.sub(r"\s+", " ", s).strip()


def template_line_hashes():
    facts = vk.template_facts()
    return set(facts.get("claude_line_hashes", []))


def find_repeats(root):
    text = vk.read_text(os.path.join(root, "CLAUDE.md")) or ""
    lines = vk.split_keep(text)
    mask = vk.masked(lines)
    shipped = template_line_hashes()
    reach = mi.reachable(root)
    note_lines = {}
    for rel in mi.memory_notes(root):
        if rel not in reach:
            continue
        body = vk.read_text(os.path.join(root, rel)) or ""
        if mi.HUB_MARK in body:
            continue
        for l in body.split("\n"):
            n = norm_line(l)
            if len(n) >= 25:
                note_lines.setdefault(n, rel)
    out = []
    for i, l in enumerate(lines):
        if mask[i]:
            continue
        s = vk.bare(l).strip()
        if not s or s.startswith("|") or vk.heading_of(s) or "{{" in s:
            continue
        n = norm_line(l)
        if len(n) < 25:
            continue
        if vk.norm_hash(n) in shipped:
            continue
        rel = note_lines.get(n)
        if not rel:
            continue
        out.append({"i": i, "line": vk.bare(l), "note": rel, "rule": vk.is_rule_like(n)})
    for k, r in enumerate(out, 1):
        r["id"] = k
    return text, out


def cmd_repeats(args, root, now):
    claude_chars = len(vk.read_text(os.path.join(root, "CLAUDE.md")) or "")
    if claude_chars <= vk.CLAUDE_WARN:
        vk.emit(args, {"repeats": [], "applied": False, "under_limit": True, "chars": claude_chars},
                ["CLAUDE.md is %s characters, under its %s limit, so no line in it is touched."
                 % (vk.fmt(claude_chars), vk.fmt(vk.CLAUDE_WARN))])
        return 0
    text, reps = find_repeats(root)
    skip = ids(args.skip)
    named = ids(args.remove) | ids(args.also_rules)
    chosen = [r for r in reps if r["id"] in named and r["id"] not in skip]
    lines = []
    if not reps:
        lines.append("CLAUDE.md: no line repeats a memory note word for word.")
        vk.emit(args, {"repeats": [], "applied": False}, lines)
        return 0
    lines.append("CLAUDE.md is %s characters, over its %s limit. These lines the owner wrote are also, word for word, "
                 "in a memory note. Each one stays unless the owner names its number:" % (vk.fmt(claude_chars),
                                                                                         vk.fmt(vk.CLAUDE_WARN)))
    for r in reps:
        tag = "states a rule or a default" if r["rule"] else "plain"
        lines.append("  [%d] (%s, stays unless named) %s" % (r["id"], tag, r["line"][:160]))
        lines.append("       also in %s" % r["note"])
    saved = sum(len(r["line"]) + 1 for r in chosen)
    res = {"repeats": reps, "chosen": [r["id"] for r in chosen], "chars_saved": saved, "applied": False}
    if args.apply and chosen:
        b = vk.read_bytes(os.path.join(root, "CLAUDE.md"))
        why = vk.write_problem(root, "CLAUDE.md")
        if why or b is None:
            print((why or "CLAUDE.md could not be read.") + " Nothing was changed.")
            return 1
        old = vk.split_keep(b.decode("utf-8"))
        drop = set(r["i"] for r in chosen)
        new = "".join(l for i, l in enumerate(old) if i not in drop)
        run = vk.Run(root, args.run_dir, now)
        try:
            run.write("CLAUDE.md", new, expect=b)
        except vk.ChangedUnderUs:
            print("CLAUDE.md changed while this ran. Nothing was changed.")
            return 1
        missing = [r for r in chosen if norm_line(r["line"]) not in
                   [norm_line(x) for x in (vk.read_text(os.path.join(root, r["note"])) or "").split("\n")]]
        res["applied"] = not missing
        res["run_dir"] = run.rel
        run.note("repeats", {"trimmed": [{"line": r["line"], "note": r["note"]} for r in chosen]})
        lines.append("Removed %d lines from CLAUDE.md (%s characters). Each one is still in its memory note."
                     % (len(chosen), vk.fmt(saved)))
    elif chosen:
        lines.append("Would remove %d lines the owner named (%s characters): %s."
                     % (len(chosen), vk.fmt(saved), ", ".join(str(r["id"]) for r in chosen)))
    else:
        lines.append("Nothing is removed unless the owner names a number (--remove 2,5).")
    vk.emit(args, res, lines)
    return 0


def ids(s):
    out = set()
    for part in (s or "").split(","):
        part = part.strip()
        if part.isdigit():
            out.add(int(part))
    return out


# ---------------------------------------------------------------- skills

def template_skills():
    facts = vk.template_facts()
    names = set(facts.get("skills", []))
    kv = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                      "update-vault", "known-versions.json")
    data = vk.load_json(kv, {})
    for v in data.get("versions", []) if isinstance(data, dict) else []:
        for rel in (v.get("files") or {}):
            p = rel.split("/")
            if rel.startswith(".claude/skills/") and len(p) > 3:
                names.add(p[2])
    return names


def cut_repeats(desc):
    """The description with the sentences it says twice cut, keeping the first time each is said, word for word.

    A sentence counts as said twice when it matches an earlier one, or when it is the start of an earlier one cut
    off (at least six words). Returns None when nothing repeats. Every word that stays is exactly the owner's."""
    parts = [x for x in re.split(r"(?<=[.!?])\s+", (desc or "").strip()) if x]
    kept, cut = [], False
    for s in parts:
        words = s.rstrip(".!?").split()
        dup = False
        for k in kept:
            kw = k.rstrip(".!?").split()
            if words == kw or (len(words) >= 6 and kw[:len(words)] == words):
                dup = True
                break
        if dup:
            cut = True
        else:
            kept.append(s)
    return " ".join(kept) if cut else None


def skills_report(root):
    out = []
    shipped = template_skills()
    for n in vk.skill_dirs(root):
        text = vk.read_text(os.path.join(root, ".claude", "skills", n, "SKILL.md")) or ""
        desc, _, _, name = vk.description_of(text)
        d = desc or ""
        L = len(d)
        status = ("missing" if not d else "short" if L < vk.DESC_MIN else "ok" if L <= vk.DESC_MAX
                  else "a bit long" if L <= vk.DESC_WARN else "over budget")
        shorter = cut_repeats(d) if L > vk.DESC_MAX else None
        if shorter and check_new_desc(d, shorter):
            shorter = None   # still too long, or it would break a rule: write the shorter text by hand
        out.append({"skill": n, "chars": L, "status": status, "phrases": vk.trigger_phrases(d),
                    "ships_with_template": n in shipped, "listing_chars": len(name or n) + 2 + L,
                    "repeats_cut": shorter})
    return out


def check_new_desc(old, new):
    problems = []
    if "\n" in new or "\r" in new:
        problems.append("it must be one line")
    if len(new) > vk.DESC_MAX:
        problems.append("it is %d characters; the most is %d" % (len(new), vk.DESC_MAX))
    if len(new) < 100:
        problems.append("it is too short to say when the skill runs")
    if "\u2014" in new:
        problems.append("it has an em dash")
    if ": " in new or " #" in new or new[:1] in "'[{*&!|>%@`\"":
        problems.append("it has a colon and a space, a ' #', or starts with a symbol, which breaks the skill header")
    lost = [p for p in vk.trigger_phrases(old) if '"' + p + '"' not in new]
    if lost:
        problems.append("it drops these trigger phrases: " + "; ".join('"' + p + '"' for p in lost))
    return problems


def cmd_skills(args, root, now):
    rep = skills_report(root)
    lines = []
    if args.skill:
        path = os.path.join(root, ".claude", "skills", args.skill, "SKILL.md")
        b = vk.read_bytes(path)
        if b is None:
            print("No skill called " + args.skill)
            return 1
        text = b.decode("utf-8", errors="replace")
        old, a, z, _ = vk.description_of(text)
        new = (args.text or "").strip()
        problems = check_new_desc(old or "", new)
        res = {"skill": args.skill, "before": old, "after": new, "chars_before": len(old or ""), "chars_after": len(new),
               "problems": problems, "applied": False}
        lines.append("Skill %s, description before (%d characters):" % (args.skill, len(old or "")))
        lines.append("  " + (old or ""))
        lines.append("After (%d characters):" % len(new))
        lines.append("  " + new)
        if problems:
            lines.append("NOT ACCEPTED: " + "; ".join(problems))
            vk.emit(args, res, lines)
            return 1
        if args.apply:
            ls = vk.split_keep(text)
            eol = vk.eol_of(ls)
            ls[a:z] = ["description: " + new + eol]
            run = vk.Run(root, args.run_dir, now)
            rel = ".claude/skills/%s/SKILL.md" % args.skill
            try:
                run.write(rel, "".join(ls), expect=b)
            except vk.ChangedUnderUs:
                print(rel + " changed while this ran. Nothing was changed.")
                return 1
            back, _, _, _ = vk.description_of(vk.read_text(path) or "")
            res["applied"] = back == new
            res["run_dir"] = run.rel
            run.note("skill-description", {"skill": args.skill, "replaced": [{"file": rel, "old": old}],
                                           "chars_before": len(old or ""), "chars_after": len(new)})
            lines.append("Saved. The old description is kept in " + run.rel + ".")
        vk.emit(args, res, lines)
        return 0
    lines.append("Skill descriptions (Claude reads every one in every chat; aim for %d to %d characters):"
                 % (vk.DESC_MIN, vk.DESC_MAX))
    for r in rep:
        who = "ships with the template" if r["ships_with_template"] else "the owner's"
        lines.append("  %-22s %5d  %-12s %s" % (r["skill"], r["chars"], r["status"], who))
    over = [r for r in rep if r["status"] == "over budget"]
    if over:
        lines.append("Over %d characters:" % vk.DESC_WARN)
        for r in over:
            lines.append("  %s: %d trigger phrases to keep: %s" % (r["skill"], len(r["phrases"]),
                                                                   "; ".join('"' + p + '"' for p in r["phrases"])))
            if r["repeats_cut"]:
                lines.append("    It says the same thing more than once. With the repeats cut, every kept word the "
                             "owner's own (%d characters), use this text as is:" % len(r["repeats_cut"]))
                lines.append("    " + r["repeats_cut"])
    vk.emit(args, {"skills": rep}, lines)
    return 0


# ---------------------------------------------------------------- .gitignore

def required_gitignore():
    facts = vk.template_facts()
    return list(facts.get("gitignore_required") or DEFAULT_GITIGNORE)


def gitignore_missing(root, extra=()):
    text = vk.read_text(os.path.join(root, ".gitignore"))
    have = set(vk.bare(l).strip() for l in vk.split_keep(text or ""))
    want = required_gitignore() + [x for x in extra if x]
    out = []
    for w in want:
        if w not in have and w not in out:
            out.append(w)
    return text, out


def add_gitignore(run, root, lines_to_add, today):
    path = os.path.join(root, ".gitignore")
    b = vk.read_bytes(path)
    text = b.decode("utf-8", errors="replace") if b is not None else ""
    eol = vk.eol_of(vk.split_keep(text)) if text else "\n"
    if text and not text.endswith("\n"):
        text += eol
    block = (eol if text else "") + "# Added by the optimize-vault skill on %s (keys, passwords and scratch files " \
                                     "stay out of git)" % today.isoformat() + eol
    block += "".join(l + eol for l in lines_to_add)
    run.write(".gitignore", text + block, expect=b)


def cmd_gitignore(args, root, now):
    today = (now or dt.datetime.now()).date()
    _, missing = gitignore_missing(root, args.add or [])
    res = {"missing": missing, "applied": False}
    lines = []
    if not missing:
        lines.append(".gitignore: has every line it needs.")
        vk.emit(args, res, lines)
        return 0
    lines.append(".gitignore is missing %d line%s: %s" % (len(missing), "" if len(missing) == 1 else "s",
                                                         ", ".join(missing)))
    if args.apply:
        run = vk.Run(root, args.run_dir, now)
        try:
            add_gitignore(run, root, missing, today)
        except vk.ChangedUnderUs:
            print(".gitignore changed while this ran. Nothing was changed.")
            return 1
        res["applied"] = True
        res["run_dir"] = run.rel
        run.note("gitignore", {"added": missing})
        lines.append("Added them at the end. Nothing was removed.")
    vk.emit(args, res, lines)
    return 0


# ---------------------------------------------------------------- scan

def looks_like_keynote(path):
    b = vk.read_bytes(path) or b""
    return b[:2] == b"PK"


def scan(root):
    """Secret files, key-looking text and media files. Paths and kinds only."""
    found = []
    note_texts = None
    for rel in vk.walk_files(root):
        path = os.path.join(root, rel)
        if os.path.islink(path) or not os.path.isfile(path):
            continue
        try:
            size = os.path.getsize(path)
        except OSError:
            continue
        name_hit = vk.SECRET_NAME.search(rel) and not vk.SECRET_NAME_OK.search(rel)
        if name_hit and rel.lower().endswith((".key", ".pem")) and looks_like_keynote(path):
            name_hit = False
        if name_hit:
            found.append({"path": rel, "kind": "secret file", "size": size})
            continue
        if vk.MEDIA_EXT.search(rel):
            if rel.startswith(vk.MEDIA_OK_DIRS):
                continue
            found.append({"path": rel, "kind": "media", "size": size, "big": size >= vk.MEDIA_BIG})
            continue
        if size <= 1024 * 1024 and (vk.TEXT_EXT.search(rel) or "." not in os.path.basename(rel)):
            raw = vk.read_bytes(path)
            if raw is None:
                found.append({"path": rel, "kind": "could not read", "size": size})
                continue
            t = raw.decode("utf-8", errors="replace")
            for n, line in enumerate(t.split("\n"), 1):
                if vk.SECRET_TEXT.search(line):
                    found.append({"path": rel, "kind": "text that looks like a key", "size": size, "line": n})
                    break
    big = [f for f in found if f.get("big")]
    if big:
        note_texts = {}
        for rel in vk.notes(root, include_history=True):
            note_texts[rel] = vk.read_text(os.path.join(root, rel)) or ""
        for f in big:
            base = os.path.basename(f["path"])
            f["linked_from"] = sorted(r for r, t in note_texts.items() if base in t)[:5]
    for f in found:
        if f["kind"] not in ("media", "could not read"):
            r = vk.git(root, "ls-files", "--error-unmatch", "--", f["path"])
            f["in_git"] = bool(r is not None and r.returncode == 0)
    return found


def cmd_scan(args, root, now):
    found = scan(root)
    lines = []
    secrets = [f for f in found if f["kind"] not in ("media", "could not read")]
    media = [f for f in found if f["kind"] == "media"]
    unread = [f for f in found if f["kind"] == "could not read"]
    if not found:
        lines.append("No secret files, key-looking text or media files in the vault.")
    if unread:
        lines.append("  Files this computer would not let it read (no permission?), so they were left as is: "
                     + ", ".join(f["path"] for f in unread[:10]) + (" and more" if len(unread) > 10 else ""))
    for f in secrets:
        extra = (" (line %d)" % f["line"]) if f.get("line") else ""
        lines.append("  %s: %s%s%s. Contents not shown." % (f["kind"], f["path"], extra,
                                                           ", saved in git history" if f.get("in_git") else ""))
    if media:
        total = sum(f["size"] for f in media)
        lines.append("  media files outside brand/logos/ and outputs/: %d (%s KB)" % (len(media), vk.fmt(total // 1024)))
        for f in media:
            if f.get("big"):
                lines.append("    big: %s (%.1f MB)%s" % (f["path"], f["size"] / 1048576.0,
                                                       (", shown in " + ", ".join(f["linked_from"]))
                                                       if f.get("linked_from") else ""))
    vk.emit(args, {"found": found}, lines)
    return 0


# ---------------------------------------------------------------- move out

def default_dest(root, today):
    parent = os.path.dirname(os.path.abspath(root))
    return os.path.join(parent, os.path.basename(os.path.abspath(root)) + " moved out " + today.isoformat())


def cmd_move_out(args, root, now):
    today = (now or dt.datetime.now()).date()
    dest = os.path.abspath(args.dest or default_dest(root, today))
    if (dest + os.sep).startswith(os.path.abspath(root) + os.sep):
        print("The place to move files to must be outside the vault.")
        return 1
    found = dict((f["path"], f) for f in scan(root))
    todo = []
    for p in args.path or []:
        rel = p.replace(os.sep, "/")
        while rel.startswith("./"):
            rel = rel[2:]
        src = os.path.abspath(os.path.join(root, rel))
        if not (src + os.sep).startswith(os.path.abspath(root) + os.sep) or rel.split("/")[0] == ".git":
            print("Not a file in the vault: " + p)
            return 1
        if not os.path.isfile(src) or os.path.islink(src):
            print("Not a file in the vault: " + p)
            return 1
        todo.append((rel, found.get(rel, {}).get("kind", "file")))
    lines = []
    res = {"dest": dest, "files": [], "applied": False}
    if not todo:
        lines.append("Nothing named to move.")
        vk.emit(args, res, lines)
        return 0
    for rel, kind in todo:
        lines.append("  %s (%s) -> %s" % (rel, kind, os.path.join(dest, rel)))
    if not args.apply:
        lines.insert(0, "Would move %d file%s out of the vault to %s:" % (len(todo), "" if len(todo) == 1 else "s", dest))
        vk.emit(args, res, lines)
        return 0
    run = vk.Run(root, args.run_dir, now)
    moved = []
    for rel, kind in todo:
        src = os.path.join(root, rel)
        dst = os.path.join(dest, rel)
        if os.path.exists(dst):
            stem, ext = os.path.splitext(dst)
            k = 2
            while os.path.exists("%s (%d)%s" % (stem, k, ext)):
                k += 1
            dst = "%s (%d)%s" % (stem, k, ext)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        h = vk.sha_file(src)
        shutil.copy2(src, dst)
        if vk.sha_file(dst) != h:
            os.remove(dst)
            print("The copy of %s did not match, so it was left in place." % rel)
            return 1
        os.remove(src)
        moved.append({"from": rel, "to": dst, "sha256": h, "kind": kind})
        res["files"].append({"from": rel, "to": dst, "kind": kind})
    gi_text = vk.read_text(os.path.join(root, ".gitignore")) or ""
    patterns = [vk.bare(l).strip() for l in vk.split_keep(gi_text)]
    patterns = [p for p in patterns if p and not p.startswith(("#", "!"))]

    def covered(rel):
        base = os.path.basename(rel)
        return any(fnmatch.fnmatch(base, p) or fnmatch.fnmatch(rel, p.lstrip("/")) for p in patterns)

    secret_lines = ["/" + m["from"] for m in moved if m["kind"] != "media" and not covered(m["from"])]
    if secret_lines:
        _, missing = gitignore_missing(root, secret_lines)
        missing = [m for m in missing if m in secret_lines]
        if missing:
            add_gitignore(run, root, missing, today)
    run.note("move-out", {"moved": moved, "gitignore_added": secret_lines})
    res["applied"] = True
    res["run_dir"] = run.rel
    lines.insert(0, "Moved %d file%s out of the vault to %s (each copy checked before the original was removed):"
                 % (len(moved), "" if len(moved) == 1 else "s", dest))
    if secret_lines:
        lines.append("Added .gitignore lines so a copy put back is never saved in git: " + ", ".join(secret_lines))
    vk.emit(args, res, lines)
    return 0


# ---------------------------------------------------------------- save points switch

def cmd_save_points(args, root, now):
    path = os.path.join(root, vk.SAVE_POINTS_FLAG)
    on = os.path.isfile(path)
    in_git = vk.is_git_root(root)
    res = {"on": on, "applied": False, "git_repo": in_git}
    if on:
        vk.emit(args, res, ["Save points at the end of each session are already on."])
        return 0
    if not in_git:
        # The save point helper only works in a git repository, and the vault check
        # flags the switch when there is none, so it stays off.
        res["why"] = "not a git repository"
        vk.emit(args, res, ["Save points at the end of each session need this folder to be a git repository, and "
                            "it is not one (or git is not set up on this computer), so they stay off. Nothing "
                            "changed."])
        return 0
    if not args.apply:
        vk.emit(args, res, ["Save points at the end of each session are off. --apply switches them on "
                            "(creates " + vk.SAVE_POINTS_FLAG + ")."])
        return 0
    run = vk.Run(root, args.run_dir, now)
    run.write(vk.SAVE_POINTS_FLAG, "")
    run.note("save-points", {"created": vk.SAVE_POINTS_FLAG})
    res.update(on=True, applied=True, run_dir=run.rel)
    vk.emit(args, res, ["Save points at the end of each session are on now (" + vk.SAVE_POINTS_FLAG + "). "
                        "Delete that file to turn them off."])
    return 0


# ---------------------------------------------------------------- log line

def cmd_log(args, root, now):
    today = (now or dt.datetime.now()).date()
    text = (args.text or "").strip()
    if not text or "\n" in text:
        print("--text must be one line saying what changed.")
        return 1
    if args.apply:
        probe = vk.Run(root, args.run_dir, now)
        if not os.path.isfile(probe.manifest_path()) or not probe.manifest()["steps"]:
            vk.emit(args, {"applied": False, "why": "nothing changed"},
                    ["Nothing changed in this run, so no log line was added."])
            return 0
    path = os.path.join(root, "decisions", "log.md")
    why = vk.write_problem(root, "decisions/log.md")
    if why or (os.path.lexists(path) and vk.read_bytes(path) is None):
        why = why or "decisions/log.md could not be read, so it was left as is."
        vk.emit(args, {"applied": False, "why": why}, [why + " No log line was added. Tell the owner, and give "
                                                        "them the line to add by hand."])
        return 0
    b = vk.read_bytes(path)
    old = b.decode("utf-8") if b is not None else ""
    eol = vk.eol_of(vk.split_keep(old)) if old else "\n"
    entry = "## %s Tidied the vault (optimize-vault)%s%s**Decision:** %s%s" % (today.isoformat(), eol, eol, text, eol)
    sep = "" if not old else (eol if old.endswith("\n") else eol + eol)
    new = old + sep + entry
    if not args.apply:
        vk.emit(args, {"entry": entry, "applied": False}, ["Would add to decisions/log.md:", entry.rstrip()])
        return 0
    run = vk.Run(root, args.run_dir, now)
    try:
        run.write("decisions/log.md", new, expect=b)
    except vk.ChangedUnderUs:
        print("decisions/log.md changed while this ran. Nothing was changed.")
        return 1
    run.note("log", {"entry": entry.strip()})
    vk.emit(args, {"entry": entry, "applied": True, "run_dir": run.rel}, ["Added to decisions/log.md:", entry.rstrip()])
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Smaller optimize-vault fixes (dry run unless --apply).")
    ap.add_argument("cmd", choices=["repeats", "skills", "gitignore", "scan", "move-out", "save-points", "log"])
    ap.add_argument("--vault", default=None)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--run-dir", default=None)
    ap.add_argument("--skip", default=None)
    ap.add_argument("--also-rules", default=None)
    ap.add_argument("--remove", default=None)
    ap.add_argument("--skill", default=None)
    ap.add_argument("--text", default=None)
    ap.add_argument("--add", action="append")
    ap.add_argument("--path", action="append")
    ap.add_argument("--dest", default=None)
    ap.add_argument("--now", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    root = vk.find_vault(args.vault)
    now = vk.parse_now(args.now)
    fn = {"repeats": cmd_repeats, "skills": cmd_skills, "gitignore": cmd_gitignore, "scan": cmd_scan,
          "move-out": cmd_move_out, "save-points": cmd_save_points, "log": cmd_log}[args.cmd]
    try:
        return fn(args, root, now)
    except (vk.Refused, vk.ChangedUnderUs, OSError) as e:
        name = getattr(e, "filename", None)
        rel = vk.rel_of(root, name) if isinstance(name, str) and name else "a file"
        print(vk.failure_line(e, rel) + " This step stopped there. Tell the owner, and do not retry it in a loop.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
