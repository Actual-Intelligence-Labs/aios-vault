"""Bring Claude's memory index (memory/claude/MEMORY.md) back under its budget,
without changing a single word of any line that carries a rule or a default.

  python3 memory_index.py plan --vault .
      Read only. Sorts every index line into one of three kinds and prints the
      plan with a number on each line that would move:
        rule     under a rules heading ("Rules", "How to work with the owner")
        default  states a default, a never or an always, starts with a verb,
                 or has a word like only, first, ask, means (see vaultkit.py)
        pointer  a plain topic pointer: a title and a few trigger words
      Only pointer lines ever move, and only when the index is over its budget
      (75 lines or 10,000 characters). They move word for word into a hub note
      for their heading, and one new index line points at the hub. It moves
      the fewest headings that bring the index under the budget. A hub holds
      at most 20 lines (more make a second page). Lines with no topic heading
      above them never move.

  python3 memory_index.py apply --vault . --expect-sha <sha from the plan>
          [--skip 3,7] --apply --run-dir archives/optimize-YYYY-MM-DD-HHMM
      Moves the planned lines, except the numbers in --skip (the owner's
      "no"). Without --apply it only shows the result. It stops if
      MEMORY.md changed since the plan.

Checks before anything is written (and again after, from disk): the new index
plus the moved lines gives back the old index byte for byte; every rule and
default line is still in the index word for word; every moved line is in its
hub; every memory note that was reachable from the index within two links
still is.
"""

import sys
sys.dont_write_bytecode = True  # never leave a __pycache__ folder in the vault
import argparse
import datetime as dt
import json
import os
import re
from urllib.parse import unquote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vaultkit as vk  # noqa: E402

INDEX_REL = "memory/claude/MEMORY.md"
MEM_DIR = "memory/claude"
HUB_MARK = "<!-- hub note made by the optimize-vault skill -->"


def link_targets(text, base_dir):
    """Memory-folder-relative targets of every markdown link and wikilink in text."""
    out = []
    for m in vk.MD_LINK_RE.finditer(text):
        t = unquote(m.group(1)).split("#", 1)[0]
        if not t or "://" in t or t.startswith("mailto:"):
            continue
        out.append(os.path.normpath(os.path.join(base_dir, t)).replace(os.sep, "/"))
    for m in vk.WIKI_LINK_RE.finditer(text):
        t = m.group(1).strip()
        if not t:
            continue
        if not t.endswith(".md"):
            t += ".md"
        if t.startswith(MEM_DIR + "/"):
            out.append(t)
        elif "/" in t:
            out.append(os.path.normpath(t).replace(os.sep, "/"))
        else:
            out.append(os.path.normpath(os.path.join(base_dir, t)).replace(os.sep, "/"))
    return [vk.nfc(x) for x in out]


def memory_notes(root):
    d = os.path.join(root, MEM_DIR)
    out = []
    for dp, dns, fns in os.walk(d):
        dns[:] = [x for x in dns if not x.startswith(".")]
        for f in fns:
            if f.endswith(".md"):
                rel = vk.nfc(vk.rel_of(root, os.path.join(dp, f)))
                if rel != INDEX_REL:
                    out.append(rel)
    return sorted(out)


def reachable(root, index_text=None, extra_texts=None, depth=2):
    """Memory notes reachable from the index within `depth` links. extra_texts:
    rel -> text for files that do not exist on disk yet (planned hubs)."""
    extra = dict(extra_texts or {})
    if index_text is None:
        index_text = vk.read_text(os.path.join(root, INDEX_REL)) or ""
    on_disk = {}
    for rel in memory_notes(root):
        on_disk[rel] = None
    for rel in extra:
        on_disk[rel] = None
    seen = {}
    frontier = [(INDEX_REL, index_text)]
    for hop in range(1, depth + 1):
        nxt = []
        for rel, text in frontier:
            base = os.path.dirname(rel)
            for t in link_targets(text, base):
                if t in on_disk and t not in seen:
                    seen[t] = hop
                    body = extra.get(t)
                    if body is None:
                        body = vk.read_text(os.path.join(root, t)) or ""
                    nxt.append((t, body))
        frontier = nxt
    return seen


def parse_index(text):
    lines = vk.split_keep(text)
    mask = vk.masked(lines)
    heading = ""
    rows = []
    for i, l in enumerate(lines):
        if mask[i]:
            continue
        h = vk.heading_of(l)
        if h:
            heading = h[1] if h[0] >= 2 else ""
            continue
        if not vk.INDEX_LINE_RE.match(vk.bare(l)):
            continue
        s = vk.bare(l)
        if vk.RULE_HEADING.search(heading):
            kind = "rule"
        elif vk.is_rule_like(s):
            kind = "default"
        else:
            kind = "pointer"
        targets = link_targets(s, MEM_DIR)
        if any("hub" in os.path.basename(t).lower() for t in targets):
            kind = "hub"
        rows.append({"i": i, "line": l, "heading": heading, "kind": kind})
    return lines, rows


