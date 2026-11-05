"""Shared helpers for the optimize-vault scripts.

Nothing here runs on its own. The other scripts in this folder import it.
Standard library only, Python 3.9 or newer.

The budgets below are the same numbers the session briefing uses, so the
briefing and this skill always agree on when a file has grown too big.
"""

import sys
sys.dont_write_bytecode = True  # never leave a __pycache__ folder in the vault
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import unicodedata

# ---------------------------------------------------------------- budgets
MEMORY_LINES = 75            # memory/claude/MEMORY.md, lines
MEMORY_CHARS = 10000         # memory/claude/MEMORY.md, characters
MEMORY_LOAD_LINES = 200      # Claude Code never loads past this
MEMORY_LOAD_BYTES = 25000
CLAUDE_WARN = 18000          # CLAUDE.md, characters
DECISIONS_CHARS = 40000      # decisions/log.md, characters
DECISIONS_DAYS = 90          # decisions/log.md, oldest entry age in days
DECISIONS_KEEP_NEWEST = 10   # never move the newest entries just to get under the size
TASKS_DONE = 20              # tasks.md, done items
INBOX_LINES = 100            # inbox.md, lines
INBOX_KEEP_NEWEST = 40       # entries that stay in inbox.md after a tidy
DESC_MIN = 300               # skill description, characters
DESC_MAX = 500
DESC_WARN = 600
NOTE_BIG = 40 * 1024         # a single note over this is worth a look
MEDIA_BIG = 1024 * 1024      # media files this big are offered for a move out
INDEX_TARGET_LINES = 70      # the index plan aims a little under the budget,
INDEX_TARGET_CHARS = 9500    # so the next few memories do not tip it over
HUB_MIN_LINES = 3            # fewer lines than this never make a hub
HUB_MAX_LINES = 20           # a hub page holds at most this many lines; more make a second page

HISTORY = "history"
STATE_REL = ".claude/optimize-state.json"
KEEP_REL = ".claude/optimize-keep.json"
SAVE_POINTS_FLAG = ".claude/save-points-on"

SKIP_WALK = {".git", ".trash", "node_modules", "__pycache__", ".venv", "venv"}
NOT_NOTES = {"archives", "outputs", HISTORY}

