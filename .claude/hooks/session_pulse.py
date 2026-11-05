"""Session pulse: runs once, the moment a Claude Code session opens in this vault.

WHAT IT DOES
  Before you type anything, it hands the AI a short briefing so a brand-new
  session already knows what has been moving:
    - notes changed in the last week
    - your latest inbox captures and open to-dos
    - your other recent Claude Code sessions in this folder (title and your
      last message), so "where were we?" just works
    - a one-line summary of HANDOFF.md, if a session left work half done
      (read in full only when your message touches that work)
    - housekeeping: a note nobody indexed, a skill with no registry row,
      Claude's memory not pointed at this vault, a Python too old for
      Sheet Geek
    - one size line when the vault has grown past a budget (the memory
      index, CLAUDE.md, decisions/log.md, finished to-dos in tasks.md,
      inbox.md, or a long skill description), so Claude can offer
      "optimize my vault"; it never tidies anything on its own.
      It reads .claude/optimize-state.json and .claude/optimize-keep.json
      and stays quiet about what the owner chose to keep or leave as is,
      until that file grows again (by 10 lines or 10 percent). Near the
      hard limit it always speaks. Notes in history/, and the topic
      pages the cleanup makes from memory lines, are never listed as
      changed this week, so the owner's real notes stay visible.
    - one line after an update that skipped its cleanup (a set-up vault
      with an archives/update-* folder, but no finished "optimize my
      vault" run: no last_run in .claude/optimize-state.json and no
      report in history/reports/). Claude offers the cleanup and its
      plain report once. The line stops for good once the cleanup has
      run, or once the owner says no (Claude then creates the empty
      file .claude/optimize-offer-off). Any size items fold into that
      same line, so the briefing never offers the cleanup twice.
  You never see the briefing and never have to run anything.
  It stays quiet after a compaction and inside helper agents.

SAFETY
  Read only. It never writes a file, never touches the network, never blocks.
  On any error it prints nothing and gets out of the way.
  Runs on Python 3.9 or newer, standard library only, through run.sh.
"""

import datetime
import json
import os
import re
import sys
import time

DAYS = 7                  # "changed this week"
MAX_CHANGED = 10          # notes listed
MAX_FILES = 5000          # stop looking after this many notes, so a huge vault stays fast
OTHER_TABS_HOURS = 48     # how far back to look for your other sessions
MAX_TABS = 6
OUTPUT_LIMIT = 6000       # characters handed to the AI

SKIP_DIRS = {".git", ".obsidian", ".claude", ".trash", "outputs", "archives",
             "node_modules", "__pycache__", ".venv", "venv"}
# The kit's own documents at the top of the vault. They are never "your notes
# changed this week".
KIT_DOCS = ("README.md", "INSTALL.md", "HOW-IT-WORKS.md", "LICENSE", "LICENSE.md",
            "CHANGELOG.md", "CONTRIBUTING.md")
# Files nobody edits in normal work. When several of them share a timestamp,
# that moment was a download or an update of the kit, and any note stamped at
# the same moment came with it rather than from the owner (see install_stamps).
MARKER_FILES = KIT_DOCS + (".gitignore", ".claude/settings.json", "archives/.gitkeep", "outputs/.gitkeep",
                           "brand/logos/.gitkeep", ".obsidian/app.json", ".obsidian/core-plugins.json",
                           ".obsidian/appearance.json")
MARKER_DIRS = (".claude/hooks",)
STAMP_WINDOW = 30         # seconds: a download or an update writes its files within moments of each other
STAMP_CLUSTER = 3         # this many marker files sharing a moment make it a download or an update
# Loaded anyway, or shown in their own section below.
NOT_LISTED = {"CLAUDE.md", "inbox.md", "tasks.md", "HANDOFF.md", "MEMORY.md"}
# The mark near the top of every topic page "optimize my vault" makes from memory
# lines (the same text as HUB_MARK in its memory_index.py). Those pages, like history/,
# are never listed as changed this week, so the owner's real notes stay visible.
TOPIC_PAGE_MARK = "<!-- hub note made by the optimize-vault skill -->"

