"""Compare a vault with the new template and with fingerprints of earlier template versions.

WHAT IT IS FOR
  The update-vault skill uses this to tell, file by file, what the owner never
  touched (safe to replace) from what the owner wrote or changed (never
  overwritten). It needs no history of the template: earlier versions are
  recognized by fingerprints (SHA-256 hashes) kept in known-versions.json next
  to this file. A fingerprint holds no text, only a check value.

HOW TO RUN IT (from the vault folder, with Python 3.9 or newer)
  python match_known.py compare <vault folder> --template <new template folder>
      Prints a plain list: what is new, what can be replaced, what is the
      owner's, what to merge, and what to point out.
  python match_known.py record <template folder> <version label>
      For whoever releases a new version of the template: prints the
      fingerprints of that folder, to add to known-versions.json.

CLAUDE.md SECTIONS
  Each section of CLAUDE.md (split at its "## " headings) has two kinds of
  fingerprint per earlier version: one for the whole section, and one per line
  (claude_section_lines). The per-line ones let compare spot a section that is
  exactly an earlier version's built-in section with lines the owner added (every
  built-in line still there, word for word and in the same order, plus one or
  more lines), and list those lines. Line endings never count. For the per-line
  fingerprints, blank lines are left out (they only space paragraphs) and spaces
  or tabs at the end of a line are ignored; spaces at the start of a line count.
  Only plain spaces and tabs: any other space character (such as a no-break
  space) is part of the line. So a section that differs only in blank lines or
  trailing spaces, or that has a built-in line removed, changed or moved, gets
  the owner's-text verdict as before. Only versions at or after the newest one
  the vault's untouched files still match are tried: a vault on a later version
  whose owner removed a line only that version has is not taken for an older
  version plus lines, so the removed line is not put back. (A whole section that
  is exactly an older version's has the same limit, as before.)

SAFETY
  Read only. It never writes, moves or deletes a file, never uses the network,
  and prints only file names, section names and short lines from the vault's
  own files, except that a line the owner added to a built-in CLAUDE.md section,
  and the line it came after, are printed whole. Standard library only.
"""

import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKIP_TOP = {".git", ".github", "outputs", "archives", ".trash", "node_modules"}
SKIP_NAMES = {".DS_Store", "Thumbs.db", "settings.local.json", "workspace.json", "workspace-mobile.json",
              "graph.json", "HANDOFF.md"}

# How each file of the template is treated. Anything the template ships that is
# in neither list is a "seeded" note: replaced only while it is still exactly an
# earlier template version, otherwise it is the owner's and left alone.
SYSTEM_FILES = {"README.md", "INSTALL.md", "HOW-IT-WORKS.md", "LICENSE", "projects/_TEMPLATE.md",
                "playbooks/_TEMPLATE.md", "brand/README.md", "references/README.md"}
SYSTEM_PREFIXES = (".claude/hooks/", ".claude/skills/")
MERGED_FILES = {".claude/settings.json", "CLAUDE.md", "skills-registry.md", ".gitignore", "projects/README.md",
                "playbooks/README.md", ".obsidian/app.json"}