DATE_RE = re.compile(r"(?<!\d)(20\d\d)-(\d\d)-(\d\d)(?!\d)")
FENCE_RE = re.compile(r"^ {0,3}(```|~~~)")
HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.*?)[ \t#]*$")
INDEX_LINE_RE = re.compile(r"^\s*[-*+] +(\[[^\]]*\]\([^)]+\)|\[\[[^\]]+\]\])")
MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
WIKI_LINK_RE = re.compile(r"!?\[\[([^\]|#]+)(?:#([^\]|]*))?(?:\|[^\]]*)?\]\]")

# Words that make a line a rule or an everyday default. A line with any of
# them stays where it is, word for word. This list is broad on purpose: a
# line that stays costs a few characters, a line that moves by mistake can
# change how Claude behaves.
RULE_WORDS = re.compile(
    r"\b(never|always|must|mustn'?t|should|shouldn'?t|don'?t|do not|does not|doesn'?t|can'?t|cannot|won'?t|"
    r"isn'?t|aren'?t|no|not|nothing|none|nobody|only|default|defaults|every|each|ask|asks|first|before|"
    r"instead|unless|until|means|mean|wins|ban|bans|banned|avoid|prefer|prefers|exception|exceptions|except|"
    r"rule|rules|required|requires|ok|ok'd|okay|careful|stop|keep|skip|without|wait|waits|confirm|approval|"
    r"approve|yes|forbidden|allowed|ever|gate|gated|limit|cap|capped|over|under|max|min|budget)\b", re.I)
RULE_SYMBOLS = re.compile(r"(=|->|=>|→|!|\bvs\b)")
# Lines that set an everyday default with no rule word: "Preferred tone: casual",
# "Timezone is Eastern", "Prices in dollars", "Spelling is British".
DEFAULT_WORDS = re.compile(
    r"\b(prefer\w*|tone|style|styles|format|formats|formatting|time ?zone|timezones?|currency|currencies|"
    r"dollars?|euros?|spelling|spelled|spelt|sign-?offs?|units|metric|imperial|language)\b", re.I)
SETTING_TITLE = re.compile(r"^\s*\S.*?\s(is|are|as|in)\s+\S", re.I)
CAPS_WORD = re.compile(r"\b[A-Z]{3,}\b")
IMPERATIVES = set("""
add answer ask avoid book build call cap check clean close confirm copy cut delete diagnose do draft drop
email fan file fill find fire fix follow get give grill hand handle keep lead leave let link list load log
look make mark match measure merge move name never offer open pick post prefer pull push put read rebuild
record remove rename reply report rerun run save say search see send serialize set ship show sign skip
start stay stop store submit switch tag take tell test think time trim try turn update use verify wait
watch write
""".split())
# Rules-type headings in the memory index. Every line under one stays.
RULE_HEADING = re.compile(
    r"\b(rules?|how to work|work(?:ing)? with|defaults?|always|never|musts?|principles?|standing|"
    r"guardrails?|non-?negotiables?|hard lines?|do'?s|don'?ts?|safety)\b", re.I)
# Stricter set for old decisions: these words mean the entry may hold a rule
# that lives nowhere else.
DECISION_RULE_WORDS = re.compile(
    r"\b(never|always|must|must not|mustn'?t|do not|don'?t|exception|rule|from now on|no longer|stop)\b", re.I)

# Secret files and secret-looking text. Only a path and a kind are ever
# shown, never the text itself.
SECRET_NAME = re.compile(
    r"((^|/)\.env(\.[^/]*)?$|(^|/)client_secret[^/]*\.json$|credentials[^/]*\.json$|service-account[^/]*\.json$|"
    r"\.pem$|\.key$|\.p12$|\.pfx$|\.token$|(^|/)id_(rsa|ed25519|ecdsa)$|\.keystore$|(^|/)\.netrc$)", re.I)
SECRET_NAME_OK = re.compile(r"(\.env\.(example|sample|template)$)", re.I)
SECRET_TEXT = re.compile(
    r"sk-ant-[A-Za-z0-9_-]{20,}|\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}|\bsk_(?:live|test)_[A-Za-z0-9]{16,}|"
    r"ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[0-9A-Z]{16}|xox[bpa]-[A-Za-z0-9-]{10,}|"
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|AIza[0-9A-Za-z_-]{35}|ya29\.[0-9A-Za-z_-]{20,}|GOCSPX-[A-Za-z0-9_-]{10,}|"
    r"[\"']?(?:refresh_token|client_secret|api[_-]?key|secret[_-]?key|access[_-]?token)[\"']?\s*[:=]\s*[\"']?"
    r"[A-Za-z0-9_\-./+]{20,}", re.I)
MEDIA_EXT = re.compile(
    r"\.(png|jpe?g|gif|webp|heic|heif|tiff?|bmp|psd|mp4|mov|m4v|avi|mkv|webm|m4a|wav|mp3|aiff?|flac|ogg|"
    r"pdf|docx?|pptx?|xlsx?|key|pages|numbers|zip|tar|gz|tgz|7z|rar|dmg|iso|safetensors|pth|npy|bin)$", re.I)
TEXT_EXT = re.compile(r"(\.(md|txt|json|ya?ml|toml|ini|cfg|conf|py|js|ts|sh|csv|env)|/\.env[^/]*|^\.env[^/]*)$", re.I)
MEDIA_OK_DIRS = ("brand/logos/", "outputs/", ".obsidian/", "archives/", ".git/")


# ---------------------------------------------------------------- basics

def now_stamp(now=None):
    n = now or dt.datetime.now()
    return n.strftime("%Y-%m-%d-%H%M")


def parse_now(text):
    """--now "YYYY-MM-DD HH:MM" for tests; None means the real clock."""
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(text, fmt)
        except ValueError:
            pass
    raise SystemExit("--now must look like 2026-11-04 15:30")


def nfc(s):
    return unicodedata.normalize("NFC", s)


def rel_of(root, path):
    return os.path.relpath(path, root).replace(os.sep, "/")


def read_bytes(path):
    """The file's bytes, or None when it is missing or cannot be read (no permission, a folder, a broken link)."""
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except OSError:
        return None


def is_utf8(b):
    """True when these bytes are valid UTF-8 text (a byte-order mark is fine)."""
    try:
        (b or b"").decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def has_bom(b):
    return bool(b) and b.startswith(b"\xef\xbb\xbf")


def read_text(path):
    b = read_bytes(path)
    if b is None:
        return None
    if b.startswith(b"\xef\xbb\xbf"):
        b = b[3:]
    return b.decode("utf-8", errors="replace")


def sha_bytes(b):
    return hashlib.sha256(b or b"").hexdigest()


def sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def norm_hash(text):
    """Hash that ignores line endings and a byte-order mark (same rule as update-vault)."""
    b = text.encode("utf-8") if isinstance(text, str) else text
    if b.startswith(b"\xef\xbb\xbf"):
        b = b[3:]
    return hashlib.sha256(b.replace(b"\r\n", b"\n").replace(b"\r", b"\n")).hexdigest()


def split_keep(text):
    """Split on \\n keeping each line's ending, so ''.join() gives the text back exactly."""
    if not text:
        return []
    parts = text.split("\n")
    out = [p + "\n" for p in parts[:-1]]
    if parts[-1]:
        out.append(parts[-1])
    return out


def bare(line):
    return line.rstrip("\r\n")


def eol_of(lines):
    crlf = sum(1 for l in lines if l.endswith("\r\n"))
    return "\r\n" if crlf and crlf * 2 >= len(lines) else "\n"


def count_lines(text):
    """Lines the way `wc -l` and the session briefing count them."""
    return (text or "").count("\n")


def tokens(chars):
    return (chars + 3) // 4


def fmt(n):
    return format(n, ",")


def dates_in(text):
    out = []
    for m in DATE_RE.finditer(text):
        try:
            out.append(dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3))))
        except ValueError:
            pass
    return out