MEMORY_LINE_LIMIT = 200   # Claude Code loads only this much of MEMORY.md
MEMORY_BYTE_LIMIT = 25000
MEMORY_BUDGET_LINES = 75  # the index's own budget, well under the load limit
MEMORY_BUDGET_CHARS = 10000
# Size budgets shared with the optimize ritual ("optimize my vault"). Past one
# of these, the pulse adds one line so Claude can offer that tidy.
CLAUDE_MD_BUDGET = 18000      # characters; all of CLAUDE.md loads into every chat
DECISIONS_BUDGET = 40000      # characters in decisions/log.md
DECISIONS_OLD_DAYS = 90       # a decisions section whose newest date is older than this
TASKS_DONE_BUDGET = 20        # finished to-dos ("- [x]") still in tasks.md
INBOX_LINE_BUDGET = 100       # lines in inbox.md
SKILL_DESC_WARN = 600         # characters in one skill description (aim for 300 to 500)
OFFER_OFF = os.path.join(".claude", "optimize-offer-off")   # the owner said no to the first cleanup


def vault_root():
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(os.path.dirname(here))
    if os.path.isdir(os.path.join(root, ".claude")):
        return root
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    return env if env and os.path.isdir(env) else os.getcwd()


def read(path, limit=None):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            return fh.read(limit) if limit else fh.read()
    except OSError:
        return ""


def no_comments(text):
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


def clip(text, n):
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= n else text[: n - 3].rstrip() + "..."


KEY_PREFIX = re.compile(r"\b(?:sk|pk|rk|ghp|gho|ghu|ghs|github_pat|xox[abpr]|AKIA|AIza)[-_]?[A-Za-z0-9_\-]{8,}")
LONG_RUN = re.compile(r"[A-Za-z0-9+=_\-]{32,}")


def _hide_long(m):
    s = m.group(0)
    # a long run that mixes letters and digits is likely a key or token
    if re.search(r"\d", s) and re.search(r"[A-Za-z]", s) and s.count("-") <= 4:
        return "[hidden]"
    return s


def redact(text):
    """Never carry anything that looks like a key or token into a new session."""
    return LONG_RUN.sub(_hide_long, KEY_PREFIX.sub("[hidden]", text))


def h1(path):
    m = re.search(r"^#\s+(.+)$", read(path, 4000), re.M)
    if not m or "{{" in m.group(1):
        return ""
    return clip(m.group(1).strip(" #*"), 90)


def walk_notes(root):
    count = 0
    for dp, dns, fns in os.walk(root):
        dns[:] = sorted(d for d in dns if d not in SKIP_DIRS and not d.startswith("."))
        for f in sorted(fns):
            if f.endswith(".md"):
                yield os.path.join(dp, f)
                count += 1
                if count >= MAX_FILES:
                    return


def install_stamps(root):
    """The moments the kit was downloaded or updated: times shared by several files nobody edits."""
    stamps = []
    for rel in MARKER_FILES:
        try:
            stamps.append(os.path.getmtime(os.path.join(root, rel)))
        except OSError:
            pass
    for rel in MARKER_DIRS:
        d = os.path.join(root, rel)
        try:
            names = os.listdir(d)
        except OSError:
            continue
        for n in names:
            if n.endswith((".py", ".sh")):
                try:
                    stamps.append(os.path.getmtime(os.path.join(d, n)))
                except OSError:
                    pass
    stamps.sort()
    out = []
    for s in stamps:
        if sum(1 for t in stamps if abs(t - s) <= STAMP_WINDOW) >= STAMP_CLUSTER:
            out.append(s)
    return out


def recent_notes(root):
    now = time.time()
    cutoff = now - DAYS * 86400
    # A fresh download, or a kit update, stamps every file it writes at the same
    # moment. A note stamped at one of those moments is not news.
    stamps = install_stamps(root)
    found = []
    seen = 0
    for path in walk_notes(root):
        seen += 1
        name = os.path.basename(path)
        rel = os.path.relpath(path, root)
        if name in NOT_LISTED or name.startswith("_") or (name in KIT_DOCS and os.sep not in rel):
            continue
        if rel.split(os.sep, 1)[0] == "history":
            continue  # pages the tidy-up moved old entries into, word for word: not news
        try:
            m = os.path.getmtime(path)
        except OSError:
            continue
        if m < cutoff or m > now + 300:
            continue
        if any(abs(m - s) <= STAMP_WINDOW for s in stamps):
            continue
        if TOPIC_PAGE_MARK in read(path, 2000):
            continue  # a topic page the cleanup made from memory lines: not news either
        found.append((m, rel))
    found.sort(reverse=True)
    # The walk stops at MAX_FILES notes, so in a vault that big the count is a floor, not the whole count.
    return found[:MAX_CHANGED], len(found), seen >= MAX_FILES


