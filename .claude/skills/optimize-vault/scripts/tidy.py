"""Tidy the three files that only grow: decisions/log.md, tasks.md and inbox.md.

Dry run by default: it prints what would move and changes nothing.
Add --apply to make the moves.

WHAT MOVES (each into a dated file in history/, a folder Obsidian shows)
  decisions/log.md  when it is over 40,000 characters or has entries older
                    than 90 days: every entry older than 90 days, then, if the
                    log is still too big, the oldest entries until it fits
                    (the newest 10 always stay).
                    -> history/decisions/decisions-YYYY-MM.md (month of the entry)
  tasks.md          when it has over 20 done items: every done item ("- [x]")
                    with no open sub-item.
                    -> history/tasks/tasks-done-YYYY.md
  inbox.md          when it is over 100 lines: every entry that says where it
                    went ("->"), except the newest 40.
                    -> history/inbox/inbox-YYYY-MM.md

WHAT NEVER MOVES
  The top of each file, undated sections, anything in a code block or an HTML
  comment, a done item with an open sub-item, an inbox entry that does not say
  where it went (unless --include-unrouted), and every entry listed in
  .claude/optimize-keep.json (the owner's "keep this one" answers).

POINTERS
  The live file gets one line per history file it sent entries to, such as
  "Older entries moved to [[history/inbox/inbox-2026-03]]", so every moved
  line is one click away. A decision that another note links to by its heading
  keeps its heading in the log, with a link under it to where it went.

PROOF
  Before anything is written, the script puts the moved lines back into the
  new file and checks the result equals the original byte for byte. After
  writing, it reads every file back and checks again. If a check fails, or a
  file cannot be written (read-only, a full disk), nothing is written, or the
  files already written are put back.

FILES LEFT AS IS
  A file that is not saved as UTF-8 text, is a link to somewhere else, or is
  set to read-only is never rewritten. The plan says so in one line.

THE OWNER'S YES
  The dry run prints a fingerprint of the plan. --apply --expect-sha <it>
  stops, changing nothing, when the plan made at apply time is not the one
  the owner saw (an entry was added or changed in between).

RULES IN OLD DECISIONS
  An old decision with a rule word in it (never, always, must, do not,
  exception, from now on...) is listed. --apply stops while any are listed,
  until --rules-checked is given: check first that each rule also lives in
  CLAUDE.md or a memory note, or keep that entry with --keep "<title start>"
  (saved in .claude/optimize-keep.json so the next run keeps it too).

Usage, from the vault folder:
  python3 tidy.py --vault .                      (dry run)
  python3 tidy.py --vault . --apply --expect-sha <from the dry run> --run-dir archives/optimize-YYYY-MM-DD-HHMM
Options: --only decisions,tasks,inbox  --keep "TITLE"  --rules-checked
         --include-unrouted  --today YYYY-MM-DD  --json
"""

import sys
sys.dont_write_bytecode = True  # never leave a __pycache__ folder in the vault
import argparse
import hashlib
import datetime as dt
import json
import os
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vaultkit as vk  # noqa: E402

KINDS = ("decisions", "tasks", "inbox")
LIVE = {"decisions": "decisions/log.md", "tasks": "tasks.md", "inbox": "inbox.md"}

PTR = {
    "decisions": "Older decisions moved to ",
    "tasks": "Done items moved to ",
    "inbox": "Older entries moved to ",
}
HEAD_PTR = "Moved on %s to "
POINTER_RE = re.compile(
    r"^(?:Older decisions moved to |Done items moved to |Older entries moved to |Moved on \d{4}-\d{2}-\d{2} to )"
    r"\[\[[^\]]+\]\][ \t]*\r?\n?$")
LOG_HEADING_RE = re.compile(r"^##[ \t]+Log[ \t]*$", re.I)
DONE_HEADING_RE = re.compile(r"^##[ \t]+Done[ \t]*$", re.I)
INBOX_ENTRY_RE = re.compile(r"^[ \t]{0,3}(?:[-*+][ \t]+)?(?:\*\*)?(20\d\d-\d\d-\d\d)")
LIST_ITEM_RE = re.compile(r"^(?:[-*+]|\d+[.)])[ \t]")
DONE_RE = re.compile(r"^[-*+] \[[xX]\]")
OPEN_BOX_RE = re.compile(r"^[ \t]*(?:[-*+]|\d+[.)]) \[ \]")
ROUTED_RE = re.compile(r"(->|=>|→)")


def is_pointer(line):
    return bool(POINTER_RE.match(line))