def title_of(line):
    m = re.match(r"^\s*[-*+]\s+\[([^\]]*)\]", line)
    if m:
        return m.group(1).strip()
    m = re.match(r"^\s*[-*+]\s+\[\[([^\]|]+)", line)
    return os.path.basename(m.group(1)).strip() if m else vk.bare(line).strip()[:40]


def hub_line(heading, hub_file, titles, eol):
    words = []
    total = 0
    more = False
    for t in titles:
        t = t.lower()
        if total + len(t) > 220:
            more = True
            break
        words.append(t)
        total += len(t) + 2
    trig = ", ".join(words) + (", and more" if more else "")
    return "- [%s hub](%s): %s%s" % (heading, hub_file, trig, eol)


def hub_header(heading, eol):
    t = ("# %s hub\n\nRelated: [[MEMORY]]\n\n%s\n\nLines moved here from the memory index by the optimize-vault skill, "
         "word for word. Each line only says where to find one memory note. A new line of that plain kind may go here. "
         "A new memory that states a rule, a default, an always or a never always gets its own line in MEMORY.md, "
         "never here.\n"
         % (heading, HUB_MARK))
    return t.replace("\n", eol)


def index_text(b):
    """The index as text, without a byte-order mark (build() reads it the same way).
    The mark goes back on when the file is written, if it had one."""
    if vk.has_bom(b):
        b = b[3:]
    return b.decode("utf-8")


def make_plan(root, today):
    path = os.path.join(root, INDEX_REL)
    b = vk.read_bytes(path)
    if b is None:
        if os.path.lexists(path):
            return {"error": "memory/claude/MEMORY.md could not be read (no permission?), so it was left as is."}
        return {"error": "memory/claude/MEMORY.md is missing"}
    why = vk.write_problem(root, INDEX_REL)
    if why:
        return {"error": why}
    text = index_text(b)
    lines, rows = parse_index(text)
    eol = vk.eol_of(lines)
    n_lines = vk.count_lines(text)
    n_chars = len(text)
    over = n_lines > vk.MEMORY_LINES or n_chars > vk.MEMORY_CHARS
    plan = {"file": INDEX_REL, "sha256": vk.sha_bytes(b), "lines": n_lines, "chars": n_chars, "over": over,
            "bom": vk.has_bom(b),
            "counts": {k: sum(1 for r in rows if r["kind"] == k) for k in ("rule", "default", "pointer", "hub")},
            "groups": [], "eol": eol}
    if not over:
        plan["why"] = "under budget (%d lines, %s characters; budget %d and %s)" % (
            n_lines, vk.fmt(n_chars), vk.MEMORY_LINES, vk.fmt(vk.MEMORY_CHARS))
        return plan
    by_head = {}
    order = []
    for r in rows:
        if r["kind"] != "pointer":
            continue
        if r["heading"] not in by_head:
            by_head[r["heading"]] = []
            order.append(r["heading"])
        by_head[r["heading"]].append(r)
    existing = set(os.listdir(os.path.join(root, MEM_DIR))) if os.path.isdir(os.path.join(root, MEM_DIR)) else set()
    index_links = set(link_targets(text, MEM_DIR))
    cands = []
    for h in order:
        if not h:
            # Lines with no topic heading above them share no topic, so a hub for them would be a
            # grab bag whose index line names only a few of them. They stay.
            continue
        rs = by_head[h]
        if len(rs) < vk.HUB_MIN_LINES:
            continue
        # At most HUB_MAX_LINES lines per hub page, so its one index line can still name what is in it.
        chunks = [rs[k:k + vk.HUB_MAX_LINES] for k in range(0, len(rs), vk.HUB_MAX_LINES)]
        if len(chunks) > 1 and len(chunks[-1]) < vk.HUB_MIN_LINES:
            chunks[-2] = chunks[-2] + chunks[-1]
            chunks.pop()
        for part, crs in enumerate(chunks, 1):
            label = h if part == 1 else "%s, part %d" % (h, part)
            stem = vk.slug(h) + ("" if part == 1 else "-part-%d" % part)
            name = stem + "-hub.md"
            n = 2
            while name in existing and (MEM_DIR + "/" + name) not in index_links:
                name = stem + "-hub-%d.md" % n
                n += 1
            hl = hub_line(label, name, [title_of(r["line"]) for r in crs], eol)
            already = (MEM_DIR + "/" + name) in index_links
            saved_chars = sum(len(r["line"]) for r in crs) - (0 if already else len(hl))
            saved_lines = len(crs) - (0 if already else 1)
            cands.append({"heading": h, "label": label, "hub": name, "hub_line": hl, "hub_exists": name in existing,
                          "hub_in_index": already, "rows": crs, "saved_chars": saved_chars,
                          "saved_lines": saved_lines})
    cands.sort(key=lambda c: (-c["saved_chars"], c["heading"]))
    chosen = []
    lines_now, chars_now = n_lines, n_chars
    for c in cands:
        if lines_now <= vk.INDEX_TARGET_LINES and chars_now <= vk.INDEX_TARGET_CHARS:
            break
        chosen.append(c)
        lines_now -= c["saved_lines"]
        chars_now -= c["saved_chars"]
    chosen.sort(key=lambda c: c["rows"][0]["i"])
    num = 0
    for c in chosen:
        items = []
        for r in c["rows"]:
            num += 1
            items.append({"id": num, "line": vk.bare(r["line"]), "i": r["i"]})
        plan["groups"].append({"heading": c["heading"], "label": c["label"], "hub": MEM_DIR + "/" + c["hub"],
                               "hub_line": vk.bare(c["hub_line"]),
                               "hub_exists": c["hub_exists"], "hub_in_index": c["hub_in_index"], "items": items})
    plan["projected_lines"] = lines_now
    plan["projected_chars"] = chars_now
    plan["fits"] = lines_now <= vk.MEMORY_LINES and chars_now <= vk.MEMORY_CHARS
    plan["stays"] = [vk.bare(r["line"]) for r in rows if r["kind"] in ("rule", "default")]
    return plan