def norm_bytes(data):
    """Line endings and a leading byte-order mark never count as a change."""
    if data.startswith(b"\xef\xbb\xbf"):
        data = data[3:]
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def file_hash(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(norm_bytes(fh.read())).hexdigest()


def text_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_text(path):
    try:
        with open(path, "rb") as fh:
            return norm_bytes(fh.read()).decode("utf-8", errors="replace")
    except OSError:
        return ""


def walk(root):
    out = []
    for dp, dns, fns in os.walk(root):
        rel_dir = os.path.relpath(dp, root).replace(os.sep, "/")
        if rel_dir == ".":
            dns[:] = [d for d in dns if d not in SKIP_TOP]
        dns[:] = [d for d in dns if d != "__pycache__"]
        for f in fns:
            if f in SKIP_NAMES or f.endswith((".pyc", ".tmp")):
                continue
            if rel_dir == "." and f == ".git":
                continue  # a git worktree's pointer file: the template's own plumbing, never shipped
            rel = f if rel_dir == "." else rel_dir + "/" + f
            out.append(rel)
    return sorted(out)


def sections(text):
    """CLAUDE.md split at its "## " headings. The part above the first heading is "(top)"."""
    out = []
    name, lines = "(top)", []
    for line in text.split("\n"):
        if line.startswith("## "):
            out.append((name, lines))
            name, lines = line[3:].strip(), [line]
        else:
            lines.append(line)
    out.append((name, lines))
    result = []
    for name, lines in out:
        while lines and not lines[-1].strip():
            lines = lines[:-1]
        result.append((name, "\n".join(lines)))
    return result


def section_starts(text):
    """The line number (from 1) where each of sections(text) starts, in the same order."""
    starts = [1]
    for i, line in enumerate(text.split("\n")):
        if line.startswith("## "):
            starts.append(i + 1)
    return starts


def line_hashes(body):
    """Per-line fingerprints of one section: one hash per line with words, in order. Blank lines are left out and
    spaces or tabs at the end of a line are ignored (see CLAUDE.md SECTIONS above)."""
    return [text_hash(ln.rstrip(" \t")) for ln in body.split("\n") if ln.strip(" \t")]


def lines_added(body, fps, name=""):
    """Is this section the built-in section with these per-line fingerprints, plus lines the owner added?

    Every built-in line must still be there, word for word and in the same order (a line may have the owner's name
    in place of {{YOUR_NAME}}), with at least one line more. Returns (name_filled, added) or None. Each added item is
    (index of the line in body, its text without trailing spaces, the line with words just above it or None when it
    came first, whether that line above is itself an added line, whether a blank line sits right above it)."""
    j = 0
    filled = False
    added = []
    prev, prev_added, blank_above = None, False, False
    for i, ln in enumerate(body.split("\n")):
        s = ln.rstrip(" \t")
        if not s:
            blank_above = True
            continue
        if j < len(fps) and text_hash(s) == fps[j]:
            j += 1
            prev_added = False
        elif j < len(fps) and name and text_hash(s.replace(name, "{{YOUR_NAME}}")) == fps[j]:
            j += 1
            filled = True
            prev_added = False
        else:
            added.append((i, s, prev, prev_added, blank_above))
            prev_added = True
        prev, blank_above = s, False
    if j < len(fps) or not added:
        return None
    return filled, added


def version_floor(sorted_files):
    """Where in the list of earlier versions the vault's own version starts: the newest version any of its untouched
    files (or merged files still exactly as shipped) matches. A file that never changed between versions matches the
    first of them, so this is the oldest the vault can be. 0 when no file says."""
    order = [v.get("label", "?") for v in sorted_files["known"]]
    seen = set(sorted_files["labels"].values())
    seen.update(st[len("version "):] for st in sorted_files["merge_status"].values() if st.startswith("version "))
    return max([order.index(lb) for lb in seen if lb in order] or [0])


def built_in_plus(sec, body, known, name=""):
    """The closest earlier version whose built-in section `sec` this section is, plus lines the owner added:
    (label, name_filled, added), or None. The fewest added lines wins; on a tie, the first version listed. compare
    passes only the versions from the vault's own version on (see version_floor)."""
    best = None
    for v in known:
        fps = v.get("claude_section_lines", {}).get(sec)
        if not fps:
            continue
        found = lines_added(body, fps, name)
        if found and (best is None or len(found[1]) < len(best[2])):
            best = (v.get("label", "?"), found[0], found[1])
    return best


def added_line_note(start, item):
    """One printed line for an added line: where it is in the vault's file, its text, and what it came right after."""
    i, text, prev, prev_added, blank_above = item
    if prev is None:
        where = "it came first in the section"
    elif prev_added:
        where = "it came right after the owner's line above"
    else:
        where = "it came right after: \"" + prev + "\""
    return ("line " + str(start + i) + ": \"" + text + "\" (" + ("a blank line above it; " if blank_above else "")
            + where + ")")


def owner_name(text):
    m = re.match(r"#\s+(.+?)'s\s", text)
    return m.group(1).strip() if m and "{{" not in m.group(1) else ""


def rule_lines(text):
    """Taste rules: "- [scope] the thing -> the principle". Wikilink lines ("- [[note]]") are not rules."""
    return [ln.strip() for ln in text.split("\n") if re.match(r"- \[[^\[]", ln.strip())]


def category(rel):
    if rel in MERGED_FILES:
        return "merged"
    if rel in SYSTEM_FILES or rel.startswith(SYSTEM_PREFIXES):
        return "system"
    return "seeded"


def load_known(path):
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return [v for v in data.get("versions", []) if isinstance(v, dict)]


def record(folder, label):
    files = {}
    for rel in walk(folder):
        files[rel] = file_hash(os.path.join(folder, rel))
    text = read_text(os.path.join(folder, "CLAUDE.md"))
    secs = {name: text_hash(body) for name, body in sections(text)} if text else {}
    sec_lines = {name: line_hashes(body) for name, body in sections(text)} if text else {}
    taste = read_text(os.path.join(folder, "memory", "taste.md"))
    seeded_rules = [text_hash(ln) for ln in rule_lines(taste)]
    # The memory index's line about its own size. An older one told Claude to merge or shorten lines on its
    # own, so compare points it out for a word-for-word swap (see OLD MEMORY HEADER LINE).
    house = {}
    mem_rel = "memory/claude/MEMORY.md"
    for ln in read_text(os.path.join(folder, mem_rel)).split("\n"):
        if ln.startswith("## "):
            break
        if ln.strip().startswith("- Keep this file under"):
            house.setdefault(mem_rel, []).append(text_hash(ln.strip()))
    print(json.dumps({"label": label, "files": files, "claude_sections": secs, "claude_section_lines": sec_lines,
                      "seeded_taste_rules": seeded_rules, "house_rule_lines": house}, indent=2, sort_keys=True))


def logical(rel):
    """A template copy kept inside the vault has its rule files renamed (see the skill): read them back."""
    if rel == "CLAUDE.new.md":
        return "CLAUDE.md"
    if rel.startswith("dot-claude/"):
        return ".claude/" + rel[len("dot-claude/"):]
    return rel


def sort_files(vault, template, known_path):
    """Sort every file into the groups of the update skill's Step 2. Read only.

    Returns a dict: "groups" maps each group name to a sorted list of paths (a
    retired skill is its folder, ending in "/"), "labels" gives the earlier
    version a file still matches, "missing_merge" lists merged files the vault
    lacks, "merge_status" says for each merged file the vault has whether it is
    already the new version ("same"), still exactly as an earlier version
    shipped it ("version <label>": nothing of the owner's in it), or holds the
    owner's text or settings ("owner"), "tmpl_paths" maps each logical path to
    its path in the template copy, and "known" is the list of earlier versions.
    copy_files.py uses it too.
    """
    known = load_known(known_path)
    tmpl_paths = {logical(r): r for r in walk(template)}
    tmpl_files = set(tmpl_paths)
    vault_files = set(walk(vault))
    known_files = set()
    for v in known:
        known_files.update(v.get("files", {}).keys())

    def earlier_match(rel, h):
        for v in known:
            if v.get("files", {}).get(rel) == h:
                return v.get("label", "?")
        return ""

    # Skill folders and hook files the template ships, now or in any earlier version.
    def skill_of(rel):
        parts = rel.split("/")
        return parts[2] if rel.startswith(".claude/skills/") and len(parts) > 3 else ""

    template_skills = {skill_of(r) for r in tmpl_files | known_files if skill_of(r)}
    template_hooks = {r for r in tmpl_files | known_files if r.startswith(".claude/hooks/")}

    groups = {k: [] for k in ("new", "same", "replace", "ask", "retire", "seed_replace", "seed_keep", "merge",
                              "owners_hooks", "owners_skills", "owners_skill_files")}
    labels = {}
    missing_merge = []
    merge_status = {}

    for rel in sorted(tmpl_files):
        cat = category(rel)
        if cat == "merged":
            groups["merge"].append(rel)
            if rel not in vault_files:
                missing_merge.append(rel)
                continue
            h = file_hash(os.path.join(vault, rel))
            if h == file_hash(os.path.join(template, tmpl_paths[rel])):
                merge_status[rel] = "same"
            else:
                label = earlier_match(rel, h)
                merge_status[rel] = "version " + label if label else "owner"
            continue
        if rel not in vault_files:
            groups["new"].append(rel)
            continue
        h = file_hash(os.path.join(vault, rel))
        if h == file_hash(os.path.join(template, tmpl_paths[rel])):
            groups["same"].append(rel)
            continue
        label = earlier_match(rel, h)
        if label:
            labels[rel] = label
        if cat == "system":
            groups["replace" if label else "ask"].append(rel)
        else:
            groups["seed_replace" if label else "seed_keep"].append(rel)

    retired_skills = set()
    for rel in sorted(vault_files - tmpl_files):
        if rel.startswith(".claude/hooks/"):
            if rel in template_hooks:
                label = earlier_match(rel, file_hash(os.path.join(vault, rel)))
                if label:
                    labels[rel] = label
                groups["retire"].append(rel)
            else:
                groups["owners_hooks"].append(rel)
        elif rel.startswith(".claude/skills/"):
            name = skill_of(rel)
            if not name:
                continue
            if name not in template_skills:
                groups["owners_skills"].append(".claude/skills/" + name + "/")
            elif not any(skill_of(t) == name for t in tmpl_files):
                retired_skills.add(name)
            elif rel not in known_files:
                groups["owners_skill_files"].append(rel)
    for name in sorted(retired_skills):
        groups["retire"].append(".claude/skills/" + name + "/")
    groups["owners_skills"] = sorted(set(groups["owners_skills"]))
    return {"groups": groups, "labels": labels, "missing_merge": missing_merge, "merge_status": merge_status,
            "tmpl_paths": tmpl_paths, "known": known}


def gitignore_missing(vault_file, tmpl_file):
    """The lines the new .gitignore has that the vault's lacks, in the new file's order, each with the comment
    lines just above it. None when either file cannot be read as text (then Claude merges it by hand)."""
    try:
        with open(vault_file, "rb") as fh:
            have_text = norm_bytes(fh.read()).decode("utf-8")
        with open(tmpl_file, "rb") as fh:
            new_text = norm_bytes(fh.read()).decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    have = {ln.strip() for ln in have_text.split("\n") if ln.strip()}
    out, added, comments = [], set(), []
    for ln in new_text.split("\n"):
        s = ln.strip()
        if not s:
            comments = []
        elif s.startswith("#"):
            comments.append(ln.rstrip())
        else:
            if s not in have and s not in added:
                out.extend(c for c in comments if c.strip() not in have and c not in out)
                out.append(ln.rstrip())
                added.add(s)
            comments = []
    return out


def merge_note(rel, status, missing=None):
    """Why a merged file is in the MERGE group, and what Step 5 does with it."""
    if rel == ".gitignore" and status != "same" and missing is not None:
        if not [ln for ln in missing if not ln.startswith("#")]:
            return " (already has every line of the new version: nothing to do)"
        return " (the copy helper adds the new lines; nothing is removed)"
    if status == "same":
        return " (already the new version: nothing to do)"
    if status.startswith("version "):
        return (" (still exactly as " + status + " shipped it, nothing of the owner's: the copy helper takes the new "
                "one)")
    return " (has the owner's text or settings: merge by hand, starting from the vault's copy)"


def compare(vault, template, known_path):
    sorted_files = sort_files(vault, template, known_path)
    labels = sorted_files["labels"]
    tmpl_paths = sorted_files["tmpl_paths"]
    known = sorted_files["known"]
    groups = {k: list(v) for k, v in sorted_files["groups"].items()}
    # The printed list says why each file is where it is.
    groups["merge"] = [r + (" (not in the vault yet: the copy helper adds it)" if r in sorted_files["missing_merge"]
                            else merge_note(r, sorted_files["merge_status"].get(r, "owner"),
                                            gitignore_missing(os.path.join(vault, ".gitignore"),
                                                              os.path.join(template, tmpl_paths.get(".gitignore",
                                                                                                    ".gitignore")))
                                            if r == ".gitignore" else None))
                       for r in groups["merge"]]
    groups["replace"] = [r + " (version " + labels[r] + ", never edited)" for r in groups["replace"]]
    groups["seed_replace"] = [r + " (still the untouched version " + labels[r] + ")" for r in groups["seed_replace"]]
    groups["retire"] = [r + (" (the whole folder)" if r.endswith("/") else
                             " (version " + labels[r] + ", never edited)" if r in labels else
                             " (you changed it: carry your additions over)") for r in groups["retire"]]

    print("Vault:    " + os.path.abspath(vault))
    print("Template: " + os.path.abspath(template))
    print("Earlier versions recognized: " + (", ".join(v.get("label", "?") for v in known) or "none"))
    titles = [
        ("new", "NEW: the template has these and the vault does not (add them)"),
        ("replace", "REPLACE: system files the owner never edited (an older copy goes to the backup)"),
        ("ask", "ASK: system files the owner changed (keep theirs, take the new one, or carry their additions in)"),
        ("retire", "RETIRE: old system files the new version no longer has (move them to the backup)"),
        ("seed_replace", "STARTER NOTES STILL UNTOUCHED: replace with the new version"),
        ("seed_keep", "THE OWNER'S NOTES: never overwritten"),
        ("merge", "MERGE: new template text in, the owner's text kept"),
        ("owners_hooks", "THE OWNER'S OWN HOOKS: never touched, and their settings entries stay"),
        ("owners_skills", "THE OWNER'S OWN SKILLS: never touched"),
        ("owners_skill_files", "THE OWNER'S FILES INSIDE TEMPLATE SKILL FOLDERS: left where they are"),
        ("same", "ALREADY THE NEW VERSION: nothing to do"),
    ]
    for key, title in titles:
        if groups[key]:
            print("")
            print(title + ":")
            for item in groups[key]:
                print("  - " + item)

    # CLAUDE.md, section by section
    vtext = read_text(os.path.join(vault, "CLAUDE.md"))
    ttext = read_text(os.path.join(template, tmpl_paths.get("CLAUDE.md", "CLAUDE.md")))
    if vtext and ttext:
        name = owner_name(vtext)
        known_secs = {}
        for v in known:
            for sec, h in v.get("claude_sections", {}).items():
                known_secs.setdefault(h, (sec, v.get("label", "?")))
        new_secs = [s for s, _ in sections(ttext)]
        floor = version_floor(sorted_files)
        print("")
        print("CLAUDE.md, section by section (the vault's sections):")
        vault_secs = sections(vtext)
        for (sec, body), start in zip(vault_secs, section_starts(vtext)):
            h = text_hash(body)
            verdict = ""
            notes_below = []
            if h in known_secs:
                verdict = "template text (version " + known_secs[h][1] + "): take the new version of it"
            elif name:
                h2 = text_hash(body.replace(name, "{{YOUR_NAME}}"))
                if h2 in known_secs:
                    verdict = ("template text with the owner's name filled in (version " + known_secs[h2][1]
                               + "): take the new version, and put \"" + name + "\" back in place of {{YOUR_NAME}}")
            if not verdict and (sec in new_secs or sec == "(top)"):
                # An earlier version's built-in section with lines the owner added: the new wording, plus their lines.
                plus = built_in_plus(sec, body, known[floor:], name)
                if plus:
                    label, filled, added = plus
                    one = len(added) == 1
                    verdict = ("built-in text" + (" with the owner's name filled in" if filled else "") + " (version "
                               + label + ") plus " + ("1 line" if one else str(len(added)) + " lines")
                               + " the owner added: take the new version of this section, "
                               + ("put \"" + name + "\" back in place of {{YOUR_NAME}}, " if filled else "")
                               + "then put " + ("this line" if one else "these lines") + " back word for word:")
                    notes_below = [added_line_note(start, item) for item in added]
            if not verdict:
                if sec in new_secs or sec == "(top)":
                    verdict = "the owner's text: keep it, adding only new lines that do not contradict it"
                else:
                    verdict = ("the owner's text, under a heading the new version does not have: keep it if the "
                               "owner wrote it")
            print("  - " + sec + ": " + verdict)
            for note in notes_below:
                print("      " + note)
        missing = [s for s in new_secs if s not in {x for x, _ in vault_secs}]
        if missing:
            print("  - New sections to add: " + ", ".join(missing))

    # Things to point out
    notes = []
    taste = read_text(os.path.join(vault, "memory", "taste.md"))
    if taste:
        seeds = set()
        for v in known:
            seeds.update(v.get("seeded_taste_rules", []))
        tmpl_rules = {text_hash(ln) for ln in rule_lines(read_text(os.path.join(template, "memory", "taste.md")))}
        hits = []
        for i, ln in enumerate(taste.split("\n"), 1):
            s = ln.strip()
            if re.match(r"- \[[^\[]", s) and text_hash(s) in seeds and text_hash(s) not in tmpl_rules:
                hits.append("line " + str(i) + ": " + s[:110])
        if hits:
            notes.append(("memory/taste.md has rules that came with an older template, not from the owner "
                          "(offer to keep or remove them):", hits))
    for rel in ("brand/brand.md",):
        text = read_text(os.path.join(vault, rel))
        if not text:
            continue
        rules = set()
        for v in known:
            rules.update(v.get("house_rule_lines", {}).get(rel, []))
        hits = []
        for i, ln in enumerate(text.split("\n"), 1):
            if ln.strip() and text_hash(ln.strip()) in rules:
                hits.append("line " + str(i) + ": " + ln.strip()[:110])
        if hits:
            notes.append((rel + " still has design rules from an older template, not from the owner "
                           "(offer to keep or remove them):", hits))
    # The older memory index told Claude to merge, shorten or move lines on its own, rules included.
    mem_rel = "memory/claude/MEMORY.md"
    mem = read_text(os.path.join(vault, mem_rel))
    if mem:
        old_lines = set()
        for v in known:
            old_lines.update(v.get("house_rule_lines", {}).get(mem_rel, []))
        new_line = ""
        for ln in read_text(os.path.join(template, mem_rel)).split("\n"):
            if ln.strip().startswith("- Keep this file under"):
                new_line = ln.strip()
                break
        hits = []
        for i, ln in enumerate(mem.split("\n"), 1):
            if ln.startswith("## "):
                break
            if ln.strip() and text_hash(ln.strip()) in old_lines and ln.strip() != new_line:
                hits.append("line " + str(i) + ": " + ln.strip()[:110])
        if hits and new_line:
            notes.append(("OLD MEMORY HEADER LINE: " + mem_rel + " still has the older template's line about its "
                          "size, which told Claude to merge, shorten or move lines on its own. In Step 5, swap just "
                          "that line for this one, word for word, and change nothing else in the file: " + new_line,
                          hits))
    conn = read_text(os.path.join(vault, "connections.md"))
    conn_replaced = any(x.startswith("connections.md ") for x in groups["seed_replace"])
    if conn and not conn_replaced and "| Can Claude reach it? |" not in conn and re.search(
            r"\|\s*mcp\s*\||not yet connected", conn):
        notes.append(("connections.md uses the older table layout. It is the owner's file and stays as it is; "
                      "the new rules read both layouts.", []))
    if notes:
        print("")
        print("POINT OUT:")
        for title, lines in notes:
            print("  - " + title)
            for ln in lines:
                print("      " + ln)

    # The update steps themselves. Which copy to follow is the owner's call, never this
    # checker's: it only says the download has newer steps, and gives one plain question.
    own_steps = os.path.join(vault, ".claude", "skills", "update-vault", "SKILL.md")
    new_steps = tmpl_paths.get(".claude/skills/update-vault/SKILL.md")
    if new_steps and os.path.isfile(own_steps):
        new_path = os.path.abspath(os.path.join(template, new_steps))
        if file_hash(own_steps) != file_hash(new_path):
            print("")
            print("NEWER UPDATE STEPS: this download has newer update steps than the vault's own copy ("
                  + new_path + "). The newer steps also clean up the vault in this same run, with one list and "
                  "one yes, and end with a short report in plain words. Which steps to use is the owner's choice. "
                  "If their message already said to use the update steps in the new download, they have chosen. "
                  "If not, ask them this one question before the change list, and wait for the answer: "
                  "\"The new version comes with newer update steps. They also clean up your vault in this same "
                  "go and end with a short report in plain words. Nothing changes until you say yes to the list. "
                  "Use the new steps? (yes or no; I suggest yes)\"")


def main(argv):
    if len(argv) >= 3 and argv[1] == "record":
        label = argv[3] if len(argv) > 3 else "?"
        record(argv[2], label)
        return 0
    if len(argv) >= 3 and argv[1] == "compare":
        vault = argv[2]
        template = None
        known_path = os.path.join(HERE, "known-versions.json")
        rest = argv[3:]
        while rest:
            a = rest.pop(0)
            if a == "--template" and rest:
                template = rest.pop(0)
            elif a == "--known" and rest:
                known_path = rest.pop(0)
        if not template:
            template = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
        compare(vault, template, known_path)
        return 0
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
