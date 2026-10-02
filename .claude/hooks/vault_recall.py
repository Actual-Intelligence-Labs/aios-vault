"""Vault recall: runs every time you send a message, before the AI answers.

WHAT IT DOES
  When your message names a person, company, project or tool that already
  lives in the vault, it hands the AI a pointer to that thing's note (its path
  and one line about it), so a brand-new session knows who "Sam" or "the Acme
  job" is without being told. It also reminds the AI to write back: if the
  conversation changes anything, update that same note and its index row.

  Where the names come from, in order:
    1. context/who-and-what.md, the index. Both the Name and the "Also called"
       columns count, a person's first name counts on its own, and small
       dictation slips are forgiven ("Jordon" still finds Jordan). A slip is
       only forgiven when the word is not an everyday English word, so
       "page" never finds Paige and "core" never finds Corey.
    2. Every note's file name, its title, and any aliases in its frontmatter,
       so a brand-new note is findable before anyone adds a row.

  When nothing matches but the message asks about someone ("who is",
  "where are we with", "remind me about", "what did Sam say"), it tells the
  AI to search the vault before asking you.

SAFETY
  Read only. Never writes, never touches the network, never blocks a turn.
  It stays fast on big vaults: it looks at no more than MAX_NOTES notes and
  reads only the first part of each. On any error it prints nothing.
  Runs on Python 3.9 or newer, standard library only, through run.sh.
"""

import json
import os
import re
import sys
import time
import unicodedata

MAX_NOTES = 3000          # notes looked at per message, at most
HEAD_BYTES = 2048         # how much of each note is read to find its title and aliases
MAX_HITS = 6
MAX_PROMPT_WORDS = 4000
MAX_FUZZY_WORDS = 200     # slips are looked for only in the first part of a message, not in a long paste
FUZZY_BUDGET_SECONDS = 1.5
INDEX = os.path.join("context", "who-and-what.md")

# A word list, where the computer has one (Macs and most Linux do). A word in
# it is an everyday word, never a slip of a name.
DICTIONARY_PATHS = ("/usr/share/dict/words", "/usr/share/dict/web2", "/usr/dict/words")

# Everyday words close to common names, for computers with no word list.
COMMON_WORDS = set("""
page pages paged core cores cored case cases cased chose login logins logon parked tailor tailors carbon brook
brooks trace traced traces tracer windy dusting hunted hunting potter walked walking turned turning copper
baked baking banker bankers barked warden herald marshal western cotton carted cartel shown shine shines wane
mare tiler grade grades graded crane brand brandy martini marked marker marking masons meson grants granted
rosy rosey roses dawned summers winters lanes cliffs drew miles penny reed reeds rocky sandy sunny wade ward
wards chip chips crystal daisy dots fern ginger glen gray grey hazel holly jays kits lance mercy pearl piper
porter raven robin ruby rusty sage scout skip stone storm violet west wolf wren kings price prices bishop
banks brown white black green gold silver baker cook cooper fisher hill hall wood young target square shell
signal linear notion ramp apple word excel teams outlook numbers keynote edge brave close front spark wave
drive sheets slack zoom loom craft bear carry mason colon dean deal dear jean jeans mark marks bill bills
grant hope will may june april august rose dawn summer autumn winter guy max sky lane cliff earl iris ivy jade
lily nick norm sterling bob buck carol dot eve hunter jay kit walker turner chase grace
""".split())

# Looked at first, so the notes that matter most fit under the cap.
PRIORITY_DIRS = ["context", "projects", "references", "decisions", "playbooks", "brand", "memory"]
SKIP_DIRS = {".git", ".obsidian", ".claude", ".trash", "outputs", "archives",
             "node_modules", "__pycache__", ".venv", "venv"}

# Kit and system notes. Their file name and title never act as a name on their
# own (aliases written in their frontmatter still count).
STOP_BASENAMES = {
    "readme", "claude", "agents", "skill", "index", "log", "tasks", "ideas", "inbox", "taste",
    "contacts", "voice", "spoken-voice", "how-i-decide", "memory", "about-me", "about-business",
    "connections", "skills-registry", "intake", "install", "how-it-works", "license", "changelog",
    "brand", "who-and-what", "where-files-live", "handoff", "template", "home", "priorities",
    "notes", "untitled", "welcome", "todo",
}