def build(root, plan, skip, today):
    """New index text, hub texts and the checks. skip: ids the owner said no to."""
    path = os.path.join(root, INDEX_REL)
    text = vk.read_text(path)
    lines = vk.split_keep(text)
    eol = plan["eol"]
    remove = {}
    inserts = {}
    hubs = {}
    moved = []
    dropped = []
    for g in plan["groups"]:
        items = [it for it in g["items"] if it["id"] not in skip]
        if len(items) < vk.HUB_MIN_LINES and not g["hub_exists"]:
            if items:
                dropped.append(g["heading"])
            continue
        if not items:
            continue
        for it in items:
            remove[it["i"]] = it
            moved.append((g["hub"], lines[it["i"]]))
        label = g.get("label") or g["heading"] or "More"
        if not g["hub_in_index"]:
            titles = [title_of(it["line"]) for it in items]
            inserts[items[0]["i"]] = hub_line(label, os.path.basename(g["hub"]), titles, eol)
        hp = os.path.join(root, g["hub"])
        before = vk.read_text(hp)
        body = before if before is not None else hub_header(label, eol)
        if not body.endswith("\n"):
            body += eol
        body += eol + "<!-- moved here on %s -->" % today.isoformat() + eol + eol
        for it in items:
            ln = lines[it["i"]]
            body += ln if ln.endswith("\n") else ln + eol
        hubs[g["hub"]] = (before, body)
    out = []
    for i, l in enumerate(lines):
        if i in inserts:
            out.append(inserts[i])
        if i in remove:
            continue
        out.append(l)
    new_text = "".join(out)
    if hubs:
        add_deep_links(root, text, new_text, hubs, moved, eol)
    return new_text, hubs, moved, dropped, list(inserts.values())


def add_deep_links(root, old_text, new_text, hubs, moved, eol):
    """A note that was two links away through a moved line would now be three
    away. List each one in the hub too, so every note stays within two links."""
    after_texts = dict((h, v[1]) for h, v in hubs.items())
    before = reachable(root, old_text)
    after = reachable(root, new_text, extra_texts=after_texts)
    lost = set(n for n in before if n not in after)
    if not lost:
        return
    add = {}
    placed = set()
    for hub_rel, line in moved:
        for t in link_targets(vk.bare(line), MEM_DIR):
            body = vk.read_text(os.path.join(root, t)) or ""
            for t2 in link_targets(body, os.path.dirname(t)):
                if t2 in lost and t2 not in placed:
                    placed.add(t2)
                    add.setdefault(hub_rel, []).append(t2)
    for hub_rel in sorted(add):
        before_text, body = hubs[hub_rel]
        if not body.endswith("\n"):
            body += eol
        body += eol + "Linked from the notes above (listed here too, so Claude can still reach them):" + eol
        for t2 in add[hub_rel]:
            body += "- [[%s]]%s" % (t2[:-3], eol)
        hubs[hub_rel] = (before_text, body)


