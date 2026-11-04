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
      Claude's memory not pointed at this vault, over its budget or near
      its size limit,
      a Python too old for Sheet Geek
  You never see the briefing and never have to run anything.
  It stays quiet after a compaction and inside helper agents.

SAFETY
  Read only. It never writes a file, never touches the network, never blocks.
  On any error it prints nothing and gets out of the way.
  Runs on Python 3.9 or newer, standard library only, through run.sh.
"""

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

MEMORY_LINE_LIMIT = 200   # Claude Code loads only this much of MEMORY.md
MEMORY_BYTE_LIMIT = 25000
MEMORY_BUDGET_LINES = 75  # the index's own budget, well under the load limit
MEMORY_BUDGET_CHARS = 10000


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
    for path in walk_notes(root):
        name = os.path.basename(path)
        rel = os.path.relpath(path, root)
        if name in NOT_LISTED or name.startswith("_") or (name in KIT_DOCS and os.sep not in rel):
            continue
        try:
            m = os.path.getmtime(path)
        except OSError:
            continue
        if m < cutoff or m > now + 300:
            continue
        if any(abs(m - s) <= STAMP_WINDOW for s in stamps):
            continue
        found.append((m, rel))
    found.sort(reverse=True)
    return found[:MAX_CHANGED]


def inbox_entries(root, n=3):
    text = no_comments(read(os.path.join(root, "inbox.md")))
    entries = re.findall(r"^\s*[-*] (\d{4}-\d{2}-\d{2}.*)$", text, re.M)
    return [clip(redact(e), 220) for e in entries[-n:]]


def open_tasks(root, n=6):
    text = no_comments(read(os.path.join(root, "tasks.md")))
    items = re.findall(r"^\s*[-*] \[ \] (.+)$", text, re.M)
    return [clip(redact(t.replace("**", "")), 160) for t in items[:n]]


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
        return rows
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
    return rows[:MAX_TABS]


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


def memory_index_size(root):
    path = os.path.join(root, "memory", "claude", "MEMORY.md")
    try:
        size = os.path.getsize(path)
    except OSError:
        return None
    text = read(path)
    chars = len(text)
    lines = text.count("\n")
    if size > MEMORY_BYTE_LIMIT * 0.9 or lines > MEMORY_LINE_LIMIT * 0.9:
        return ("- Claude's memory index (memory/claude/MEMORY.md) is near its load limit: " + str(lines)
                + " of 200 lines, " + str(size // 1000) + " of 25 KB. Anything past the limit never loads in "
                "a new session. Compact it this session: merge duplicates, keep one short line per note, move "
                "detail into the notes themselves.")
    if chars > MEMORY_BUDGET_CHARS or lines > MEMORY_BUDGET_LINES:
        return ("- Claude's memory index (memory/claude/MEMORY.md) is over its budget: " + str(lines)
                + " lines and " + str(chars) + " characters (budget 75 lines and 10,000 characters; Claude "
                "Code stops loading at 200 lines or 25 KB). Longest index lines: " + longest_titles(text)
                + ". Shorten those, or group a topic's lines under one hub note with a single index line; a "
                "new memory joins its closest hub. Mention it once; no big rewrite unasked.")
    return None


def longest_titles(text, n=5):
    """The titles of the n longest '- [Title](...)' index lines, longest first."""
    rows = [ln.rstrip("\n") for ln in text.splitlines() if ln.startswith("- [")]
    rows.sort(key=len, reverse=True)
    out = []
    for ln in rows[:n]:
        m = re.match(r"^- \[([^\]]*)\]", ln)
        if m:
            out.append(clip(m.group(1), 60))
    return "; ".join(out) or "(none in the usual '- [Title](file.md)' form)"


def housekeeping(root, set_up):
    out = []
    missing = unindexed_notes(root)
    if missing:
        out.append("- Notes in projects/ that no index lists (add a row to context/who-and-what.md, and to "
                   "projects/README.md if it is live work): " + ", ".join(missing[:8])
                   + (" and more" if len(missing) > 8 else ""))
    unreg = unregistered_skills(root)
    if unreg:
        out.append("- Skills with no row in skills-registry.md (add the row in passing; a missing row is never "
                   "a reason not to use a skill): " + ", ".join(unreg))
    size = memory_index_size(root)
    if size:
        out.append(size)
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
        "files go: context/where-files-live.md. Claude's own memory: memory/claude/ (index MEMORY.md)."
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

    if set_up:
        notes = recent_notes(root)
        if notes:
            out.append("Notes changed in the last " + str(DAYS) + " days (newest first):")
            for m, rel in notes:
                t = h1(os.path.join(root, rel))
                out.append("- " + time.strftime("%m-%d %H:%M", time.localtime(m)) + "  " + rel
                           + ("  (" + t + ")" if t else ""))

    inbox = inbox_entries(root)
    if inbox:
        out.append("Latest captures in inbox.md:")
        out += ["- " + e for e in inbox]

    tasks = open_tasks(root)
    if tasks:
        out.append("Open in tasks.md (check the dates, some may be stale):")
        out += ["- " + t for t in tasks]

    sessions = other_sessions(data, root)
    if sessions:
        out.append("The owner's other sessions in this folder, last " + str(OTHER_TABS_HOURS) + " hours "
                   "(title | their last message). If they ask \"where were we?\", start here:")
        for m, stitle, sprompt in sessions:
            out.append("- " + time.strftime("%m-%d %H:%M", time.localtime(m)) + "  "
                       + (stitle or "(untitled)") + " | " + sprompt)

    lint = housekeeping(root, set_up)
    if lint:
        out.append("Housekeeping (fix in passing, then tell the owner in one line):")
        out += lint

    text = "\n".join(out)
    if len(text) > OUTPUT_LIMIT:
        text = text[: OUTPUT_LIMIT - 3] + "..."
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": text,
    }}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