def wikilink(rel_md, heading=None):
    target = rel_md[:-3] if rel_md.endswith(".md") else rel_md
    if heading:
        sub = re.sub(r"[#|^:%\[\]$\\]", " ", heading)
        sub = re.sub(r"\s+", " ", sub).strip()
        if sub:
            return "[[%s#%s|%s]]" % (target, sub, os.path.basename(target))
    return "[[%s]]" % target


class Move(object):
    def __init__(self, start, lines, archive, title, kind):
        self.start = start
        self.lines = list(lines)
        self.archive = archive
        self.title = title
        self.kind = kind
        self.heading = None          # set when the heading line stays live (a linked decision)
        self.rule_lines = []

    @property
    def text(self):
        return "".join(self.lines)

    def piece(self, eol):
        body = self.text
        if body and not body.endswith("\n"):
            body += eol
        if self.heading is not None:
            head = self.heading if self.heading.endswith("\n") else self.heading + eol
            return eol + head + eol + body
        if self.kind == "decisions":
            return eol + body
        return body


class Plan(object):
    def __init__(self, kind, text):
        self.kind = kind
        self.rel = LIVE[kind]
        self.orig_text = text
        self.orig = vk.split_keep(text)
        self.eol = vk.eol_of(self.orig)
        self.moves = []
        self.insert_after = {}       # line index -> pointer lines added after it (-1 = top of file)
        self.insert_before = {}
        self.notes = []              # things kept, with why
        self.questions = []          # things only the owner can answer
        self.triggered = False
        self.why = ""
        self.new = list(self.orig)
        self.error = None
        self.refused = None          # a plain sentence when the file (or its history file) is left as is

    def build(self):
        gone = set()
        for m in self.moves:
            gone.update(range(m.start, m.start + len(m.lines)))
        out = []
        for i, line in enumerate(self.orig):
            for p in self.insert_before.get(i, []):
                out.append(p)
            if i not in gone:
                if i == len(self.orig) - 1 and not line.endswith("\n") and self.insert_after.get(i):
                    line = line + self.eol
                out.append(line)
            for p in self.insert_after.get(i, []):
                if out and not out[-1].endswith("\n"):
                    out[-1] = out[-1] + self.eol
                out.append(p)
        self.new = out

    @property
    def new_text(self):
        return "".join(self.new)

    def changed(self):
        return self.new_text != self.orig_text

    def added_pointers(self):
        out = []
        for d in (self.insert_after, self.insert_before):
            for v in d.values():
                out.extend(v)
        return out


# ---------------------------------------------------------------- decisions

def heading_links(root):
    """Normalized heading names that some note links to inside decisions/log."""
    found = set()
    for rel in vk.notes(root):
        if rel == LIVE["decisions"]:
            continue
        t = vk.read_text(os.path.join(root, rel)) or ""
        if "#" not in t:
            continue
        for m in vk.WIKI_LINK_RE.finditer(t):
            target, sub = m.group(1).strip(), m.group(2)
            if sub and target.lower().rstrip("/") in ("decisions/log", "log", "decisions/log.md"):
                found.add(vk.obsidian_norm(sub))
    return found


def decision_sections(lines, mask):
    """(start, end, heading text, heading date) for each dated '## ' entry."""
    heads = []
    for i, l in enumerate(lines):
        if mask[i]:
            continue
        h = vk.heading_of(l)
        if h and h[0] <= 2:
            heads.append((i, h[0], h[1]))
    out = []
    for n, (i, level, text) in enumerate(heads):
        if level != 2:
            continue
        end = heads[n + 1][0] if n + 1 < len(heads) else len(lines)
        d = vk.dates_in(text)
        if not d:
            continue
        out.append((i, end, text, d[0]))
    return out


def section_is_pointer_only(lines, s, e):
    body = [l for l in lines[s + 1:e] if vk.bare(l).strip()]
    return bool(body) and all(is_pointer(l) for l in body)


def newest_past(text, today):
    ds = [d for d in vk.dates_in(text) if d <= today]
    return max(ds) if ds else None


def decisions_state(text, today, keeps):
    """Counts the session briefing and this skill agree on."""
    lines = vk.split_keep(text)
    mask = vk.masked(lines)
    secs = decision_sections(lines, mask)
    cutoff = today - dt.timedelta(days=vk.DECISIONS_DAYS)
    old = 0
    live = 0
    for s, e, title, hd in secs:
        if section_is_pointer_only(lines, s, e):
            continue
        live += 1
        newest = newest_past("".join(lines[s:e]), today) or hd
        if newest < cutoff and not vk.is_kept(title, keeps):
            old += 1
    return {"chars": len(text), "entries": live, "older_than_90_days": old,
            "over": len(text) > vk.DECISIONS_CHARS or old > 0}