# Ordinary words. On their own they never count as a name; inside a longer
# name ("Acme Group") they are fine.
STOP_WORDS = {
    "a", "an", "the", "and", "or", "of", "for", "to", "in", "on", "at", "by", "with", "from", "my", "our",
    "your", "me", "we", "us", "it", "is", "be", "do", "new", "old", "next", "last", "first", "main",
    "call", "card", "meeting", "meetings", "system", "project", "projects", "note", "notes", "plan",
    "brief", "summary", "review", "update", "status", "data", "email", "emails", "video", "site",
    "website", "home", "today", "tomorrow", "week", "month", "year", "team", "client", "clients",
    "company", "business", "work", "task", "tasks", "idea", "ideas", "inbox", "file", "files", "folder",
    "doc", "docs", "document", "draft", "report", "invoice", "proposal", "contract", "sales",
    "marketing", "brand", "design", "content", "research", "archive", "template", "people", "person",
    "contact", "contacts", "memory", "taste", "voice", "decision", "decisions", "log", "playbook",
    "skill", "skills", "setup", "list", "general", "misc", "other", "stuff", "thing", "things",
    "inc", "llc", "ltd", "co", "corp", "group", "services", "lab", "labs", "studio", "agency",
    "partners", "solutions", "consulting", "about", "readme", "index", "map", "money", "finance",
    "finances", "tools", "tool", "app", "apps", "account", "accounts", "order", "orders", "price",
    "pricing", "quote", "budget", "launch", "product", "products", "service", "office", "admin",
    "claude", "obsidian", "vault", "chat", "session",
}

# Courtesy titles, never a first name.
TITLES = {"mr", "mrs", "ms", "miss", "dr", "prof", "sir", "dame", "rev", "hon"}

# Everyday words that are also names of people, companies or tools ("Will",
# "Grant", "Teams", "Monday"). They count as a single-word name only when the
# message writes them capitalized in mid-sentence. Edit freely.
NAMEISH_WORDS = {
    "will", "may", "june", "april", "august", "mark", "bill", "grant", "hope", "faith", "chase", "rich",
    "joy", "art", "pat", "sue", "rob", "don", "jack", "frank", "gene", "ray", "rose", "dawn", "summer",
    "autumn", "winter", "guy", "max", "sky", "dean", "lane", "page", "cliff", "drew", "earl", "iris", "ivy",
    "jade", "jean", "lily", "miles", "nick", "norm", "penny", "pierce", "reed", "rocky", "sandy",
    "sterling", "sunny", "wade", "ward", "bob", "buck", "carol", "chip", "crystal", "daisy", "dot", "eve",
    "fern", "ginger", "glen", "gray", "grey", "hazel", "holly", "hunter", "jay", "kit", "lance", "mason",
    "mercy", "pearl", "piper", "porter", "raven", "robin", "ruby", "rusty", "sage", "scout", "skip", "star",
    "stone", "storm", "violet", "west", "wolf", "wren", "king", "price", "bishop", "banks", "brown", "white",
    "black", "green", "gold", "silver", "baker", "cook", "cooper", "fisher", "hill", "hall", "wood", "young",
    "target", "square", "shell", "gap", "box", "signal", "linear", "notion", "ramp", "apple", "meta",
    "word", "excel", "teams", "outlook", "pages", "numbers", "keynote", "edge", "brave", "monday", "make",
    "close", "copper", "front", "spark", "wave", "drive", "sheets", "slack", "zoom", "loom", "craft", "bear",
}

WHO_PATTERNS = re.compile(
    r"\b(who'?s|who is|who was|who are|remind me\b(?! to\b)|what'?s the (deal|latest|status)|latest (on|with)|"
    r"where (did|do) we (land|stand)|where are we (with|on|at)|what happened (with|to)|catch me up|"
    r"status (on|of)|update on|what did \w+ (say|want|ask|send|decide)|prep me|follow up with|"
    r"any word from|heard (back )?from|remember (the|that|when|who|what))",
    re.I,
)

# Long dashes some people put in titles ("Acme <dash> Website"), written as codes.
LONG_DASHES = chr(0x2014) + chr(0x2013)

# Messages the computer wrote, not the owner (a finished background task, a
# scheduled wake-up). Nothing to recall there.
MACHINE_SOURCES = {"system", "loop_wakeup", "schedule_wakeup", "poll_event"}
MACHINE_PREFIXES = ("<task-notification", "<local-command", "<system-reminder")