def masked(lines):
    """True for each line inside a code fence or an HTML comment (those are never parsed)."""
    out = []
    fence = False
    comment = False
    for line in lines:
        s = bare(line)
        if fence:
            out.append(True)
            if FENCE_RE.match(s):
                fence = False
            continue
        if comment:
            out.append(True)
            if "-->" in s:
                comment = False
            continue
        if FENCE_RE.match(s):
            out.append(True)
            fence = True
            continue
        if "<!--" in s:
            out.append(True)
            if "-->" not in s[s.index("<!--") + 4:]:
                comment = True
            continue
        out.append(False)
    return out


def heading_of(line):
    m = HEADING_RE.match(bare(line))
    if not m:
        return None
    return len(m.group(1)), m.group(2).strip()


def obsidian_norm(s):
    s = re.sub(r"[!\"#$%&()*+,.:;<=>?@^`{|}~/\[\]\\\r\n]", " ", s)
    return re.sub(r"\s+", " ", s).strip().lower()


def slug(text):
    s = nfc(text).lower()
    s = re.sub(r"[^\w]+", "-", s, flags=re.U).strip("-")
    return s or "topic"


def is_rule_like(text):
    """True when a line states a rule or an everyday default."""
    t = text
    if RULE_WORDS.search(t) or RULE_SYMBOLS.search(t) or DEFAULT_WORDS.search(t):
        return True
    if CAPS_WORD.search(re.sub(r"\([^)]*\)", "", t)):
        return True
    m = re.match(r"^\s*[-*+]\s+\[([^\]]*)\]", t)
    title = m.group(1) if m else t
    if SETTING_TITLE.match(title):
        return True  # "Timezone is Eastern", "Dates as day month year": a title that states a setting
    first = re.findall(r"[A-Za-z']+", title)
    if first and first[0].lower() in IMPERATIVES:
        return True
    after = t.split("):", 1)[1] if "):" in t else ""
    first2 = re.findall(r"[A-Za-z']+", after)
    if first2 and first2[0].lower() in IMPERATIVES:
        return True
    return False