def shown_of(shown, total, word="first", partial=False):
    """'first 6 of 12' when a list is cut, else '': a cut list always says how much it leaves out, so Claude
    never gives the owner the shown part as the whole count. partial: the count itself stopped early
    ('first 10 of at least 40')."""
    if partial:
        return word + " " + str(shown) + " of at least " + str(total)
    return word + " " + str(shown) + " of " + str(total) if total > shown else ""


def inbox_entries(root, n=3):
    text = no_comments(read(os.path.join(root, "inbox.md")))
    entries = re.findall(r"^\s*[-*] (\d{4}-\d{2}-\d{2}.*)$", text, re.M)
    return [clip(redact(e), 220) for e in entries[-n:]], len(entries)


LIST_ITEM = re.compile(r"^(?:[-*+]|\d+[.)]) (?:\[([ xX])\](?: |$))?(.*)$")  # the same boxes tidy.py reads


def open_tasks(root, n=6):
    """The first n open to-dos ("- [ ]"), and how many are open in all. Not open: finished ones ("- [x]"), an
    empty box with no words, a sub-item under a finished one (its parent is done), and lines inside an HTML
    comment (an unclosed one hides the rest of the file) or a code block."""
    text = no_comments(read(os.path.join(root, "tasks.md")))
    text = text.split("<!--", 1)[0]
    items, stack, fence = [], [], False
    for raw in text.splitlines():
        line = raw.expandtabs(4)
        body = line.lstrip()
        if body.startswith(("```", "~~~")):
            fence = not fence
            continue
        if fence or not body:
            continue
        indent = len(line) - len(body)
        m = LIST_ITEM.match(body)
        if not m:
            if indent == 0:
                stack = []  # a heading or a plain paragraph ends the list
            continue
        while stack and stack[-1][0] >= indent:
            stack.pop()
        under_done = bool(stack) and stack[-1][1]
        box = m.group(1)
        done = under_done or (box is not None and box != " ")
        stack.append((indent, done))
        words = m.group(2).strip()
        if box == " " and not under_done and words:
            items.append(words)
    return [clip(redact(t.replace("**", "")), 160) for t in items[:n]], len(items)


def projects_dir(data, root):
    """Where Claude Code keeps this folder's session transcripts."""
    tp = data.get("transcript_path") or ""
    if tp and os.path.isdir(os.path.dirname(tp)):
        return os.path.dirname(tp)
    base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    project = os.environ.get("CLAUDE_PROJECT_DIR") or root
    key = re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(project))
    return os.path.join(base, "projects", key)


def tail_lines(path, nbytes):
    try:
        with open(path, "rb") as fh:
            fh.seek(0, 2)
            size = fh.tell()
            fh.seek(max(0, size - nbytes))
            return fh.read().decode("utf-8", errors="ignore").splitlines()
    except OSError:
        return []


def other_sessions(data, root):
    """Titles and last messages of the owner's other recent sessions here."""
    d = projects_dir(data, root)
    current = data.get("session_id") or ""
    cutoff = time.time() - OTHER_TABS_HOURS * 3600
    rows = []
    try:
        names = [n for n in os.listdir(d) if n.endswith(".jsonl")]
    except OSError:
        return rows, 0
    for n in names:
        p = os.path.join(d, n)
        if n[:-6] == current:
            continue
        try:
            m = os.path.getmtime(p)
        except OSError:
            continue
        if m < cutoff:
            continue
        head = read(p, 200000)
        ep = re.search(r'"entrypoint"\s*:\s*"([^"]+)"', head)
        if ep and ep.group(1).startswith("sdk"):
            continue  # a scripted, headless run, not one of the owner's sessions
        title, custom, prompt = "", "", ""
        for line in reversed(tail_lines(p, 300000)):
            if not custom and '"custom-title"' in line:
                try:
                    custom = json.loads(line).get("customTitle") or ""
                except Exception:
                    pass
            if not title and '"ai-title"' in line:
                try:
                    title = json.loads(line).get("aiTitle") or ""
                except Exception:
                    pass
            if not prompt and '"last-prompt"' in line:
                try:
                    prompt = json.loads(line).get("lastPrompt") or ""
                except Exception:
                    pass
            if (custom or title) and prompt:
                break
        title = custom or title
        if title or prompt:
            rows.append((m, clip(redact(title), 70), clip(redact(prompt), 110)))
    rows.sort(reverse=True)
    return rows[:MAX_TABS], len(rows)


def table_rows(text):
    """Only real table rows count as listing a note, never an example in a sentence or a comment."""
    return "\n".join(ln for ln in no_comments(text).splitlines() if ln.lstrip().startswith("|"))