def vault_root():
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(os.path.dirname(here))
    if os.path.isdir(os.path.join(root, ".claude")):
        return root
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    return env if env and os.path.isdir(env) else os.getcwd()


def norm(s):
    """Lowercase, accents off, punctuation to single spaces."""
    if not s.isascii():
        s = unicodedata.normalize("NFKD", s)
        s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[\W_]+", " ", s.lower()).strip()


def capitalized_mid_sentence(prompt, word):
    """True when the word appears capitalized somewhere other than a sentence start."""
    pat = re.compile(r"\b" + re.escape(word[:1].upper() + word[1:].lower()) + r"\b")
    for m in pat.finditer(prompt):
        before = prompt[: m.start()].rstrip()
        if before and before[-1] not in ".!?:\n\"'(":
            return True
    return False


_DICTIONARY = None


def dictionary():
    """Lowercase words from the computer's word list, loaded only when a slip needs checking."""
    global _DICTIONARY
    if _DICTIONARY is None:
        _DICTIONARY = set()
        for path in DICTIONARY_PATHS:
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                    for line in fh:
                        w = line.strip()
                        if w and w.islower():
                            _DICTIONARY.add(w)
            except OSError:
                continue
            if _DICTIONARY:
                break
    return _DICTIONARY


def everyday_word(t):
    """True for an ordinary English word ("page", "parked"), which is never a slip of a name."""
    forms = {t}
    for suffix, back in (("ing", ""), ("ing", "e"), ("ed", ""), ("ed", "e"), ("es", ""), ("s", ""),
                         ("er", ""), ("er", "e"), ("ly", "")):
        if t.endswith(suffix) and len(t) - len(suffix) >= 3:
            forms.add(t[: -len(suffix)] + back)
    if any(f in COMMON_WORDS for f in forms):
        return True
    words = dictionary()
    return any(f in words for f in forms)


def head_of(path, limit=HEAD_BYTES):
    try:
        with open(path, "rb") as fh:
            return fh.read(limit).decode("utf-8", errors="ignore")
    except OSError:
        return ""


def no_comments(text):
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


def clip(text, n):
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= n else text[: n - 3].rstrip() + "..."


def live_notes(root):
    """Relative paths of up to MAX_NOTES notes, the important folders first."""
    out = []
    seen_dirs = set()

    def walk(start):
        for dp, dns, fns in os.walk(start):
            dns[:] = sorted(d for d in dns if d not in SKIP_DIRS and not d.startswith("."))
            for f in sorted(fns):
                if f.endswith(".md"):
                    out.append(os.path.relpath(os.path.join(dp, f), root))
                    if len(out) >= MAX_NOTES:
                        return True
        return False

    for d in PRIORITY_DIRS:
        full = os.path.join(root, d)
        if os.path.isdir(full):
            seen_dirs.add(d)
            if walk(full):
                return out
    try:
        entries = sorted(os.listdir(root))
    except OSError:
        return out
    for n in entries:
        full = os.path.join(root, n)
        if n.endswith(".md") and os.path.isfile(full):
            out.append(n)
            if len(out) >= MAX_NOTES:
                return out
    for n in entries:
        full = os.path.join(root, n)
        if n in seen_dirs or n in SKIP_DIRS or n.startswith(".") or not os.path.isdir(full):
            continue
        if walk(full):
            return out
    return out


def frontmatter(text):
    if not text.startswith("---"):
        return ""
    end = text.find("\n---", 3)
    return text[3:end] if end > 0 else ""


def frontmatter_aliases(text):
    fm = frontmatter(text)
    if not fm:
        return []
    m = re.search(r"^aliases:\s*\[(.*?)\]\s*$", fm, re.M)
    if m:
        items = m.group(1).split(",")
    else:
        m = re.search(r"^aliases:\s*\n((?:[ \t]*-[ \t]*.+\n?)+)", fm, re.M)
        if not m:
            return []
        items = [re.sub(r"^\s*-\s*", "", ln) for ln in m.group(1).splitlines()]
    out = []
    for a in items:
        a = a.strip().strip("'\"").strip()
        if a and "{{" not in a:
            out.append(a)
    return out


def h1_of(text):
    m = re.search(r"^#\s+(.+)$", no_comments(text), re.M)
    if not m:
        return ""
    t = m.group(1).strip().strip("#*").strip()
    return "" if "{{" in t else t