def plan_decisions(root, text, today, run_date, keeps, extra_keeps=()):
    plan = Plan("decisions", text)
    lines = plan.orig
    mask = vk.masked(lines)
    state = decisions_state(text, today, keeps + list(extra_keeps))
    if not state["over"]:
        plan.why = "under budget (%s characters, no entry older than %d days)" % (vk.fmt(len(text)), vk.DECISIONS_DAYS)
        return plan
    plan.triggered = True
    plan.why = ("%s characters (budget %s), %d entries older than %d days"
                % (vk.fmt(len(text)), vk.fmt(vk.DECISIONS_CHARS), state["older_than_90_days"], vk.DECISIONS_DAYS))
    cutoff = today - dt.timedelta(days=vk.DECISIONS_DAYS)
    linked = heading_links(root)
    secs = [x for x in decision_sections(lines, mask) if not section_is_pointer_only(lines, x[0], x[1])]
    all_keeps = list(keeps) + list(extra_keeps)
    chosen = []
    for s, e, title, hd in secs:
        newest = newest_past("".join(lines[s:e]), today) or hd
        if newest >= cutoff:
            continue
        if vk.is_kept(title, all_keeps):
            plan.notes.append("kept (you asked to keep it): " + title)
            continue
        if any(is_pointer(l) for l in lines[s + 1:e]):
            plan.notes.append("kept (it already holds a pointer line): " + title)
            continue
        chosen.append((s, e, title, hd))
    # Still too big: the oldest entries next, never the newest few.
    size = len(text) - sum(len("".join(lines[s:e])) for s, e, _, _ in chosen)
    if size > vk.DECISIONS_CHARS:
        rest = [x for x in secs if x not in chosen and not vk.is_kept(x[2], all_keeps)
                and not any(is_pointer(l) for l in lines[x[0] + 1:x[1]])]
        rest.sort(key=lambda x: (x[3], x[0]))
        protected = set(x[0] for x in sorted(secs, key=lambda x: (x[3], x[0]))[-vk.DECISIONS_KEEP_NEWEST:])
        for x in rest:
            if size <= vk.DECISIONS_CHARS:
                break
            if x[0] in protected:
                continue
            chosen.append(x)
            size -= len("".join(lines[x[0]:x[1]]))
    chosen.sort()
    first_moved = None
    for s, e, title, hd in chosen:
        archive = "%s/decisions/decisions-%s.md" % (vk.HISTORY, hd.strftime("%Y-%m"))
        if vk.obsidian_norm(title) in linked:
            # The heading and the blank lines around the body stay, so the log still reads cleanly.
            a, b = s + 1, e
            while a < b and not vk.bare(lines[a]).strip():
                a += 1
            while b > a and not vk.bare(lines[b - 1]).strip():
                b -= 1
            m = Move(a, lines[a:b], archive, title, "decisions")
            m.heading = lines[s]
            plan.insert_after.setdefault(a - 1, []).append(
                HEAD_PTR % run_date.isoformat() + wikilink(archive, title) + plan.eol)
            plan.notes.append("heading stays in the log (a note links to it): " + title)
        else:
            m = Move(s, lines[s:e], archive, title, "decisions")
            if first_moved is None:
                first_moved = s
        m.rule_lines = [vk.bare(l).strip() for l in m.lines if vk.DECISION_RULE_WORDS.search(l)]
        plan.moves.append(m)
    # One pointer line per history file, under "## Log" (or where the first moved entry was).
    want = []
    existing = set(vk.bare(l) for l in lines if is_pointer(l))
    for arch in sorted(set(m.archive for m in plan.moves)):
        p = PTR["decisions"] + wikilink(arch)
        if p not in existing:
            want.append(p + plan.eol)
    if want:
        anchor = None
        for i, l in enumerate(lines):
            if not mask[i] and LOG_HEADING_RE.match(vk.bare(l)):
                anchor = i
                break
        if anchor is not None:
            j = anchor
            while j + 1 < len(lines) and is_pointer(lines[j + 1]):
                j += 1
            plan.insert_after.setdefault(j, []).extend(want)
        elif first_moved is not None:
            plan.insert_before.setdefault(first_moved, []).extend(want)
        else:
            s0 = plan.moves[0].start - 1
            plan.insert_after.setdefault(s0, []).extend(want)
    for m in plan.moves:
        if m.rule_lines:
            plan.questions.append({"title": m.title, "lines": m.rule_lines})
    plan.build()
    return plan


# ---------------------------------------------------------------- units (tasks and inbox)