def checks(root, old_text, new_text, hubs_after, hubs_before, moved, inserted, stays):
    problems = []
    # 1. Put the moved lines back and drop the new hub lines: the old index, byte for byte.
    new_lines = vk.split_keep(new_text)
    for h in inserted:
        if h in new_lines:
            new_lines.remove(h)
        else:
            problems.append("a new hub line is missing")
    old_lines = vk.split_keep(old_text)
    moved_set = {}
    for hub, line in moved:
        moved_set[line] = moved_set.get(line, 0) + 1
    rebuilt_minus = [l for l in old_lines]
    for line, n in moved_set.items():
        for _ in range(n):
            rebuilt_minus.remove(line)
    if rebuilt_minus != new_lines:
        problems.append("the new index is not the old index minus the moved lines")
    # 2. Every rule and default line is still there, word for word.
    have = set(vk.bare(l) for l in vk.split_keep(new_text))
    lost_rules = [s for s in stays if s not in have]
    if lost_rules:
        problems.append("%d rule or default lines are not in the new index word for word" % len(lost_rules))
    # 3. Every moved line is in its hub, once more than before.
    for hub, line in moved:
        a = (hubs_after.get(hub) or "").count(line if line.endswith("\n") else line)
        b = (hubs_before.get(hub) or "").count(line if line.endswith("\n") else line)
        if a <= b:
            problems.append("a moved line is missing from " + hub)
    # 4. Reachability within two links: nothing that was reachable is lost.
    before = reachable(root, old_text)
    after = reachable(root, new_text, extra_texts=hubs_after)
    lost = sorted(set(before) - set(after))
    if lost:
        problems.append("%d memory notes would no longer be reachable within two links: %s"
                        % (len(lost), ", ".join(lost[:5])))
    return problems, before, after


def cmd_plan(args, root, today):
    plan = make_plan(root, today)
    lines = []
    if plan.get("error"):
        lines.append(plan["error"])
        vk.emit(args, plan, lines)
        return 1
    c = plan["counts"]
    lines.append("Memory index: %d lines, %s characters (budget %d lines, %s characters)."
                 % (plan["lines"], vk.fmt(plan["chars"]), vk.MEMORY_LINES, vk.fmt(vk.MEMORY_CHARS)))
    lines.append("  %d rule lines and %d default lines stay word for word. %d plain pointer lines. %d hub lines."
                 % (c["rule"], c["default"], c["pointer"], c["hub"]))
    if not plan["over"]:
        lines.append("Nothing to do: " + plan["why"] + ".")
        vk.emit(args, plan, lines)
        return 0
    if not plan["groups"]:
        lines.append("Over budget, but no topic heading has %d or more plain pointer lines to group. Lines with no "
                     "heading above them stay, and so does every line that carries a rule or a default. Ask the owner "
                     "what to do (see the skill)." % vk.HUB_MIN_LINES)
        vk.emit(args, plan, lines)
        return 0
    lines.append("Plan: move these plain pointer lines, word for word, into hub notes. Each hub gets one index line.")
    for g in plan["groups"]:
        lines.append("")
        lines.append("Under \"%s\" -> %s%s" % (g["heading"] or "(no heading)", g["hub"],
                                               " (exists, lines are added)" if g["hub_exists"] else " (new)"))
        if not g["hub_in_index"]:
            lines.append("  new index line: " + g["hub_line"])
        for it in g["items"]:
            lines.append("  [%d] %s" % (it["id"], it["line"]))
    lines.append("")
    lines.append("After: about %d lines and %s characters%s." % (
        plan["projected_lines"], vk.fmt(plan["projected_chars"]),
        "" if plan["fits"] else " (still over budget: the rest are rules and defaults, which never move)"))
    lines.append("To apply: memory_index.py apply --vault . --expect-sha %s --apply --run-dir <run folder> "
                 "[--skip 3,7 for any line the owner wants to keep in the index]" % plan["sha256"])
    vk.emit(args, plan, lines)
    return 0