def status_line(path):
    """The note's dated status line, or its frontmatter status, in one line."""
    text = no_comments(head_of(path, 8000))
    m = re.search(r"^\s*(?:[-*]\s+)?\*\*Status\b(.*)$", text, re.M)
    if m:
        line = "Status" + m.group(1)
        if "{{" not in line:
            return clip(line.replace("**", ""), 170)
    m = re.search(r"^status:\s*([^#\n]+)", frontmatter(text), re.M)
    if m and "{{" not in m.group(1) and m.group(1).strip():
        return "status: " + clip(m.group(1), 40)
    return ""


def by_basename(notes):
    table = {}
    for rel in sorted(notes, key=lambda r: (r.startswith("memory" + os.sep), len(r))):
        b = os.path.basename(rel)[:-3].lower()
        table.setdefault(b, rel)
    return table


def resolve(root, target, basenames):
    """A wikilink or path from the Home column, as a path that exists if possible."""
    target = target.strip().strip("`").strip()
    if target.lower().endswith(".md"):
        target = target[:-3]
    target = target.replace("\\", "/").lstrip("./")
    if not target:
        return ""
    if os.path.isfile(os.path.join(root, target + ".md")):
        return os.path.normpath(target + ".md")
    if "/" in target:
        tail = "/" + target.lower() + ".md"
        for rel in basenames.values():
            if ("/" + rel.replace(os.sep, "/").lower()).endswith(tail):
                return rel
    hit = basenames.get(os.path.basename(target).lower())
    return hit or target + ".md"


def split_cells(line):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|") and not line.endswith("\\|"):
        line = line[:-1]
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", line)]


def curated_rows(root, basenames):
    rows = []
    text = no_comments(head_of(os.path.join(root, INDEX), 600000))
    in_people = False
    for line in text.splitlines():
        if line.startswith("#"):
            in_people = "people" in line.lower()
            continue
        if not line.lstrip().startswith("|"):
            continue
        cells = split_cells(line)
        if len(cells) < 4:
            continue
        name, also, home = cells[0], cells[1], cells[-1]
        what = " | ".join(c for c in cells[2:-1] if c)
        if not name or name.lower() == "name" or set(name) <= set("-: ") or "{{" in name:
            continue
        m = re.search(r"\[\[([^\]|#]+)", home) or re.search(r"\]\(([^)#\s]+)", home)
        target = m.group(1) if m else home
        path = resolve(root, target, basenames) if target and "{{" not in target else ""
        # (alias, written by the owner?) Names the owner wrote count even when every
        # word is an ordinary one ("The Lab"); a derived first name does not.
        aliases = [(name, True)]
        plain = re.sub(r"\s*\([^)]*\)", "", name).strip()
        if plain and plain != name:
            aliases.append((plain, True))
        for a in re.split(r"[,;]", also):
            a = a.strip().strip("'\"").strip()
            if a and "{{" not in a and a.lower() not in ("-", "none", "n/a", "na"):
                aliases.append((a, True))
        if in_people:
            # people are mostly called by their first name: "Jordan Lee" is also "Jordan"
            words = [w for w in re.split(r"\s+", plain or name) if w]
            if len(words) >= 2 and words[0].rstrip(".").lower() not in TITLES:
                aliases.append((words[0], False))
        rows.append({"label": name, "what": "" if "{{" in what else what, "home": path,
                     "aliases": aliases, "rank": 0})
    return rows


def auto_rows(root, notes):
    rows = []
    index_rel = os.path.normpath(INDEX)
    for rel in notes:
        if os.path.normpath(rel) == index_rel:
            continue
        name = os.path.basename(rel)
        base = name[:-3]
        if name.startswith(("_", ".")) or re.fullmatch(r"\d{4}-\d{2}-\d{2}.*", base):
            continue  # templates and daily notes
        text = head_of(os.path.join(root, rel))
        aliases = [(a, True) for a in frontmatter_aliases(text)]
        title = h1_of(text)
        if base.lower() not in STOP_BASENAMES:
            aliases.append((base.replace("-", " ").replace("_", " "), False))
            for seg in re.split(r"\s*[:(|/," + LONG_DASHES + r"]\s*|\s+-\s+", title):
                seg = seg.strip(" )*#")
                if seg:
                    aliases.append((seg, False))
        if aliases:
            rows.append({"label": title or base, "what": "", "home": rel, "aliases": aliases, "rank": 1})
    return rows