def units(lines, start, stop, mask, is_start):
    """Group lines[start:stop] into (kind, first, end): 'unit' (an item and its indented lines),
    'blank' or 'other'."""
    out = []
    i = start
    cur = None
    while i < stop:
        line = lines[i]
        s = vk.bare(line)
        if not mask[i] and not s.strip():
            j = i
            while j < stop and not vk.bare(lines[j]).strip():
                j += 1
            if cur is not None and j < stop and lines[j][:1] in (" ", "\t") and not mask[j]:
                cur[2] = j
                i = j
                continue
            if cur is not None:
                out.append(tuple(cur))
                cur = None
            for k in range(i, j):
                out.append(("blank", k, k + 1))
            i = j
            continue
        if not mask[i] and (is_start(s) or vk.heading_of(s)):
            if cur is not None:
                out.append(tuple(cur))
            cur = ["unit" if is_start(s) else "other", i, i + 1]
            if cur[0] == "other":
                out.append(tuple(cur))
                cur = None
        elif cur is not None and not mask[i] and line[:1] in (" ", "\t"):
            cur[2] = i + 1
        else:
            if cur is not None:
                out.append(tuple(cur))
                cur = None
            out.append(("other", i, i + 1))
        i += 1
    if cur is not None:
        out.append(tuple(cur))
    return out


def absorb_blanks(plan, us, moving):
    """A moved item takes the blank line after it when the line kept before it is
    blank too, so no run of empty lines is left behind."""
    lines = plan.orig
    if not us:
        return
    first = us[0][1]
    last_blank = first == 0 or not vk.bare(lines[first - 1]).strip()
    absorbed = set()
    for n, (kind, a, b) in enumerate(us):
        if n in absorbed:
            continue
        m = moving.get(n)
        if m is None:
            last_blank = kind == "blank" or not vk.bare(lines[b - 1]).strip()
            continue
        if (last_blank and n + 1 < len(us) and us[n + 1][0] == "blank" and (n + 1) not in moving
                and us[n + 1][1] == m.start + len(m.lines)):
            m.lines.append(lines[us[n + 1][1]])
            absorbed.add(n + 1)


def tasks_state(text):
    lines = vk.split_keep(text)
    mask = vk.masked(lines)
    done = sum(1 for i, l in enumerate(lines) if not mask[i] and DONE_RE.match(l))
    return {"done_items": done, "over": done > vk.TASKS_DONE}


def plan_tasks(root, text, today, run_date, keeps):
    plan = Plan("tasks", text)
    lines = plan.orig
    mask = vk.masked(lines)
    st = tasks_state(text)
    if not st["over"]:
        plan.why = "under budget (%d done items, budget %d)" % (st["done_items"], vk.TASKS_DONE)
        return plan
    plan.triggered = True
    plan.why = "%d done items (budget %d)" % (st["done_items"], vk.TASKS_DONE)
    first_item = None
    for i, l in enumerate(lines):
        if not mask[i] and LIST_ITEM_RE.match(l):
            first_item = i
            break
    if first_item is None:
        return plan
    us = units(lines, first_item, len(lines), mask, lambda s: bool(LIST_ITEM_RE.match(s)))
    moving = {}
    for n, (kind, a, b) in enumerate(us):
        if kind != "unit" or not DONE_RE.match(lines[a]):
            continue
        block = lines[a:b]
        title = vk.bare(lines[a]).strip()
        if any(OPEN_BOX_RE.match(l) for l in block[1:]):
            plan.notes.append("kept (done, but a sub-item is still open): " + title[:80])
            continue
        if any(is_pointer(l) for l in block):
            continue
        if vk.is_kept(re.sub(r"^[-*+] \[[xX]\]\s*", "", title), keeps):
            plan.notes.append("kept (you asked to keep it): " + title[:80])
            continue
        when = newest_past("".join(block), today) or run_date
        archive = "%s/tasks/tasks-done-%d.md" % (vk.HISTORY, when.year)
        moving[n] = Move(a, block, archive, title, "tasks")
    absorb_blanks(plan, us, moving)
    plan.moves = [moving[n] for n in sorted(moving)]
    want = []
    existing = set(vk.bare(l) for l in lines if is_pointer(l))
    for arch in sorted(set(m.archive for m in plan.moves)):
        p = PTR["tasks"] + wikilink(arch)
        if p not in existing:
            want.append(p + plan.eol)
    if want:
        anchor = None
        for i, l in enumerate(lines):
            if not mask[i] and DONE_HEADING_RE.match(vk.bare(l)):
                anchor = i
                break
        if anchor is not None:
            j = anchor
            while j + 1 < len(lines) and is_pointer(lines[j + 1]):
                j += 1
            plan.insert_after.setdefault(j, []).extend(want)
        else:
            plan.insert_before.setdefault(first_item, []).extend(want)
    plan.build()
    return plan