def cmd_apply(args, root, today, now):
    plan = make_plan(root, today)
    if plan.get("error"):
        print(plan["error"])
        return 1
    if args.expect_sha and plan["sha256"] != args.expect_sha:
        print("memory/claude/MEMORY.md changed since the plan was made. Make the plan again and show it to the owner.")
        return 1
    if not plan["over"] or not plan["groups"]:
        vk.emit(args, {"applied": False, "why": plan.get("why", "nothing to move")},
                ["Memory index: nothing to move (" + plan.get("why", "no plain pointer lines to group") + ")."])
        return 0
    skip = set()
    for part in (args.skip or "").split(","):
        part = part.strip()
        if part.isdigit():
            skip.add(int(part))
    old_b = vk.read_bytes(os.path.join(root, INDEX_REL))
    if old_b is None or vk.sha_bytes(old_b) != plan["sha256"]:
        print("memory/claude/MEMORY.md changed while this ran. Nothing in it was changed. Make the plan again.")
        return 1
    old_text = index_text(old_b)
    new_text, hubs, moved, dropped, inserted = build(root, plan, skip, today)
    hubs_before = dict((k, v[0]) for k, v in hubs.items())
    hubs_after = dict((k, v[1]) for k, v in hubs.items())
    problems, before, after = checks(root, old_text, new_text, hubs_after, hubs_before, moved, inserted, plan["stays"])
    res = {"applied": False, "moved": len(moved), "hubs": sorted(hubs), "skipped": sorted(skip), "dropped": dropped,
           "lines_before": plan["lines"], "lines_after": vk.count_lines(new_text),
           "chars_before": plan["chars"], "chars_after": len(new_text), "problems": problems,
           "reachable_before": len(before), "reachable_after": len(after)}
    if problems:
        vk.emit(args, res, ["Memory index: check FAILED, nothing written: " + "; ".join(problems)])
        return 1
    if args.apply and moved:
        run = vk.Run(root, args.run_dir, now)
        written = []
        current = INDEX_REL
        try:
            for hub in sorted(hubs):
                why = vk.write_problem(root, hub)
                if why:
                    raise vk.Refused(why)
            for hub in sorted(hubs):
                current = hub
                run.write(hub, hubs_after[hub])
                written.append(hub)
            current = INDEX_REL
            run.write(INDEX_REL, ("\ufeff" if plan.get("bom") else "") + new_text, expect=old_b)
        except (vk.ChangedUnderUs, vk.Refused, OSError) as e:
            stuck = run.undo(written)
            msg = vk.failure_line(e, current)
            if stuck:
                print(msg + " These files could not be put back, so their copies are in %s/backup: %s"
                      % (run.rel, ", ".join(stuck)))
            else:
                print(msg + " Nothing was moved, and every file is as it was. Make the plan again once that is fixed.")
            return 1
        disk_hubs = dict((h, vk.read_text(os.path.join(root, h))) for h in hubs)
        disk_index = vk.read_text(os.path.join(root, INDEX_REL))
        problems2, before2, after2 = checks(root, old_text, disk_index, disk_hubs, hubs_before, moved, inserted,
                                            plan["stays"])
        res["problems"] = problems2
        res["applied"] = not problems2
        res["run_dir"] = run.rel
        run.note("memory-index", {"moved_lines": [l.rstrip("\r\n") for _, l in moved], "hubs": sorted(hubs),
                                  "skipped": sorted(skip), "kept_verbatim": len(plan["stays"])})
    lines = []
    lines.append("Memory index: %s %d lines into %d hub note%s%s." % (
        "moved" if res["applied"] else "would move", len(moved), len(hubs), "" if len(hubs) == 1 else "s",
        (" (skipped: " + ", ".join(str(x) for x in sorted(skip)) + ")") if skip else ""))
    lines.append("  %d lines, %s characters before. %d lines, %s characters after." % (
        res["lines_before"], vk.fmt(res["chars_before"]), res["lines_after"], vk.fmt(res["chars_after"])))
    lines.append("  Rule and default lines kept word for word: %d of %d." % (len(plan["stays"]), len(plan["stays"])))
    lines.append("  Memory notes reachable within two links: %d before, %d after." % (
        res["reachable_before"], res["reachable_after"]))
    for d in dropped:
        lines.append("  Not moved (too few lines left after the owner's no): " + (d or "(no heading)"))
    if res.get("problems"):
        lines.append("  PROBLEM after writing: " + "; ".join(res["problems"]))
    vk.emit(args, res, lines)
    return 0 if not res.get("problems") else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="Plan or apply a memory index shrink (rule lines never move).")
    ap.add_argument("cmd", choices=["plan", "apply"])
    ap.add_argument("--vault", default=None)
    ap.add_argument("--expect-sha", default=None)
    ap.add_argument("--skip", default=None)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--run-dir", default=None)
    ap.add_argument("--now", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    root = vk.find_vault(args.vault)
    now = vk.parse_now(args.now)
    today = (now or dt.datetime.now()).date()
    if args.cmd == "plan":
        return cmd_plan(args, root, today)
    return cmd_apply(args, root, today, now)


if __name__ == "__main__":
    sys.exit(main())