def usable(alias_norm, explicit):
    words = alias_norm.split()
    if not words:
        return False
    if len(words) == 1:
        w = words[0]
        return len(w) >= 3 and w not in STOP_WORDS and not w.isdigit()
    if explicit:
        return True               # "file map", written on purpose as another name for a note
    return any(w not in STOP_WORDS and not w.isdigit() for w in words)


def prompt_index(prompt):
    words = norm(prompt).split()[:MAX_PROMPT_WORDS]
    grams = set()
    for n in range(1, 6):
        for i in range(len(words) - n + 1):
            grams.add(" ".join(words[i:i + n]))
    joined = {a + b for a, b in zip(words, words[1:])}
    # Words written with a capital letter, as typed (names usually are).
    capital = set()
    for m in re.finditer(r"[^\W_]+", prompt[:20000]):
        tok = m.group(0)
        if tok[:1].isupper() and not (len(tok) > 1 and tok.isupper()):
            capital.update(norm(tok).split())
    head = words[:MAX_FUZZY_WORDS]
    tokens = []
    seen = set()
    for w in head:
        if len(w) >= 4 and w not in seen and w not in STOP_WORDS and not w.isdigit():
            seen.add(w)
            tokens.append(w)
    by_len = {}
    for n in (2, 3):
        seen_g = set()
        for i in range(len(head) - n + 1):
            g = " ".join(head[i:i + n])
            if g not in seen_g:
                seen_g.add(g)
                by_len.setdefault(n, []).append(g)
    return {"grams": grams, "joined": joined, "words": set(words), "text": " " + " ".join(words) + " ",
            "tokens": tokens, "grams_by_len": by_len, "capital": capital}


def exact_hit(a, idx):
    if a in idx["grams"] or (a + "s") in idx["grams"]:
        return True
    if a.count(" ") >= 5 and (" " + a + " ") in idx["text"]:
        return True
    squashed = a.replace(" ", "")
    # "blue bird" finds "Bluebird", and "bluebird" finds "Blue Bird"
    return len(squashed) >= 5 and (squashed in idx["joined"] or squashed in idx["words"])


def edits(a, b, limit):
    """How many letters differ (insert, delete or swap one), stopping early past the limit."""
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        if min(cur) > limit:
            return limit + 1
        prev = cur
    return prev[-1]


def skeleton(w):
    return re.sub(r"[aeiouyh]", "", w)


def close_word(t, a):
    """A dictation slip of the same word. Names under 5 letters must match exactly."""
    if t == a:
        return True
    if len(a) < 5 or t[0] != a[0]:
        return False
    limit = 2 if len(a) >= 8 else 1
    if abs(len(t) - len(a)) > limit:
        return False
    # 5-letter names: only vowel-ish slips (Sara for Sarah), so "grade" never finds "Grace"
    if len(a) == 5 and skeleton(t) != skeleton(a):
        return False
    return edits(t, a, limit) <= limit


def believable_slip(t, idx):
    """A near miss counts only when it is not an everyday word ("page" is never Paige). Where the
    computer has no word list, it must also be written with a capital letter, as names usually are."""
    if everyday_word(t):
        return False
    return bool(dictionary()) or t in idx["capital"]


def fuzzy_hit(a, idx, deadline):
    """A slip in a name: "Jordon" for "Jordan", "Jordon Lee" for "Jordan Lee"."""
    if time.time() > deadline:
        return ""
    parts = a.split()
    if len(parts) == 1:
        if len(a) < 5:
            return ""
        for t in idx["tokens"]:
            if t != a and close_word(t, a) and believable_slip(t, idx):
                return t
        return ""
    if len(parts) > 3 or not any(len(w) >= 5 for w in parts):
        return ""
    for g in idx["grams_by_len"].get(len(parts), ()):
        gw = g.split()
        if all(close_word(x, y) for x, y in zip(gw, parts)):
            if all(x == y or believable_slip(x, idx) for x, y in zip(gw, parts)):
                return g
    return ""