def inbox_state(text):
    n = vk.count_lines(text)
    return {"lines": n, "over": n > vk.INBOX_LINES}


def plan_inbox(root, text, today, run_date, keeps, include_unrouted=False):
    plan = Plan("inbox", text)
    lines = plan.orig
    mask = vk.masked(lines)
    st = inbox_state(text)
    if not st["over"]:
        plan.why = "under budget (%d lines, budget %d)" % (st["lines"], vk.INBOX_LINES)
        return plan
    plan.triggered = True
    plan.why = "%d lines (budget %d)" % (st["lines"], vk.INBOX_LINES)
    log_i = None
    for i, l in enumerate(lines):
        if not mask[i] and LOG_HEADING_RE.match(vk.bare(l)):
            log_i = i
            break
    start = log_i + 1 if log_i is not None else None
    if start is None:
        for i, l in enumerate(lines):
            if not mask[i] and INBOX_ENTRY_RE.match(vk.bare(l)):
                start = i
                break
    if start is None:
        plan.notes.append("no dated entries found")
        return plan
    stop = len(lines)
    for i in range(start, len(lines)):
        h = vk.heading_of(lines[i])
        if not mask[i] and h and h[0] <= 2 and not vk.dates_in(h[1]):
            stop = i
            break
    us = units(lines, start, stop, mask, lambda s: bool(INBOX_ENTRY_RE.match(s)))
    entries = []
    for n, (kind, a, b) in enumerate(us):
        if kind != "unit":
            continue
        d = vk.dates_in(vk.bare(lines[a]))
        if not d:
            continue
        entries.append((d[0], a, n))
    newest = set(n for _, _, n in sorted(entries)[-vk.INBOX_KEEP_NEWEST:])
    moving = {}
    unrouted = 0
    for d, a, n in entries:
        if n in newest:
            continue
        kind, a, b = us[n]
        block = lines[a:b]
        if any(is_pointer(l) for l in block):
            continue
        title = vk.bare(lines[a]).strip()
        if not ROUTED_RE.search("".join(block)) and not include_unrouted:
            unrouted += 1
            continue
        if vk.is_kept(re.sub(r"^[-*+]\s*", "", title), keeps):
            plan.notes.append("kept (you asked to keep it): " + title[:80])
            continue
        archive = "%s/inbox/inbox-%s.md" % (vk.HISTORY, d.strftime("%Y-%m"))
        moving[n] = Move(a, block, archive, title, "inbox")
    if unrouted:
        plan.questions.append({"title": "%d older inbox entries do not say where they went" % unrouted,
                               "lines": ["Move them to history too? (--include-unrouted)"]})
    absorb_blanks(plan, us, moving)
    plan.moves = [moving[n] for n in sorted(moving)]
    want = []
    existing = set(vk.bare(l) for l in lines if is_pointer(l))
    for arch in sorted(set(m.archive for m in plan.moves)):
        p = PTR["inbox"] + wikilink(arch)
        if p not in existing:
            want.append(p + plan.eol)
    if want:
        if log_i is not None:
            j = log_i
            while j + 1 < len(lines) and (is_pointer(lines[j + 1]) or (mask[j + 1] and "<!--" in lines[j + 1]
                                                                        and "-->" in lines[j + 1])):
                j += 1
            plan.insert_after.setdefault(j, []).extend(want)
        else:
            plan.insert_before.setdefault(start, []).extend(want)
    plan.build()
    return plan


# ---------------------------------------------------------------- history files

def history_header(kind, rel, eol):
    stem = os.path.basename(rel)[:-3]
    label = stem.split("-", 1)[1] if kind != "tasks" else stem.rsplit("-", 1)[1]
    if kind == "decisions":
        t = ("# Decisions history, %s\n\nRelated: [[decisions/log]]\n\nWhole entries moved out of [[decisions/log]] "
             "by the optimize-vault skill, word for word.\n" % label)
    elif kind == "inbox":
        t = ("# Inbox history, %s\n\nRelated: [[inbox]]\n\nEntries moved out of [[inbox]] by the optimize-vault "
             "skill, word for word, in their old order.\n" % label)
    else:
        t = ("# Done tasks, %s\n\nRelated: [[tasks]]\n\nDone items moved out of [[tasks]] by the optimize-vault "
             "skill, word for word.\n" % label)
    return t.replace("\n", eol)


def compose_history(existing, plan, rel, run_date):
    moves = [m for m in plan.moves if m.archive == rel]
    eol = plan.eol
    out = existing if existing is not None else history_header(plan.kind, rel, eol)
    if not out.endswith("\n"):
        out += eol
    out += eol + "<!-- moved here on %s -->" % run_date.isoformat() + eol
    if plan.kind != "decisions":
        out += eol
    for m in moves:
        out += m.piece(eol)
    return out


