"""Measure what this vault costs every chat, and what has grown past its budget.
Read only: it never changes a file in the vault.

  python3 measure.py --vault .                 the plain report
  python3 measure.py --vault . --json          the same numbers as JSON
  python3 measure.py --vault . --save-before   also keeps these numbers in this
                                               computer's temp folder for --compare
  python3 measure.py --vault . --compare       before and after, side by side
  --doctor   also runs the vault check (doctor.py) and lists what it flags
  --no-briefing   skips running the session briefing
  --today YYYY-MM-DD   counts the age of old entries from this day (for tests)

"Rough tokens" is characters divided by 4, the usual rule of thumb. "Pages" is
characters divided by 3,000: say pages to the owner, never tokens.

"Helper descriptions" counts each helper type in .claude/agents/ (such as
lean-worker): Claude Code lists its name, description and tools in every chat,
so the owner's chat can start one.

When the vault has no memory/claude/MEMORY.md, the memory count is the index
Claude Code reads from its own folder for this vault (or from
"autoMemoryDirectory" in .claude/settings.local.json), so the "before" number
is what Claude really read.
"""

import sys
sys.dont_write_bytecode = True  # never leave a __pycache__ folder in the vault
import argparse
import datetime as dt
import json
import os
import re
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vaultkit as vk  # noqa: E402
import tidy  # noqa: E402
import memory_index as mi  # noqa: E402
import fixes  # noqa: E402

BASE_HOOKS = {"SessionStart": ["session_pulse.py"],
              "UserPromptSubmit": ["auto_capture.py", "brand_guard.py", "vault_recall.py"],
              "Stop": ["brain_log.py"]}


def run_hook(root, script, payload, timeout=25):
    run_sh = os.path.join(root, ".claude", "hooks", "run.sh")
    if not os.path.isfile(run_sh):
        return None
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = root
    # Any note a helper keeps for itself goes to this computer's temp folder, never the vault.
    scratch = os.path.join(vk.temp_dir_for(root), "hooks")
    env["VAULT_HOOKS_TEMP"] = scratch
    env["VAULT_HOOKS_STATE_DIR"] = os.path.join(scratch, "state")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    # The briefing's one-time offer of a first cleanup is not a cost every chat carries: leave it out.
    env["VAULT_PULSE_MEASURE"] = "1"
    try:
        r = subprocess.run(["sh", run_sh, script], input=json.dumps(payload).encode("utf-8"), cwd=root, env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    except Exception:
        return None
    return r.stdout.decode("utf-8", "replace")


def briefing_chars(root):
    out = run_hook(root, "session_pulse.py", {"hook_event_name": "SessionStart", "source": "startup",
                                              "session_id": "optimize-vault-measure"})
    if not out:
        return None
    try:
        return len(json.loads(out)["hookSpecificOutput"]["additionalContext"])
    except Exception:
        return None


def doctor_fixes(root):
    out = run_hook(root, "doctor.py", {}, timeout=120)
    if out is None:
        return None
    return [l[len("[fix] "):].strip() for l in out.splitlines() if l.startswith("[fix] ")]


def hooks_missing(root):
    path = os.path.join(root, ".claude", "settings.json")
    data = vk.load_json(path, None)
    out = []
    if not os.path.isfile(os.path.join(root, ".claude", "hooks", "run.sh")):
        out.append(".claude/hooks/run.sh (no helper can start without it)")
    if not isinstance(data, dict):
        out.append(".claude/settings.json is missing or broken, so no helper is switched on")
        return out
    hooks = data.get("hooks") or {}
    cmds = []
    for event, groups in (hooks.items() if isinstance(hooks, dict) else []):
        for g in groups if isinstance(groups, list) else []:
            for h in (g.get("hooks") or []) if isinstance(g, dict) else []:
                if isinstance(h, dict):
                    cmds.append((event, str(h.get("command") or "")))
    for event, scripts in BASE_HOOKS.items():
        for s in scripts:
            if not any(e == event and s in c for e, c in cmds):
                out.append(s + " is not switched on in .claude/settings.json")
            elif not os.path.isfile(os.path.join(root, ".claude", "hooks", s)):
                out.append(".claude/hooks/" + s + " is missing")
    for e, c in cmds:
        m = re.search(r"run\.sh\"?\s+([\w.-]+\.py)", c)
        if m and not os.path.isfile(os.path.join(root, ".claude", "hooks", m.group(1))):
            item = ".claude/hooks/" + m.group(1) + " is missing"
            if item not in out:
                out.append(item)
    return out


KIT_DOCS = ("README.md", "INSTALL.md", "HOW-IT-WORKS.md", "LICENSE", "LICENSE.md", "CHANGELOG.md")
PAGE_CHARS = 3000


def pages(chars):
    """Pages of about 3,000 characters, one decimal place: the number the owner hears."""
    return round(chars / float(PAGE_CHARS), 1)


def outside_memory_index(root):
    """The memory index Claude Code reads for this vault when the vault has none of its own:
    the folder named in .claude/settings.local.json, else Claude Code's own folder for this path."""
    local = vk.load_json(os.path.join(root, ".claude", "settings.local.json"), {})
    places = []
    if isinstance(local, dict) and local.get("autoMemoryDirectory"):
        places.append(os.path.expanduser(str(local["autoMemoryDirectory"])))
    base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    places.append(os.path.join(base, "projects", re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(root)), "memory"))
    inside = os.path.realpath(os.path.join(root, mi.MEM_DIR))
    for d in places:
        if os.path.realpath(d) == inside:
            continue
        path = os.path.join(d, "MEMORY.md")
        if os.path.isfile(path):
            return path
    return None


