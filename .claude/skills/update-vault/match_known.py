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

SAFETY
  Read only. It never writes, moves or deletes a file, never uses the network,
  and prints only file names, section names and short lines from the vault's
  own files. Standard library only.
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
    taste = read_text(os.path.join(folder, "memory", "taste.md"))
    seeded_rules = [text_hash(ln) for ln in rule_lines(taste)]
    print(json.dumps({"label": label, "files": files, "claude_sections": secs, "seeded_taste_rules": seeded_rules,
                      "house_rule_lines": {}}, indent=2, sort_keys=True))


def logical(rel):
    """A template copy kept inside the vault has its rule files renamed (see the skill): read them back."""
    if rel == "CLAUDE.new.md":
        return "CLAUDE.md"
    if rel.startswith("dot-claude/"):
        return ".claude/" + rel[len("dot-claude/"):]
    return rel


def compare(vault, template, known_path):
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

    for rel in sorted(tmpl_files):
        cat = category(rel)
        if cat == "merged":
            groups["merge"].append(rel + ("" if rel in vault_files else " (not in the vault yet: add it)"))
            continue
        if rel not in vault_files:
            groups["new"].append(rel)
            continue
        h = file_hash(os.path.join(vault, rel))
        if h == file_hash(os.path.join(template, tmpl_paths[rel])):
            groups["same"].append(rel)
            continue
        label = earlier_match(rel, h)
        if cat == "system":
            if label:
                groups["replace"].append(rel + " (version " + label + ", never edited)")
            else:
                groups["ask"].append(rel)
        else:
            if label:
                groups["seed_replace"].append(rel + " (still the untouched version " + label + ")")
            else:
                groups["seed_keep"].append(rel)

    retired_skills = set()
    for rel in sorted(vault_files - tmpl_files):
        if rel.startswith(".claude/hooks/"):
            if rel in template_hooks:
                h = file_hash(os.path.join(vault, rel))
                label = earlier_match(rel, h)
                groups["retire"].append(rel + (" (version " + label + ", never edited)" if label
                                               else " (you changed it: carry your additions over)"))
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
        groups["retire"].append(".claude/skills/" + name + "/ (the whole folder)")
    groups["owners_skills"] = sorted(set(groups["owners_skills"]))

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
        print("")
        print("CLAUDE.md, section by section (the vault's sections):")
        vault_secs = sections(vtext)
        for sec, body in vault_secs:
            h = text_hash(body)
            verdict = ""
            if h in known_secs:
                verdict = "template text (version " + known_secs[h][1] + "): take the new version of it"
            elif name:
                h2 = text_hash(body.replace(name, "{{YOUR_NAME}}"))
                if h2 in known_secs:
                    verdict = ("template text with the owner's name filled in (version " + known_secs[h2][1]
                               + "): take the new version, and put \"" + name + "\" back in place of {{YOUR_NAME}}")
            if not verdict:
                if sec in new_secs or sec == "(top)":
                    verdict = "the owner's text: keep it, adding only new lines that do not contradict it"
                else:
                    verdict = ("the owner's text, under a heading the new version does not have: keep it if the "
                               "owner wrote it")
            print("  - " + sec + ": " + verdict)
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