def count_block(hay, block):
    hay = "\n" + (hay or "")
    needle = "\n" + block
    n, i = 0, hay.find(needle)
    while i != -1:
        n += 1
        i = hay.find(needle, i + 1)
    return n


def proof(plan, history_before, history_after):
    """Every original line is in the new file or in a history file. Returns problems."""
    problems = []
    # 1. The new file, minus the pointer lines this run added, with every moved
    #    block put back where it was, is the original byte for byte.
    added = list(plan.added_pointers())
    rebuilt = []
    starts = dict((m.start, m) for m in plan.moves)
    new_iter = list(plan.new)
    # Remove added pointer lines (each once).
    for p in added:
        if p in new_iter:
            new_iter.remove(p)
        else:
            problems.append("an added pointer line is missing from the new file")
    k = 0
    i = 0
    orig = plan.orig
    while i < len(orig):
        if i in starts:
            rebuilt.extend(starts[i].lines)
            i += len(starts[i].lines)
            continue
        if k < len(new_iter):
            line = new_iter[k]
            if i == len(orig) - 1 and not orig[i].endswith("\n") and line.endswith("\n") and \
                    line[:-len(plan.eol)] == orig[i]:
                line = orig[i]
            rebuilt.append(line)
            k += 1
        i += 1
    if k != len(new_iter):
        problems.append("the new file has %d lines the original does not explain" % (len(new_iter) - k))
    if "".join(rebuilt) != plan.orig_text:
        problems.append("putting the moved lines back does not give the original file")
    # 2. Each moved block landed in its history file, once more than before.
    want = {}
    for m in plan.moves:
        want.setdefault((m.archive, m.text), 0)
        want[(m.archive, m.text)] += 1
    for (rel, text), n in sorted(want.items()):
        gained = count_block(history_after.get(rel), text) - count_block(history_before.get(rel), text)
        if gained < n:
            problems.append("%s is missing a moved block that starts: %s" % (rel, vk.bare(text.split("\n")[0])[:70]))
    return problems


# ---------------------------------------------------------------- run

def make_plans(root, args, today, run_date):
    keep_file = {k: vk.keep_titles(root, k) for k in KINDS}
    extra = list(args.keep or [])
    plans = []
    only = [k.strip() for k in (args.only or ",".join(KINDS)).split(",") if k.strip()]
    for kind in KINDS:
        if kind not in only:
            continue
        path = os.path.join(root, LIVE[kind])
        if not os.path.lexists(path):
            continue
        b = vk.read_bytes(path)
        why = vk.write_problem(root, LIVE[kind])
        if why or b is None:
            # Not UTF-8, a link, read-only or unreadable: the file is left exactly as it is.
            p = Plan(kind, "")
            p.refused = why or ("%s could not be read, so it was left as is." % LIVE[kind])
            p.why = p.refused
            p.orig_bytes = b
            plans.append(p)
            continue
        text = b.decode("utf-8")  # a byte-order mark stays in line 1, so it is written back as it was
        if kind == "decisions":
            p = plan_decisions(root, text, today, run_date, keep_file[kind], extra)
        elif kind == "tasks":
            p = plan_tasks(root, text, today, run_date, keep_file[kind] + extra)
        else:
            p = plan_inbox(root, text, today, run_date, keep_file[kind] + extra, args.include_unrouted)
        p.orig_bytes = b
        # A history file that cannot be written (a link, not UTF-8, read-only) stops this file's move.
        for rel in sorted(set(m.archive for m in p.moves)):
            hwhy = vk.write_problem(root, rel)
            if hwhy:
                p.refused = hwhy + " So nothing in %s moves this time." % LIVE[kind]
                p.why = p.refused
                break
        plans.append(p)
    return plans


def key_title(m):
    """The words an owner would use to name an item: the heading, or the line without its marker."""
    t = m.title
    if m.kind == "tasks":
        return re.sub(r"^[-*+] \[[xX]\]\s*", "", t)
    if m.kind == "inbox":
        return re.sub(r"^[-*+]\s*", "", t)
    return t