# ---------------------------------------------------------------- the vault

def find_vault(arg):
    root = os.path.abspath(arg or os.getcwd())
    if not os.path.isfile(os.path.join(root, "CLAUDE.md")):
        raise SystemExit("This does not look like a vault: there is no CLAUDE.md in " + root
                         + ". Run this from the vault folder, or pass --vault <folder>.")
    return root


def walk_files(root, skip_top=()):
    """Every file under root (relative paths, sorted), never inside .git and the like."""
    out = []
    for dp, dns, fns in os.walk(root):
        rd = rel_of(root, dp)
        if rd == ".":
            dns[:] = [d for d in dns if d not in SKIP_WALK and d not in skip_top]
        else:
            dns[:] = [d for d in dns if d not in SKIP_WALK]
        for f in fns:
            out.append(f if rd == "." else rd + "/" + f)
    return sorted(out)


def notes(root, include_history=False):
    """Every .md note that is live work: not archives, outputs, .claude or other dot folders."""
    out = []
    for rel in walk_files(root):
        if not rel.endswith(".md"):
            continue
        top = rel.split("/", 1)[0]
        if top.startswith(".") or top in ("archives", "outputs"):
            continue
        if top == HISTORY and not include_history:
            continue
        out.append(rel)
    return out


def git_ok():
    """A git that runs without popping up an install window on a Mac."""
    g = shutil.which("git")
    if not g:
        return None
    if sys.platform == "darwin" and os.path.realpath(g).startswith("/usr/bin/"):
        try:
            r = subprocess.run(["xcode-select", "-p"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
            if r.returncode != 0:
                return None
        except Exception:
            return None
    return g


def git(root, *args, timeout=60):
    g = git_ok()
    if not g:
        return None
    try:
        return subprocess.run([g, "-C", root] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=timeout)
    except Exception:
        return None


def is_git_root(root):
    r = git(root, "rev-parse", "--show-toplevel")
    if r is None or r.returncode != 0:
        return False
    top = r.stdout.decode("utf-8", "replace").strip()
    return bool(top) and os.path.realpath(top) == os.path.realpath(root)


def load_json(path, default):
    t = read_text(path)
    if t is None:
        return default
    try:
        return json.loads(t)
    except ValueError:
        return default


def load_keep(root):
    data = load_json(os.path.join(root, KEEP_REL), {})
    return data if isinstance(data, dict) else {}


def keep_titles(root, kind):
    out = []
    for item in load_keep(root).get(kind, []) or []:
        if isinstance(item, dict) and item.get("title"):
            out.append(str(item["title"]))
        elif isinstance(item, str):
            out.append(item)
    return out


def title_key(t):
    return re.sub(r"[^\w]+", "", nfc(t).lower(), flags=re.U)


DATE_PREFIX_RE = re.compile(r"^\W*20\d\d-\d\d-\d\d(?:[ T]\d\d:\d\d)?\W*")


def is_kept(title, keeps):
    """True when a keep answer matches the start of the title, with or without its date."""
    k = title_key(title)
    k2 = title_key(DATE_PREFIX_RE.sub("", title))
    for x in keeps:
        x = title_key(x)
        if x and (k.startswith(x) or k2.startswith(x)):
            return True
    return False


# ---------------------------------------------------------------- safe writes

def backup_name(rel):
    """Where a file's copy goes inside the run folder. Rule files are renamed so
    Claude Code never reads a second set of rules from the backup."""
    parts = rel.split("/")
    out = []
    for p in parts:
        if p == ".claude":
            p = "dot-claude"
        elif p == "CLAUDE.md":
            p = "CLAUDE.old.md"
        elif p == "CLAUDE.local.md":
            p = "CLAUDE.local.old.md"
        out.append(p)
    return "/".join(out)


class Run(object):
    """One optimize run: a dated folder in archives/ that keeps a copy of every
    file before it changes, plus a list of what changed (manifest.json)."""

    def __init__(self, root, run_dir=None, now=None):
        self.root = root
        self.now = now or dt.datetime.now()
        if run_dir:
            rd = run_dir if os.path.isabs(run_dir) else os.path.join(root, run_dir)
        else:
            rd = os.path.join(root, "archives", "optimize-" + now_stamp(self.now))
        self.dir = os.path.abspath(rd)
        arch = os.path.join(os.path.abspath(root), "archives")
        if not (self.dir + os.sep).startswith(arch + os.sep):
            raise SystemExit("The run folder must be inside the vault's archives/ folder.")
        if os.path.islink(arch) or not (os.path.realpath(self.dir) + os.sep).startswith(
                os.path.join(os.path.realpath(root), "archives") + os.sep):
            raise SystemExit("The vault's archives/ folder is a link to somewhere else, so this run stops here. "
                             "Copies of changed files must stay inside the vault.")
        self.rel = rel_of(root, self.dir)

    def manifest_path(self):
        return os.path.join(self.dir, "manifest.json")

    def manifest(self):
        data = load_json(self.manifest_path(), {})
        if not isinstance(data, dict):
            data = {}
        data.setdefault("files", {})
        data.setdefault("steps", [])
        return data

    def save_manifest(self, data):
        os.makedirs(self.dir, exist_ok=True)
        atomic_write(self.manifest_path(), json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n")

    def backup(self, rel):
        """Copy the file into the run folder once (the first copy is the original)."""
        src = os.path.join(self.root, rel)
        data = self.manifest()
        entry = data["files"].get(rel)
        if entry is not None:
            return
        if os.path.isfile(src):
            dst = os.path.join(self.dir, "backup", backup_name(rel))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            data["files"][rel] = {"existed": True, "backup": rel_of(self.root, dst), "sha256": sha_file(src)}
        else:
            data["files"][rel] = {"existed": False}
        self.save_manifest(data)

    def note(self, step, info):
        data = self.manifest()
        info = dict(info)
        info["step"] = step
        info["at"] = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data["steps"].append(info)
        self.save_manifest(data)

    def write(self, rel, text, expect=None):
        """Back up, then write through a temp file and os.replace. expect: the bytes
        the file must still hold (another tab may have changed it); None skips the check.
        Raises Refused (with a plain reason) for a file write_problem() turns down."""
        path = os.path.join(self.root, rel)
        why = write_problem(self.root, rel)
        if why:
            raise Refused(why)
        if expect is not None and read_bytes(path) != expect:
            raise ChangedUnderUs(rel)
        self.backup(rel)
        atomic_write(path, text)

    def restore(self, rel):
        """Put one file back the way it was before this run wrote it. True when that
        worked. Never raises, because it runs while another error is being handled."""
        try:
            info = self.manifest()["files"].get(rel) or {}
            path = os.path.join(self.root, rel)
            if info.get("existed") and info.get("backup"):
                b = read_bytes(os.path.join(self.root, info["backup"]))
                if b is None:
                    return False
                if read_bytes(path) != b:
                    atomic_write(path, b)
            elif info.get("existed") is False and os.path.isfile(path) and not os.path.islink(path):
                os.remove(path)  # this run made the file, so taking it away loses nothing
            return True
        except Exception:
            return False

    def undo(self, rels):
        """Restore every file in rels. Returns the ones that could not be put back."""
        return [r for r in rels if not self.restore(r)]


def failure_line(err, rel):
    """One plain sentence about why writing rel stopped."""
    if isinstance(err, ChangedUnderUs):
        return "%s changed while this ran (another session?)." % rel
    if isinstance(err, Refused):
        return err.args[0] if err.args else "%s was left as is." % rel
    what = getattr(err, "strerror", None) or err.__class__.__name__
    return "%s could not be written (%s)." % (rel, what)


class ChangedUnderUs(Exception):
    pass


class Refused(Exception):
    """A file this run will not write. args[0] is a plain sentence for the owner."""
    pass


def write_problem(root, rel):
    """Why this file must not be written, in one plain sentence, or None when it is safe.
    Refuses: a path that leaves the vault, a link (to a file or through a folder), a file that is
    not saved as UTF-8 text (it would be changed without anyone noticing), and a read-only file."""
    root_real = os.path.realpath(root)
    path = os.path.join(root, rel)
    parts = rel.replace(os.sep, "/").split("/")
    cur = root
    for p in parts:
        cur = os.path.join(cur, p)
        if os.path.islink(cur):
            return ("%s is a link to somewhere else (or sits inside a linked folder), so it was left as is." % rel)
        if not os.path.lexists(cur):
            break
    real = os.path.realpath(path)
    if not (real + os.sep).startswith(root_real + os.sep):
        return "%s is outside the vault, so it was left as is." % rel
    if os.path.isfile(path):
        b = read_bytes(path)
        if b is None:
            return "%s could not be read (no permission?), so it was left as is." % rel
        if not is_utf8(b):
            return "%s is not saved as UTF-8 text, so it was left as is." % rel
        if not os.access(path, os.W_OK):
            return "%s is set to read-only, so it was left as is." % rel
    folder = os.path.dirname(path)
    while folder and not os.path.isdir(folder):
        folder = os.path.dirname(folder)
    if folder and not os.access(folder, os.W_OK):
        return "The folder that holds %s is set to read-only, so it was left as is." % rel
    return None


def atomic_write(path, text):
    d = os.path.dirname(path) or "."
    os.makedirs(d, exist_ok=True)
    data = text.encode("utf-8") if isinstance(text, str) else text
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".optimize-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        try:
            os.chmod(tmp, os.stat(path).st_mode & 0o7777)
        except OSError:
            os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


# ---------------------------------------------------------------- skills

def skill_dirs(root):
    sk = os.path.join(root, ".claude", "skills")
    try:
        names = sorted(os.listdir(sk))
    except OSError:
        return []
    return [n for n in names if os.path.isfile(os.path.join(sk, n, "SKILL.md"))]


def frontmatter_span(lines):
    """(start, end) line indexes of the frontmatter body, or None."""
    if not lines or bare(lines[0]).strip() != "---":
        return None
    for i in range(1, min(len(lines), 200)):
        if bare(lines[i]).strip() == "---":
            return 1, i
    return None


def description_of(text):
    """(description text, first line index, last line index + 1, name) or (None, ...)."""
    lines = split_keep(text)
    span = frontmatter_span(lines)
    if not span:
        return None, None, None, None
    a, b = span
    name = None
    for i in range(a, b):
        m = re.match(r"^name:\s*(.*)$", bare(lines[i]))
        if m:
            name = m.group(1).strip()
    for i in range(a, b):
        m = re.match(r"^description:\s*(.*)$", bare(lines[i]))
        if not m:
            continue
        val = m.group(1)
        j = i + 1
        if val.strip() in ("|", ">", "|-", ">-", "|+", ">+"):
            parts = []
            while j < b and (bare(lines[j]).startswith((" ", "\t")) or not bare(lines[j]).strip()):
                parts.append(bare(lines[j]).strip())
                j += 1
            joiner = "\n" if val.strip().startswith("|") else " "
            return joiner.join(p for p in parts if p).strip(), i, j, name
        while j < b and bare(lines[j]).startswith((" ", "\t")):
            val += " " + bare(lines[j]).strip()
            j += 1
        v = val.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1].replace('\\"', '"') if v[0] == '"' else v[1:-1].replace("''", "'")
        return v, i, j, name
    return None, None, None, name


def trigger_phrases(desc):
    return re.findall(r'"([^"]{2,120})"', (desc or "").replace('\\"', '"'))


# ---------------------------------------------------------------- output

def emit(args, data, plain_lines):
    if getattr(args, "json", False):
        print(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False))
    else:
        print("\n".join(plain_lines))


def temp_dir_for(root):
    """A folder in this computer's temp space for this vault (never inside or beside it)."""
    key = hashlib.sha256(os.path.realpath(root).encode("utf-8")).hexdigest()[:12]
    d = os.path.join(tempfile.gettempdir(), "optimize-vault-" + key)
    os.makedirs(d, exist_ok=True)
    return d


def template_facts():
    here = os.path.dirname(os.path.abspath(__file__))
    return load_json(os.path.join(os.path.dirname(here), "template-facts.json"), {})