def unindexed_notes(root):
    index = table_rows(read(os.path.join(root, "context", "who-and-what.md"))
                       + "\n" + read(os.path.join(root, "projects", "README.md")))
    pdir = os.path.join(root, "projects")
    missing = []
    try:
        names = sorted(os.listdir(pdir))
    except OSError:
        return missing
    for n in names:
        full = os.path.join(pdir, n)
        if n.startswith((".", "_")) or n == "README.md":
            continue
        if n.endswith(".md"):
            base = n[:-3]
        elif os.path.isdir(full):
            base = n
        else:
            continue
        link = re.compile(r"\[\[(?:projects/)?" + re.escape(base) + r"(?:\.md)?\s*(?:[|#\]])", re.I)
        if not link.search(index) and ("projects/" + base) not in index:
            missing.append(n)
    return missing


def unregistered_skills(root):
    registry = read(os.path.join(root, "skills-registry.md"))
    sk = os.path.join(root, ".claude", "skills")
    out = []
    try:
        names = sorted(os.listdir(sk))
    except OSError:
        return out
    for n in names:
        if n.startswith(".") or not os.path.isdir(os.path.join(sk, n)):
            continue
        if not re.search(r"(?<![\w-])" + re.escape(n) + r"(?![\w-])", registry):
            out.append(n)
    return out


def memory_location(root):
    """None when Claude's memory points at this vault, else a fix-it line."""
    if os.environ.get("CLAUDE_CODE_DISABLE_AUTO_MEMORY", "").lower() in ("1", "true", "yes"):
        return None
    want = os.path.join(root, "memory", "claude")
    raw = read(os.path.join(root, ".claude", "settings.local.json")).strip()
    try:
        local = json.loads(raw) if raw else {}
    except Exception:
        return ("- .claude/settings.local.json is not valid JSON, so Claude Code ignores it, including where "
                "Claude's memory lives. Repair it (keep the owner's other settings), then ask the owner to "
                "reload the window once.")
    if not isinstance(local, dict):
        local = {}
    if local.get("autoMemoryEnabled") is False:
        return None
    have = str(local.get("autoMemoryDirectory") or "")
    if not have:
        return ("- Claude's memory is not pointed at this vault yet, so what you learn is saved outside it. "
                "Fix in passing: add \"autoMemoryDirectory\": \"" + want + "\" to .claude/settings.local.json "
                "(create the file if needed, keep anything already in it), then ask the owner to reload the "
                "window once (VS Code: Command Palette, Developer: Reload Window).")
    try:
        same = os.path.realpath(os.path.expanduser(have)) == os.path.realpath(want)
    except Exception:
        same = False
    if not same:
        return ("- Claude's memory points at " + have + ", but this vault is at " + root + " (was the folder "
                "moved?). Fix in passing: set \"autoMemoryDirectory\" in .claude/settings.local.json to \""
                + want + "\", then ask the owner to reload the window once.")
    return None