def save_keeps(run, root, kind, titles, today):
    if not titles:
        return
    data = vk.load_keep(root)
    items = data.get(kind, []) or []
    have = set(vk.title_key(x.get("title", "") if isinstance(x, dict) else str(x)) for x in items)
    changed = False
    for t in titles:
        if vk.title_key(t) not in have:
            items.append({"title": t, "added": today.isoformat(), "why": "the owner asked to keep it in place"})
            changed = True
    if changed:
        data[kind] = items
        run.write(vk.KEEP_REL, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def apply_plan(run, root, plan, run_date):
    """Write history files first, then the live file. Returns problems (empty = done)."""
    rels = sorted(set(m.archive for m in plan.moves))
    before = dict((r, vk.read_text(os.path.join(root, r))) for r in rels)
    after = dict((r, compose_history(before[r], plan, r, run_date)) for r in rels)
    problems = proof(plan, before, after)
    if problems:
        return problems
    written = []
    current = plan.rel
    try:
        for r in rels:
            current = r
            run.write(r, after[r])
            written.append(r)
        current = plan.rel
        run.write(plan.rel, plan.new_text, expect=plan.orig_bytes)
    except (vk.ChangedUnderUs, vk.Refused, OSError) as e:
        stuck = run.undo(written)
        msg = vk.failure_line(e, current)
        if stuck:
            raise WriteStopped(msg + " These files could not be put back, so their copies are in %s/backup: %s"
                               % (run.rel, ", ".join(stuck)))
        raise WriteStopped(msg + " Nothing was moved, and every file is as it was. Run it again once that is fixed.")
    disk = dict((r, vk.read_text(os.path.join(root, r))) for r in rels)
    live = vk.read_bytes(os.path.join(root, plan.rel))
    problems = proof(plan, before, disk)
    if live != plan.new_text.encode("utf-8"):
        problems.append("%s does not read back as written" % plan.rel)
    return problems


class WriteStopped(Exception):
    """A write failed part way. args[0] is a plain sentence that says what was put back."""
    pass


def restore(run, root, rel):
    return run.restore(rel)


def plan_sha(plans, today):
    """A fingerprint of what the owner is shown: every move, every question, every file left as is.
    --apply --expect-sha stops when the plan made at apply time is not the same one."""
    items = [today.isoformat()]
    for p in plans:
        items.append(["file", p.rel, p.refused or ""])
        for m in p.moves:
            items.append(["move", m.archive, m.text, m.heading or ""])
        for q in p.questions:
            items.append(["question", q.get("title", ""), q.get("lines", [])])
    return hashlib.sha256(json.dumps(items, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description="Tidy decisions/log.md, tasks.md and inbox.md (dry run by default).")
    ap.add_argument("--vault", default=None)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--run-dir", default=None)
    ap.add_argument("--only", default=None)
    ap.add_argument("--keep", action="append")
    ap.add_argument("--rules-checked", action="store_true")
    ap.add_argument("--include-unrouted", action="store_true")
    ap.add_argument("--today", default=None)
    ap.add_argument("--now", default=None)
    ap.add_argument("--expect-sha", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    root = vk.find_vault(args.vault)
    now = vk.parse_now(args.now) or (dt.datetime.strptime(args.today, "%Y-%m-%d") if args.today else None)
    today = (now or dt.datetime.now()).date()
    run_date = today
    plans = make_plans(root, args, today, run_date)

    rule_flags = [q for p in plans if p.kind == "decisions" and not p.refused for q in p.questions]
    # The fingerprint is of the plan the owner is first shown (no --keep, no --include-unrouted),
    # so their answers to its questions never count as a change.
    if args.keep or args.include_unrouted:
        shown = make_plans(root, argparse.Namespace(**dict(vars(args), keep=None, include_unrouted=False)),
                           today, run_date)
    else:
        shown = plans
    sha = plan_sha(shown, today)
    drifted = bool(args.apply and args.expect_sha and args.expect_sha != sha)
    stopped = args.apply and (drifted or (bool(rule_flags) and not args.rules_checked))
    warnings = []
    results = []
    run = None
    unmatched = []
    if args.apply and not stopped:
        run = vk.Run(root, args.run_dir, now)
        if args.keep:
            # Save each --keep answer under the file it matched, so the next run keeps it too.
            plain = argparse.Namespace(**dict(vars(args), keep=None))
            base = make_plans(root, plain, today, run_date)
            matched = set()
            for p in base:
                hits = [k for k in args.keep if any(vk.is_kept(key_title(m), [k]) for m in p.moves)]
                matched.update(hits)
                try:
                    save_keeps(run, root, p.kind, hits, today)
                except (vk.Refused, vk.ChangedUnderUs, OSError) as e:
                    warnings.append("Your keep answers could not be saved for next time: " +
                                    vk.failure_line(e, vk.KEEP_REL) + " They still count in this run.")
            unmatched = [k for k in args.keep if k not in matched]
    for p in plans:
        r = {"file": p.rel, "triggered": p.triggered, "why": p.why, "moves": len(p.moves),
             "lines_moved": sum(len(m.lines) for m in p.moves),
             "chars_before": len(p.orig_text), "chars_after": len(p.new_text),
             "lines_before": vk.count_lines(p.orig_text), "lines_after": vk.count_lines(p.new_text),
             "history_files": sorted(set(m.archive for m in p.moves)),
             "kept": p.notes, "questions": p.questions,
             "items": [{"title": m.title[:120], "to": m.archive, "lines": len(m.lines)} for m in p.moves]}
        if p.moves:
            before = dict((rel, vk.read_text(os.path.join(root, rel))) for rel in r["history_files"])
            after = dict((rel, compose_history(before[rel], p, rel, run_date)) for rel in r["history_files"])
            probs = proof(p, before, after)
            r["proof"] = "passed" if not probs else "FAILED: " + "; ".join(probs)
        if p.refused:
            r["refused"] = p.refused
            r.pop("proof", None)
        elif run is not None and p.moves and p.changed():
            try:
                probs = apply_plan(run, root, p, run_date)
            except WriteStopped as e:
                r["applied"] = False
                r["stopped"] = e.args[0]
                r.pop("proof", None)
                results.append(r)
                continue
            r["applied"] = not probs
            if probs:
                r["proof"] = "FAILED: " + "; ".join(probs)
            else:
                r["proof"] = "passed after writing"
                try:
                    run.note("tidy", {"file": p.rel, "moved_items": len(p.moves), "lines_moved": r["lines_moved"],
                                      "history_files": r["history_files"]})
                except OSError:
                    warnings.append("The list of changes in %s could not be updated." % run.rel)
        results.append(r)

    ok = all(not str(r.get("proof", "")).startswith("FAILED") and not r.get("stopped") for r in results)
    ok = ok and not drifted
    data = {"keep_not_found": unmatched, "mode": "apply" if (args.apply and not stopped) else ("stopped" if stopped else "dry run"),
            "results": results, "ok": ok, "run_dir": run.rel if run else None,
            "rule_questions": rule_flags, "plan_sha": sha, "plan_changed": drifted, "warnings": warnings}
    lines = []
    if drifted:
        lines.append("Tidy: STOPPED, nothing changed. The plan is not the one the owner saw: an entry was added, "
                     "changed or answered since. Run the dry run again, show the new list, and ask again.")
    elif stopped:
        lines.append("Tidy: STOPPED, nothing changed. Some old decisions hold a rule (listed below). Check that each "
                     "rule also lives in CLAUDE.md or a memory note. Keep any that do not with --keep \"<title>\". "
                     "Then run again with --apply --rules-checked.")
    elif args.apply and any(r.get("applied") for r in results):
        lines.append("Tidy: done. Copies of every file it changed are in %s." % (run.rel if run else "-"))
    elif args.apply:
        lines.append("Tidy: nothing to move, so nothing changed.")
    else:
        if any(r["moves"] and not r.get("refused") for r in results):
            lines.append("Tidy: dry run, nothing changed. To make exactly these moves after the owner's yes, add "
                         "--apply --expect-sha %s" % sha)
        else:
            lines.append("Tidy: dry run, nothing changed.")
    lines.extend(warnings)
    for k in unmatched:
        lines.append("No moving entry starts with \"%s\", so nothing was saved for it." % k)
    for r in results:
        lines.append("")
        if r.get("refused"):
            lines.append(r["refused"])
            continue
        if r.get("stopped"):
            lines.append("%s: STOPPED. %s" % (r["file"], r["stopped"]))
            continue
        if not r["triggered"]:
            lines.append("%s: nothing to do, %s." % (r["file"], r["why"]))
            continue
        lines.append("%s: %s. %d %s move (%d lines). %s characters now, %s after."
                     % (r["file"], r["why"], r["moves"], "item" if r["moves"] == 1 else "items", r["lines_moved"],
                        vk.fmt(r["chars_before"]), vk.fmt(r["chars_after"])))
        for h in r["history_files"]:
            n = sum(1 for it in r["items"] if it["to"] == h)
            lines.append("  -> %s (%d)" % (h, n))
        for k in r["kept"][:12]:
            lines.append("  " + k)
        if len(r["kept"]) > 12:
            lines.append("  ... and %d more kept" % (len(r["kept"]) - 12))
        for q in r["questions"]:
            lines.append("  QUESTION: " + q["title"])
            for ql in q["lines"][:4]:
                lines.append("      > " + ql[:160])
        if r.get("proof"):
            lines.append("  Line check: " + (r["proof"] if r["proof"].startswith("FAILED")
                                              else "every line is in the new file or a history file (" + r["proof"] + ")."))
    vk.emit(args, data, lines)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