def match(prompt, rows):
    idx = prompt_index(prompt)
    deadline = time.time() + FUZZY_BUDGET_SECONDS
    found = []
    for row in rows:
        best = None
        for alias, explicit in row["aliases"]:
            a = norm(alias)
            if not usable(a, explicit):
                continue
            said = ""
            if exact_hit(a, idx):
                said = a
                # "Will", "Teams", "Monday": a name only when written like one
                if " " not in a and a in NAMEISH_WORDS and not capitalized_mid_sentence(prompt, a):
                    said = ""
            elif row["rank"] == 0:
                said = fuzzy_hit(a, idx, deadline)
            if said and (best is None or len(a) > len(best[1])):
                best = (said, a)
        if best:
            hit = dict(row)
            hit["said"], hit["alias"] = best
            found.append(hit)
    # Every matching index row gets its own line (several people can share
    # context/contacts as home). A note found only by its title drops out when
    # an index row already points at it.
    indexed_homes = {h["home"] for h in found if h["rank"] == 0 and h["home"]}
    out, seen = [], set()
    for h in sorted(found, key=lambda h: (h["rank"], -len(h["alias"]))):
        if h["rank"] > 0:
            if h["home"] in indexed_homes or h["home"] in seen:
                continue
            seen.add(h["home"])
        out.append(h)
    return out[:MAX_HITS]


def is_machine(data, prompt):
    if str(data.get("source") or "") in MACHINE_SOURCES:
        return True
    return prompt.lstrip().startswith(MACHINE_PREFIXES)


def hit_line(root, h, status_shown):
    home = h["home"]
    index = INDEX.replace(os.sep, "/")
    where = home if home else "(no note yet, only its row in " + index + ")"
    if home and not os.path.isfile(os.path.join(root, home)):
        where = home + " (that note is missing: fix the Home link in the index)"
    slip = h["said"] != h["alias"]
    if h["rank"] == 0:
        who = clip(h["label"], 60) + " (row in " + index
        if slip:
            who = ("probably " + who + "; \"" + h["said"] + "\" looks like a slip for \"" + h["alias"]
                   + "\": if it is them, add \"" + h["said"] + "\" to Also called")
        who += ")"
    else:
        who = "the note \"" + clip(h["label"], 60) + "\""
    said = "\"" + h["said"] + "\""
    parts = []
    if h["what"]:
        parts.append(clip(h["what"], 160))
    if home and home not in status_shown and os.path.isfile(os.path.join(root, home)):
        status_shown.add(home)
        st = status_line(os.path.join(root, home))
        if st:
            parts.append(st)
    return ("- " + said + " = " + who + " -> " + where.replace(os.sep, "/")
            + (": " + " | ".join(parts) if parts else ""))


def write_back(hits):
    text = ("WRITE BACK: if this conversation changes anything about one of them (a status, a decision, a new "
            "fact, a new person), update that same note in place before you finish, including its dated status "
            "line (**Status (YYYY-MM-DD):** ...) if it has one.")
    if any(h["rank"] == 0 for h in hits):
        text += (" For a name from the index, keep its row in context/who-and-what.md in step, and add any new "
                 "spelling the owner used to Also called.")
    loose = sorted({h["home"].replace(os.sep, "/") for h in hits
                    if h["rank"] > 0 and h["home"].replace(os.sep, "/").startswith("projects/")})
    if loose:
        text += (" Not in the index yet: " + ", ".join(loose) + ". Give each a row in context/who-and-what.md "
                 "in passing.")
    return text + " Never create a second note for the same thing."


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    if not isinstance(data, dict):
        return
    prompt = data.get("prompt") or data.get("user_prompt") or data.get("userPrompt") or ""
    if not isinstance(prompt, str) or not prompt.strip() or is_machine(data, prompt):
        return
    root = vault_root()
    notes = live_notes(root)
    basenames = by_basename(notes)
    rows = curated_rows(root, basenames) + auto_rows(root, notes)
    hits = match(prompt, rows)
    lines = []
    if hits:
        lines.append("VAULT RECALL (automatic): names in this message match notes in this vault. Read the home "
                     "note before answering, and never ask the owner to re-explain who or what this is.")
        status_shown = set()
        for h in hits:
            lines.append(hit_line(root, h, status_shown))
        lines.append(write_back(hits))
    elif WHO_PATTERNS.search(prompt):
        lines.append("VAULT RECALL: no name in this message matched the vault's index. If it refers to a person, "
                     "company, project or thing you do not recognize, search the vault first (for example grep -ril "
                     "\"the name\" context projects references decisions memory) and read what you find. Only then "
                     "ask the owner, and add a row to context/who-and-what.md so the next session knows it.")
    if lines:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": "\n".join(lines)[:4000],
        }}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