def memory_load(text):
    lines = text.split("\n")
    part = "\n".join(lines[:vk.MEMORY_LOAD_LINES])
    b = part.encode("utf-8")[:vk.MEMORY_LOAD_BYTES]
    return len(b.decode("utf-8", errors="ignore"))


def agent_listing(root):
    """Characters of the helper types in .claude/agents/ that every chat loads: Claude Code lists each one
    as "name: description (Tools: ...)" so the chat can start it."""
    folder = os.path.join(root, ".claude", "agents")
    try:
        names = sorted(n for n in os.listdir(folder) if n.endswith(".md"))
    except OSError:
        return 0
    total = 0
    for n in names:
        text = vk.read_text(os.path.join(folder, n)) or ""
        desc, _, _, name = vk.description_of(text)
        if not desc:
            continue
        head = text.split("\n---", 1)[0]
        m = re.search(r"(?m)^tools:[ \t]*(.+)$", head)
        tools = m.group(1).strip() if m else ""
        total += len(name or n[:-3]) + 2 + len(desc) + (len(" (Tools: " + tools + ")") if tools else 0)
    return total


def second_rules(root):
    out = []
    for rel in vk.walk_files(root):
        name = rel.split("/")[-1]
        if name in ("CLAUDE.md", "CLAUDE.local.md") and rel not in ("CLAUDE.md", "CLAUDE.local.md", ".claude/CLAUDE.md"):
            out.append(rel)
        elif "/.claude/skills/" in "/" + rel and not rel.startswith(".claude/") and name == "SKILL.md":
            out.append(rel)
    return out