def memory_index_size(root, floors=None):
    """What to say about the size of MEMORY.md, or None when it is within budget. Near the load limit it
    always speaks. Over the budget only, it stays quiet while the index is no bigger than an optimize run
    left it (its rule lines never move, so that run could not go lower)."""
    floors = floors or {}
    path = os.path.join(root, "memory", "claude", "MEMORY.md")
    try:
        size = os.path.getsize(path)
    except OSError:
        return None
    text = read(path)
    chars = len(text)
    lines = text.count("\n")
    if size > MEMORY_BYTE_LIMIT * 0.9 or lines > MEMORY_LINE_LIMIT * 0.9:
        return ("Claude's memory index (memory/claude/MEMORY.md) is near its load limit: " + str(lines)
                + " of 200 lines, " + str(size // 1000) + " of 25 KB, and anything past the limit never loads "
                "in a new session")
    if (chars > MEMORY_BUDGET_CHARS or lines > MEMORY_BUDGET_LINES) and (
            grew(lines, floors.get("memory_lines"), lines=True) or grew(chars, floors.get("memory_chars"))):
        return ("Claude's memory index (memory/claude/MEMORY.md) is over its budget: " + str(lines)
                + " lines and " + "{:,}".format(chars) + " characters (budget 75 lines and 10,000 characters)")
    return None


DATE_RE = re.compile(r"(?<!\d)(20\d\d)-(\d\d)-(\d\d)(?!\d)")
FENCE_RE = re.compile(r"^ {0,3}(```|~~~)")


def plain_lines(text):
    """The lines of a note outside HTML comments and code fences."""
    out, fenced = [], False
    for ln in no_comments(text).splitlines():
        if FENCE_RE.match(ln):
            fenced = not fenced
            continue
        if not fenced:
            out.append(ln)
    return out


def newest_date(text):
    best = None
    for m in DATE_RE.finditer(text):
        try:
            d = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            continue
        best = d if best is None or d > best else best
    return best


def title_key(t):
    return re.sub(r"[^\w]+", "", t.lower(), flags=re.U)


def is_kept(title, keeps):
    """Same test as the optimize skill: a keep answer matches the start of the title, with or without its date."""
    k = title_key(title)
    k2 = title_key(re.sub(r"^\W*20\d\d-\d\d-\d\d(?:[ T]\d\d:\d\d)?\W*", "", title))
    for x in keeps:
        x = title_key(x)
        if x and (k.startswith(x) or k2.startswith(x)):
            return True
    return False


def old_decision_sections(text, now, keeps=()):
    """How many dated '## ' sections of decisions/log.md have nothing newer than DECISIONS_OLD_DAYS, by the
    same rules the optimize skill moves them: the heading holds a real date, any '#' or '##' heading ends a
    section, a section the owner chose to keep never counts, and neither does one that holds only headings
    and pointers to history/ (left by a tidy)."""
    today = datetime.date.fromtimestamp(now)
    cutoff = today - datetime.timedelta(days=DECISIONS_OLD_DAYS)
    lines = plain_lines(text)
    starts = [i for i, ln in enumerate(lines) if re.match(r"^#{1,2}[ \t]", ln)] + [len(lines)]
    count = 0
    for a, b in zip(starts, starts[1:]):
        if not lines[a].startswith("## "):
            continue
        head_date = newest_date(lines[a])
        if head_date is None:
            continue
        title = lines[a][3:].strip()
        if keeps and is_kept(title, keeps):
            continue
        body = [ln for ln in lines[a + 1:b] if ln.strip() and not ln.startswith("#") and "[[history/" not in ln]
        if not body:
            continue
        past = [d for d in (newest_date(ln) for ln in lines[a:b]) if d is not None and d <= today]
        newest = max(past) if past else head_date
        if newest < cutoff:
            count += 1
    return count


def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def keep_titles(root, kind):
    out = []
    for item in load_json(os.path.join(root, ".claude", "optimize-keep.json")).get(kind) or []:
        if isinstance(item, dict) and item.get("title"):
            out.append(str(item["title"]))
        elif isinstance(item, str):
            out.append(item)
    return out


def grew(now_value, floor, lines=False):
    """True when a size is clearly past what the last optimize run left (the size it could not go under).
    Lines and counts: more than 10 over, or 10 percent. Characters: 10 percent."""
    if not isinstance(floor, (int, float)) or isinstance(floor, bool):
        return True
    slack = max(10, floor * 0.1) if lines else floor * 0.1
    return now_value > floor + slack


def skill_description(path):
    """The description from a SKILL.md front matter, whitespace collapsed, or ''."""
    head = read(path, 8000)
    m = re.match(r"^---\s*\n(.*?)\n---", head, re.S)
    if not m:
        return ""
    d = re.search(r"(?ms)^description:[ \t]*(.*?)(?=^[A-Za-z_][\w-]*:|\Z)", m.group(1))
    if not d:
        return ""
    text = re.sub(r"\s+", " ", d.group(1)).strip()
    if text[:1] in (">", "|"):
        text = text[1:].lstrip("-+ ")
    if len(text) > 1 and text[0] == text[-1] and text[0] in "\"'":
        text = text[1:-1]
    return text


def size_items(root, include_memory=True):
    """Short phrases for every shared size budget this vault has crossed. After an optimize run, a size it
    could not get under (rule lines that never move, entries the owner kept) stays quiet until the file
    grows clearly past it, so the same offer does not come back every session."""
    items = []
    floors = load_json(os.path.join(root, ".claude", "optimize-state.json")).get("floors")
    floors = floors if isinstance(floors, dict) else {}
    if include_memory:
        mem = memory_index_size(root, floors)
        if mem:
            items.append(mem)
    n = len(read(os.path.join(root, "CLAUDE.md")))
    if n > CLAUDE_MD_BUDGET and grew(n, floors.get("claude_chars")):
        items.append("CLAUDE.md is " + "{:,}".format(n) + " characters (budget 18,000), and all of it loads into "
                     "every chat")
    log = read(os.path.join(root, "decisions", "log.md"))
    if len(log) > DECISIONS_BUDGET and grew(len(log), floors.get("decisions_chars")):
        items.append("decisions/log.md is " + "{:,}".format(len(log)) + " characters (budget 40,000)")
    old = old_decision_sections(log, time.time(), keep_titles(root, "decisions")) if log else 0
    if old:
        items.append("decisions/log.md has " + str(old) + " section" + ("s" if old != 1 else "")
                     + " older than 90 days")
    done = sum(1 for ln in plain_lines(read(os.path.join(root, "tasks.md"))) if re.match(r"^[-*+] \[[xX]\]", ln))
    if done > TASKS_DONE_BUDGET and grew(done, floors.get("tasks_done"), lines=True):
        items.append("tasks.md has " + str(done) + " finished to-dos (budget 20)")
    inbox_lines = read(os.path.join(root, "inbox.md")).count("\n")
    if inbox_lines > INBOX_LINE_BUDGET and grew(inbox_lines, floors.get("inbox_lines"), lines=True):
        items.append("inbox.md is " + str(inbox_lines) + " lines (budget 100)")
    long_skills = []
    sk = os.path.join(root, ".claude", "skills")
    try:
        names = sorted(os.listdir(sk))
    except OSError:
        names = []
    left = floors.get("long_skills") if isinstance(floors.get("long_skills"), list) else []
    for name in names:
        if len(skill_description(os.path.join(sk, name, "SKILL.md"))) > SKILL_DESC_WARN and name not in left:
            long_skills.append(name)
    if long_skills:
        cut = shown_of(len(long_skills[:5]), len(long_skills))
        items.append(str(len(long_skills)) + " skill description" + ("s are" if len(long_skills) != 1 else " is")
                     + " over 600 characters (" + (cut + ": " if cut else "") + ", ".join(long_skills[:5])
                     + "), and every chat loads them")
    return items


def size_line(root):
    """One line when the vault has crossed any shared size budget, else None."""
    items = size_items(root)
    if not items:
        return None
    return ("Size check: " + "; ".join(items) + ". Tell the owner once, in one plain sentence, what grew and that "
            "they can say \"optimize my vault\" to tidy it. Do not tidy, move or reword anything unasked, and never "
            "shorten or reword a line of the memory index to save space.")


def cleaned_up(root):
    """True once "optimize my vault" has finished in this vault: its state file records a run, or a
    report from it is saved in history/reports/."""
    if load_json(os.path.join(root, ".claude", "optimize-state.json")).get("last_run"):
        return True
    try:
        names = os.listdir(os.path.join(root, "history", "reports"))
    except OSError:
        return False
    return any(n.endswith(".md") and "vault-report" in n for n in names)


def updated_before(root):
    """True when an update from an older version ran here: it always leaves archives/update-*/."""
    base = os.path.join(root, "archives")
    try:
        names = os.listdir(base)
    except OSError:
        return False
    return any(n.startswith("update-") and os.path.isdir(os.path.join(base, n)) for n in names)


def cleanup_offer(root, set_up):
    """One line when an update skipped its cleanup, else None. Never on a vault with no owner content yet
    (setup not done, or never updated from an older version), never once the cleanup ran or the owner said
    no. The size check measuring this vault sets VAULT_PULSE_MEASURE, so this one-time line is not counted
    as a cost every chat carries."""
    if not set_up or os.environ.get("VAULT_PULSE_MEASURE"):
        return None
    if os.path.exists(os.path.join(root, OFFER_OFF)) or not updated_before(root) or cleaned_up(root):
        return None
    line = ("First cleanup not done yet: this vault was updated from an older version, but its cleanup has "
            "not run, so the owner never got the short plain report on how their brain was working before and "
            "what the new version does for them. Offer it once, in one or two plain sentences: they can say "
            "\"optimize my vault\", which shows one list and changes nothing until they say yes. If they say "
            "no, create the empty file .claude/optimize-offer-off so this offer stops. Do not tidy anything "
            "unasked.")
    items = size_items(root)
    if items:
        line += (" It has also grown: " + "; ".join(items) + ". Never shorten or reword a line of the memory "
                 "index to save space.")
    return line


def housekeeping(root, set_up):
    out = []
    missing = unindexed_notes(root)
    if missing:
        cut = shown_of(len(missing[:8]), len(missing))
        out.append("- Notes in projects/ that no index lists (add a row to context/who-and-what.md, and to "
                   "projects/README.md if it is live work)" + (", " + cut if cut else "") + ": "
                   + ", ".join(missing[:8]))
    unreg = unregistered_skills(root)
    if unreg:
        out.append("- Skills with no row in skills-registry.md (add the row in passing; a missing row is never "
                   "a reason not to use a skill): " + ", ".join(unreg))
    if set_up:
        loc = memory_location(root)
        if loc:
            out.append(loc)
        if not os.path.exists(os.path.join(root, "context", "who-and-what.md")):
            out.append("- context/who-and-what.md (the index of people, companies, projects and tools) is "
                       "missing, so names in messages cannot be matched. The owner can say \"update my vault\" "
                       "to add it.")
    if sys.version_info < (3, 10):
        out.append("- Python here is " + ".".join(str(x) for x in sys.version_info[:3]) + ". The vault works, "
                   "but Sheet Geek (the spreadsheet plugin) needs Python 3.10 or newer. Mention it once and "
                   "offer to help install a newer Python.")
    return out


def age(seconds):
    if seconds < 3600:
        return str(max(1, int(seconds // 60))) + " min ago"
    if seconds < 86400 * 2:
        return str(int(seconds // 3600)) + " h ago"
    return str(int(seconds // 86400)) + " days ago"


def setup_partway(root):
    """A line when intake.md says setup stopped partway, else None."""
    text = read(os.path.join(root, "intake.md"), 6000)
    if not re.search(r"\*\*Setup status:\*\*\s*in progress", text, re.I):
        return None
    m = re.search(r"\*\*Questions asked:\*\*\s*(\d+)\s*of\s*(\d+)", text)
    where = " (Questions asked: " + m.group(1) + " of " + m.group(2) + ", saved in intake.md)" if m else ""
    return ("Setup stopped partway" + where + ". Offer once to pick up where it stopped: \"set me up\" "
            "resumes from intake.md and never re-asks an answered question.")


HANDOFF_FRESH = 3600         # seconds: a session that is still open may be writing it
HANDOFF_OLD = 48 * 3600       # seconds
HANDOFF_LONG = 5000           # bytes


def handoff_goal(text):
    """First non-empty line under a '## What we were doing' heading, or ''."""
    lines = no_comments(text).splitlines()
    for i, ln in enumerate(lines):
        if re.match(r"^##\s+What we were doing\s*$", ln.strip(), re.I):
            for nxt in lines[i + 1:]:
                s = nxt.strip()
                if s.startswith("#"):
                    return ""
                if s:
                    return s.lstrip("-* ").strip()
            return ""
    return ""


def handoff_line(root):
    """One line about HANDOFF.md at the vault root, or None when there is none."""
    path = os.path.join(root, "HANDOFF.md")
    if not os.path.isfile(path):
        return None
    try:
        size = os.path.getsize(path)
        secs = time.time() - os.path.getmtime(path)
    except OSError:
        return None
    text = read(path, 20000)
    title = h1(path) or "Handoff"
    goal = handoff_goal(text)
    goal = clip(redact(goal), 200) if goal else ""
    line = ("HANDOFF.md is waiting at the vault root (written " + age(max(0, secs)) + ", "
            + "%.1f" % (size / 1000.0) + " KB): \"" + redact(title) + "\"."
            + (" Goal: " + goal + ("" if goal.endswith((".", "!", "?")) else ".") if goal else "")
            + " Read the whole file when the owner's message touches that work (its subject, \"pick up "
            "where we left off\", \"where were we\", or where things stand); for an unrelated message, "
            "answer it and leave the file alone. Delete it (or only the section you picked up, if it holds "
            "more than one) once the owner picks that work up.")
    if secs < HANDOFF_FRESH:
        line += (" It was written in the last hour, so a session that is still open may be writing it: "
                 "ask the owner once before deleting it.")
    if size > HANDOFF_LONG or secs > HANDOFF_OLD:
        line += (" It is long or old, so it may be stale or belong to another session: read its title "
                 "first, and confirm with the owner before acting on it.")
    return line


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}
    # After a compaction the summary already carries the briefing, and a helper
    # agent does not need the owner's briefing. Startup, resume and clear keep the
    # full pulse. (agent_type alone is not a helper: `claude --agent` sets it too.)
    if (data.get("source") == "compact" or data.get("agent_id")
            or "/subagents/" in str(data.get("transcript_path") or "").replace("\\", "/")):
        return
    root = vault_root()
    set_up = "{{YOUR_NAME}}" not in read(os.path.join(root, "CLAUDE.md"), 6000)

    out = [
        "VAULT PULSE (automatic, session start). The owner works out of this folder. People, companies, "
        "projects and tools: context/who-and-what.md (a hook also matches names in every message). Where "
        "files go: context/where-files-live.md. Claude's own memory: memory/claude/ (index MEMORY.md). When you "
        "pass any of this on, name things as the owner would (your to-do list, your inbox), not by file name, "
        "unless they ask where something is."
    ]
    if not set_up:
        out.append("SETUP NOT DONE YET: CLAUDE.md still says {{YOUR_NAME}}. Unless the owner is already in the "
                   "middle of setup, offer it once, in one line (they can say \"set me up\", which runs the "
                   "onboard skill). Do not start asking setup questions unasked. Until setup runs, Claude's own "
                   "memory is saved outside this vault: setup points it at memory/claude/.")
        partway = setup_partway(root)
        if partway:
            out.append(partway)

    handoff = handoff_line(root)
    if handoff:
        out.append(handoff)

    # A list cut short says so ("first 6 of 12"), so a count Claude passes on is never the shown part alone.
    # Each list is (its heading for a given cut text, its lines, how many there are in all, the word for the cut,
    # its name if it has to be left out). The heading is built from the lines really shown, after any cut for length.
    lists = []
    if set_up:
        notes, n_notes, notes_partial = recent_notes(root)
        if notes:
            lines = []
            for m, rel in notes:
                t = h1(os.path.join(root, rel))
                lines.append("- " + time.strftime("%m-%d %H:%M", time.localtime(m)) + "  " + rel
                             + ("  (" + t + ")" if t else ""))
            lists.append([lambda cut: "Notes changed in the last " + str(DAYS) + " days (newest first"
                          + (", " + cut if cut else "") + "):", lines, n_notes, "first",
                          "notes changed in the last " + str(DAYS) + " days", notes_partial])

    inbox, n_inbox = inbox_entries(root)
    if inbox:
        lists.append([lambda cut: "Latest captures in inbox.md" + (", " + cut if cut else "") + ":",
                      ["- " + e for e in inbox], n_inbox, "newest", "captures in inbox.md", False])

    tasks, n_tasks = open_tasks(root)
    if tasks:
        lists.append([lambda cut: "Open in tasks.md" + (", " + cut if cut else "")
                      + " (check the dates, some may be stale):", ["- " + t for t in tasks], n_tasks, "first",
                      "open to-dos in tasks.md", False])

    sessions, n_sessions = other_sessions(data, root)
    if sessions:
        lines = ["- " + time.strftime("%m-%d %H:%M", time.localtime(m)) + "  " + (stitle or "(untitled)") + " | "
                 + sprompt for m, stitle, sprompt in sessions]
        lists.append([lambda cut: "The owner's other sessions in this folder, last " + str(OTHER_TABS_HOURS)
                      + " hours" + (", " + cut if cut else "") + " (title | their last message). If they ask "
                      "\"where were we?\", start here:", lines, n_sessions, "newest",
                      "the owner's other sessions in the last " + str(OTHER_TABS_HOURS) + " hours", False])

    tail = []
    lint = housekeeping(root, set_up)
    if lint:
        tail.append("Housekeeping (fix in passing, then tell the owner in one line):")
        tail += lint
    # One offer at most: the first cleanup line (sizes folded in), or else the size line.
    grown = cleanup_offer(root, set_up) or size_line(root)
    if grown:
        tail.append(grown)

    # When the briefing is too long, cut the lists above, never the housekeeping and size lines. Whole lines go,
    # from the last list first (sessions, then to-dos, then captures, then changed notes), so each heading's
    # "N of M" counts only the lines still shown, and a list left out whole is named with its full count.
    end = "\n".join(tail)
    room = OUTPUT_LIMIT - (len(end) + 1 if end else 0)
    left_out = []

    def render():
        parts = list(out)
        for head, lines, total, word, name, partial in lists:
            if lines:
                parts.append(head(shown_of(len(lines), total, word, partial)))
                parts += lines
        if left_out:
            parts.append("Left out to keep this briefing short (the full count of each): " + "; ".join(left_out)
                         + ".")
        return "\n".join(parts)

    text = render()
    for entry in reversed(lists):
        while len(text) > room and entry[1]:
            entry[1].pop()
            if not entry[1]:
                left_out.insert(0, entry[4] + " (" + ("at least " if entry[5] else "") + str(entry[2]) + ")")
            text = render()
    if len(text) > room:
        text = text[: max(0, room - 3)] + "..."  # last resort: the fixed lines alone are too long
    if end:
        text = (text + "\n" + end)[:OUTPUT_LIMIT]
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": text,
    }}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