def measure(root, briefing=True, doctor=False, today=None):
    today = today or dt.date.today()
    data = {"vault": root, "when": dt.datetime.now().strftime("%Y-%m-%d %H:%M")}
    every = {}
    for rel in ("CLAUDE.md", "CLAUDE.local.md", ".claude/CLAUDE.md"):
        t = vk.read_text(os.path.join(root, rel))
        if t is not None:
            every[rel] = len(t)
    mem = vk.read_text(os.path.join(root, mi.INDEX_REL))
    outside = None
    if mem is None:
        outside = outside_memory_index(root)
        loaded = memory_load(vk.read_text(outside) or "") if outside else 0
        mem = ""
    else:
        loaded = memory_load(mem)
    every["memory/claude/MEMORY.md"] = loaded
    sk = fixes.skills_report(root)
    every["skill descriptions"] = sum(s["listing_chars"] for s in sk)
    helpers = agent_listing(root)
    if helpers:
        every["helper descriptions"] = helpers
    b = briefing_chars(root) if briefing else None
    if b is not None:
        every["session briefing"] = b
    total = sum(every.values())
    data["every_chat"] = {"parts": every, "chars": total, "tokens": vk.tokens(total), "pages": pages(total)}
    data["memory_outside_vault"] = bool(outside)
    claude_chars = every.get("CLAUDE.md", 0)
    data["claude_md"] = {"chars": claude_chars, "over": claude_chars > vk.CLAUDE_WARN}
    plan = mi.make_plan(root, today)
    data["memory_index"] = {"lines": vk.count_lines(mem), "chars": len(mem),
                            "over": vk.count_lines(mem) > vk.MEMORY_LINES or len(mem) > vk.MEMORY_CHARS,
                            "counts": plan.get("counts", {}),
                            "movable": sum(len(g["items"]) for g in plan.get("groups", []))}
    keeps = {k: vk.keep_titles(root, k) for k in tidy.KINDS}
    dt_ = vk.read_text(os.path.join(root, tidy.LIVE["decisions"]))
    data["decisions"] = tidy.decisions_state(dt_, today, keeps["decisions"]) if dt_ is not None else None
    tt = vk.read_text(os.path.join(root, tidy.LIVE["tasks"]))
    data["tasks"] = tidy.tasks_state(tt) if tt is not None else None
    it = vk.read_text(os.path.join(root, tidy.LIVE["inbox"]))
    data["inbox"] = tidy.inbox_state(it) if it is not None else None
    big = []
    for rel in vk.notes(root):
        try:
            s = os.path.getsize(os.path.join(root, rel))
        except OSError:
            continue
        if s > vk.NOTE_BIG and rel not in (tidy.LIVE["decisions"],) and rel not in KIT_DOCS:
            big.append({"path": rel, "kb": s // 1024})
    data["big_notes"] = big
    found = fixes.scan(root)
    data["unreadable"] = [f["path"] for f in found if f["kind"] == "could not read"]
    found = [f for f in found if f["kind"] != "could not read"]
    data["secrets"] = [f for f in found if f["kind"] != "media"]
    data["media"] = {"count": sum(1 for f in found if f["kind"] == "media"),
                     "kb": sum(f["size"] for f in found if f["kind"] == "media") // 1024,
                     "big": [f for f in found if f.get("big")]}
    _, missing = fixes.gitignore_missing(root)
    data["gitignore_missing"] = missing
    data["hooks_missing"] = hooks_missing(root)
    data["skills"] = {"over": [s for s in sk if s["status"] == "over budget"],
                      "count": len(sk)}
    _, reps = fixes.find_repeats(root)
    data["repeats"] = {"count": len(reps), "plain": sum(1 for r in reps if not r["rule"]),
                       "chars": sum(len(r["line"]) + 1 for r in reps if not r["rule"]),
                       "lines": [fixes.norm_line(r["line"]) for r in reps]}
    reach = mi.reachable(root)
    notes_all = mi.memory_notes(root)
    data["memory_unreachable"] = [n for n in notes_all if n not in reach]
    data["second_rules"] = second_rules(root)
    st = vk.load_json(os.path.join(root, vk.STATE_REL), {})
    data["last_optimized"] = st.get("last_run") if isinstance(st, dict) else None
    data["save_points_on"] = os.path.isfile(os.path.join(root, vk.SAVE_POINTS_FLAG))
    if doctor:
        data["doctor_fixes"] = doctor_fixes(root)
    # To do: only what a run would really change. A file over budget whose plan moves nothing
    # (kept entries, inbox lines that do not say where they went, done items with an open
    # sub-item) is not on it, and neither is anything the owner chose to leave as is last time.
    movable = {}
    try:
        tp = tidy.make_plans(root, argparse.Namespace(only=None, keep=None, include_unrouted=False), today, today)
        for p in tp:
            movable[p.kind] = 0 if p.refused else len(p.moves)
    except Exception:
        movable = {}
    left = (st.get("floors") or {}).get("left_as_is") if isinstance(st, dict) and isinstance(st.get("floors"), dict) \
        else None
    left = left if isinstance(left, dict) else {}
    now_open = open_items(root, data)
    todo = []
    if data["memory_index"]["over"] and data["memory_index"]["movable"]:
        todo.append("memory index")
    for k in ("decisions", "tasks", "inbox"):
        if data[k] and data[k]["over"] and movable.get(k, 1):
            todo.append(tidy.LIVE[k])
    if data["claude_md"]["over"] and set(now_open["repeats"]) - set(left.get("repeats") or []):
        todo.append("repeated CLAUDE.md lines")
    if set(now_open["skills"]) - set(left.get("skills") or []):
        todo.append("long skill descriptions")
    if set(now_open["files"]) - set(left.get("files") or []):
        todo.append("files to move out")
    if set(now_open["gitignore"]) - set(left.get("gitignore") or []):
        todo.append(".gitignore lines")
    data["to_do"] = todo
    return data


def open_items(root, data=None):
    """What the owner was asked about and may have said no to: secret and big media files, missing
    .gitignore lines, long skill descriptions, CLAUDE.md lines a memory note repeats. Recorded at the
    end of a run, so the next run does not count them as new work."""
    if data is None:
        found = [f for f in fixes.scan(root) if f["kind"] != "could not read"]
        secrets = [f for f in found if f["kind"] != "media"]
        big = [f for f in found if f.get("big")]
        _, missing = fixes.gitignore_missing(root)
        over = [s for s in fixes.skills_report(root) if s["status"] == "over budget"]
        _, reps = fixes.find_repeats(root)
        rep_lines = [fixes.norm_line(r["line"]) for r in reps]
    else:
        secrets, big = data["secrets"], data["media"]["big"]
        missing, over, rep_lines = data["gitignore_missing"], data["skills"]["over"], data["repeats"]["lines"]
    return {"files": sorted(set(f["path"] for f in secrets) | set(f["path"] for f in big)),
            "gitignore": sorted(missing), "skills": sorted(s["skill"] for s in over),
            "repeats": sorted(set(rep_lines))}


def report(d):
    L = []
    e = d["every_chat"]
    L.append("Vault size check (reads only, changes nothing). Rough tokens = characters / 4.")
    L.append("")
    L.append("Loaded into every chat:                  characters   rough tokens")
    for k, v in e["parts"].items():
        name = {"memory/claude/MEMORY.md": "Memory index (MEMORY.md)"}.get(k, k)
        L.append("  %-38s %10s   %12s" % (name, vk.fmt(v), vk.fmt(vk.tokens(v))))
    L.append("  %-38s %10s   %12s" % ("Total", vk.fmt(e["chars"]), vk.fmt(e["tokens"])))
    L.append("  For the owner: about %s pages read before every answer (one page is about 3,000 characters)."
             % e.get("pages", pages(e["chars"])))
    if d.get("memory_outside_vault"):
        L.append("  (The memory count is the list Claude Code keeps outside this vault, because the vault has none.)")
    L.append("")
    m = d["memory_index"]
    L.append("Memory index: %d lines, %s characters (budget %d lines, %s)%s" % (
        m["lines"], vk.fmt(m["chars"]), vk.MEMORY_LINES, vk.fmt(vk.MEMORY_CHARS), ": over" if m["over"] else ": fine"))
    if m.get("counts"):
        L.append("  %d rule lines and %d default lines (these never move), %d plain pointer lines."
                 % (m["counts"].get("rule", 0), m["counts"].get("default", 0), m["counts"].get("pointer", 0)))
    if d["claude_md"]["over"]:
        L.append("CLAUDE.md: %s characters, over the %s budget." % (vk.fmt(d["claude_md"]["chars"]), vk.fmt(vk.CLAUDE_WARN)))
    L.append("")
    L.append("Files that grow:")
    dd = d.get("decisions")
    if dd:
        L.append("  decisions/log.md: %s characters, %d entries, %d older than %d days%s" % (
            vk.fmt(dd["chars"]), dd["entries"], dd["older_than_90_days"], vk.DECISIONS_DAYS,
            ": tidy" if dd["over"] else ": fine"))
    t = d.get("tasks")
    if t:
        L.append("  tasks.md: %d done items (budget %d)%s" % (t["done_items"], vk.TASKS_DONE, ": tidy" if t["over"] else ": fine"))
    i = d.get("inbox")
    if i:
        L.append("  inbox.md: %d lines (budget %d)%s" % (i["lines"], vk.INBOX_LINES, ": tidy" if i["over"] else ": fine"))
    L.append("")
    L.append("Other checks:")
    L.append("  Notes over 40 KB: " + (", ".join("%s (%d KB)" % (b["path"], b["kb"]) for b in d["big_notes"]) or "none"))
    if d["secrets"]:
        L.append("  Secret files or key-looking text in the vault (contents never shown):")
        for s in d["secrets"]:
            L.append("    %s: %s%s%s" % (s["kind"], s["path"], (" line %d" % s["line"]) if s.get("line") else "",
                                        ", saved in git history" if s.get("in_git") else ""))
    else:
        L.append("  Secret files in the vault: none")
    md = d["media"]
    L.append("  Media files outside brand/logos/ and outputs/: %d (%s KB)%s" % (
        md["count"], vk.fmt(md["kb"]), "" if not md["big"] else "; big ones: " + ", ".join(
            "%s (%.1f MB)" % (b["path"], b["size"] / 1048576.0) for b in md["big"])))
    if d.get("unreadable"):
        L.append("  Files this computer would not let it read (left as is): " + ", ".join(d["unreadable"][:6]))
    L.append("  .gitignore missing: " + (", ".join(d["gitignore_missing"]) or "nothing"))
    L.append("  Hooks missing: " + ("; ".join(d["hooks_missing"]) or "none"))
    so = d["skills"]["over"]
    L.append("  Skill descriptions over %d characters: %s" % (
        vk.DESC_WARN, ", ".join("%s (%d)" % (s["skill"], s["chars"]) for s in so) or "none"))
    r = d["repeats"]
    L.append("  CLAUDE.md lines a memory note repeats word for word: %d (%d plain, %s characters)" % (
        r["count"], r["plain"], vk.fmt(r["chars"])))
    if d["memory_unreachable"]:
        L.append("  Memory notes the index does not reach within two links: " + ", ".join(d["memory_unreachable"][:6]))
    if d["second_rules"]:
        L.append("  A second set of rules or skills inside the vault: " + ", ".join(d["second_rules"][:4]))
    if d.get("doctor_fixes") is not None:
        L.append("  Vault check (doctor): " + ("; ".join(d["doctor_fixes"]) or "nothing to fix"))
    L.append("  Save points at the end of each session: " + ("on" if d["save_points_on"] else "off"))
    if d.get("last_optimized"):
        L.append("  Last optimized: " + d["last_optimized"])
    L.append("")
    L.append("To do: " + (", ".join(d["to_do"]) if d["to_do"] else "nothing. The vault is within every budget."))
    return L


def compare(before, after):
    L = ["Before and after (rough tokens = characters / 4):", ""]
    L.append("  %-34s %12s %12s" % ("", "before", "after"))
    keys = sorted(set(before["every_chat"]["parts"]) | set(after["every_chat"]["parts"]))
    for k in keys:
        a = before["every_chat"]["parts"].get(k, 0)
        b = after["every_chat"]["parts"].get(k, 0)
        L.append("  %-34s %12s %12s" % (k, vk.fmt(a), vk.fmt(b)))
    L.append("  %-34s %12s %12s" % ("Every chat, characters", vk.fmt(before["every_chat"]["chars"]),
                                    vk.fmt(after["every_chat"]["chars"])))
    L.append("  %-34s %12s %12s" % ("Every chat, rough tokens", vk.fmt(before["every_chat"]["tokens"]),
                                    vk.fmt(after["every_chat"]["tokens"])))
    rows = [("Memory index lines", lambda d: d["memory_index"]["lines"]),
            ("Memory index characters", lambda d: d["memory_index"]["chars"]),
            ("decisions/log.md characters", lambda d: (d.get("decisions") or {}).get("chars", 0)),
            ("tasks.md done items", lambda d: (d.get("tasks") or {}).get("done_items", 0)),
            ("inbox.md lines", lambda d: (d.get("inbox") or {}).get("lines", 0)),
            ("Secret files in the vault", lambda d: len(d["secrets"])),
            ("Big media files", lambda d: len(d["media"]["big"]))]
    for name, f in rows:
        L.append("  %-34s %12s %12s" % (name, vk.fmt(f(before)), vk.fmt(f(after))))
    return L


def main(argv=None):
    ap = argparse.ArgumentParser(description="Measure the vault (read only).")
    ap.add_argument("--vault", default=None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--save-before", action="store_true")
    ap.add_argument("--compare", action="store_true")
    ap.add_argument("--doctor", action="store_true")
    ap.add_argument("--no-briefing", action="store_true")
    ap.add_argument("--today", default=None)
    args = ap.parse_args(argv)
    root = vk.find_vault(args.vault)
    today = dt.datetime.strptime(args.today, "%Y-%m-%d").date() if args.today else None
    d = measure(root, briefing=not args.no_briefing, doctor=args.doctor, today=today)
    before_path = os.path.join(vk.temp_dir_for(root), "before.json") if (args.save_before or args.compare) else None
    if args.save_before:
        with open(before_path, "w", encoding="utf-8") as fh:
            json.dump(d, fh, ensure_ascii=False)
    if args.compare:
        before = vk.load_json(before_path, None)
        if not isinstance(before, dict):
            print("No saved numbers from before. Run with --save-before first.")
            return 1
        d["before"] = before
        vk.emit(args, d, compare(before, d) + [""] + report(d))
        return 0
    vk.emit(args, d, report(d))
    return 0


if __name__ == "__main__":
    sys.exit(main())
