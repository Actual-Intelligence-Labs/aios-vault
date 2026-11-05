"""Helper cost check: runs before a helper agent uses Bash or Read.

WHAT IT DOES
  Helper agents (the ones a lead session or a workflow starts) waste the most
  tokens in three ways. This check catches each one and sends the step back
  once, with the cheaper way to do it:
    1. A single wait longer than 4 minutes (a Bash timeout over 270 seconds
       that is not in the background, or a sleep over 240 seconds). A wait
       past 5 minutes makes Claude re-read the helper's whole conversation
       at full price.
    2. Reading a whole text file over 20 KB (with Read and no line limit, or
       a limit over 500 lines), or printing one with cat, head, tail or sed.
       Whatever a helper reads rides along in every later step.
       Not counted: SKILL.md, CLAUDE.md, MEMORY.md, AGENTS.md and anything
       under .claude/skills or .claude/agents.
    3. Reading an image over 1600 pixels on its long side.
  The same request sent again, unchanged, passes, so a helper that truly needs
  it pays one extra step and never gets stuck.

  It only ever looks at helper agents. The owner's own chat is never checked.

SAFETY
  It never blocks for good, never changes anything, and logs nothing. It
  remembers only short fingerprints of the requests it sent back, in the
  computer's temp folder, so the second try passes.
  On any error it prints nothing and gets out of the way.
  Runs on Python 3.9 or newer, standard library only, through run.sh.
"""

import glob
import hashlib
import json
import os
import re
import shlex
import struct
import sys
import tempfile

MAX_BASH_MS = 270000
MAX_SLEEP_S = 240
MAX_IMG_EDGE = 1600
MAX_TEXT_BYTES = 20000
MAX_LIMIT_LINES = 500
IMG = re.compile(r"\.(png|jpe?g|webp|gif)$", re.I)
SKIP_TEXT = re.compile(r"\.(pdf|ipynb|png|jpe?g|webp|gif|bmp|tiff?|heic)$", re.I)
EXEMPT = re.compile(r"(^|[/\\])(SKILL|CLAUDE|MEMORY|AGENTS)\.md$|[/\\]\.claude[/\\](skills|agents)[/\\]", re.I)
SLEEP = re.compile(r"\bsleep\s+(\d+(?:\.\d+)?)\s*([smh]?)\b")
PRINT_CMDS = ("cat", "head", "tail", "sed")
PUNCT = ";&|()<>\n"
OPS = re.compile(r"\|\||&&|;;|\|&|&>>|&>|>>|>&|>\||<<<|<<|<&|<>|<\(|>\(|[;&|()<>\n]")
HEREDOC = re.compile(r"(?<!<)<<-?(?!<)\s*(['\"]?)([A-Za-z_][\w.-]*)\1")
PREFIX = re.compile(r"^[A-Za-z_]\w*=")
SED_RANGE = re.compile(r"^(\d+|\$)(?:,(\d+|\$))?p$")
SED_QUIT = re.compile(r"^(\d+)q$")
HUGE = 50000000
try:  # Claude Code keeps about this many characters of one command's output
    BASH_OUT_CAP = max(1000, int(os.environ.get("BASH_MAX_OUTPUT_LENGTH") or 30000))
except ValueError:
    BASH_OUT_CAP = 30000

WAIT_REASON = (
    "Cheaper way first: never let one step wait longer than 4 minutes. A wait past 5 minutes makes Claude "
    "re-read your whole conversation at full price. Start long jobs (tests, builds, renders) with the Bash "
    "tool's run_in_background option, writing a log (COMMAND > LOG 2>&1). Claude Code stops that job when the "
    "session ends; never use nohup, setsid or disown, because nothing may outlive the session. Then wait in "
    "slices with a timeout of "
    "250000 or less, for example: for i in $(seq 1 24); do grep -q DONE LOG && break; sleep 10; done; tail -5 LOG. "
    "Repeat the slice until the job is done. If this exact command truly has to wait, send it again unchanged and "
    "it will pass.")


def is_helper(data):
    """A helper agent carries agent_id, or writes its transcript under a subagents folder.
    agent_type alone is not a helper: a main chat started with --agent has it too."""
    tp = str(data.get("transcript_path") or "").replace("\\", "/")
    return bool(data.get("agent_id") or "/subagents/" in tp)


def state_dir():
    base = os.environ.get("VAULT_HOOKS_TEMP") or os.path.join(tempfile.gettempdir(), "aios-vault-hooks")
    return os.path.join(base, "helper-cost-check")


def seen_before(data, key):
    """True when this helper was already sent back for this exact request; otherwise remember it."""
    who = hashlib.sha256(("%s|%s" % (data.get("session_id"), data.get("agent_id"))).encode()).hexdigest()[:24]
    mark = hashlib.sha256(key.encode("utf-8", "replace")).hexdigest()[:24]
    folder = state_dir()
    os.makedirs(folder, mode=0o700, exist_ok=True)
    path = os.path.join(folder, who)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            if mark in fh.read().split():
                return True
    except OSError:
        pass
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(mark + "\n")
    return False


def image_size(path):
    """(width, height) from the file header for PNG, GIF, WebP and JPEG, else None."""
    with open(path, "rb") as f:
        head = f.read(32)
        if head[:8] == b"\x89PNG\r\n\x1a\n":
            return struct.unpack(">II", head[16:24])
        if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
            f.seek(12)
            chunk = f.read(30)
            kind = chunk[:4]
            if kind == b"VP8X":
                return (1 + int.from_bytes(chunk[12:15], "little"), 1 + int.from_bytes(chunk[15:18], "little"))
            if kind == b"VP8 ":
                w, h = struct.unpack("<HH", chunk[14:18])
                return w & 0x3FFF, h & 0x3FFF
            if kind == b"VP8L":
                v = int.from_bytes(chunk[9:13], "little")
                return (v & 0x3FFF) + 1, ((v >> 14) & 0x3FFF) + 1
            return None
        if head[:6] in (b"GIF87a", b"GIF89a"):
            return struct.unpack("<HH", head[6:10])
        if head[:2] == b"\xff\xd8":
            f.seek(2)
            for _ in range(10000):
                b = f.read(1)
                while b and b != b"\xff":
                    b = f.read(1)
                while b == b"\xff":
                    b = f.read(1)
                if not b:
                    return None
                m = b[0]
                if m in (0xD8, 0x01) or 0xD0 <= m <= 0xD7:
                    continue
                ln = struct.unpack(">H", f.read(2))[0]
                if m in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                    f.read(1)
                    h, w = struct.unpack(">HH", f.read(4))
                    return w, h
                f.seek(ln - 2, 1)
    return None


def deny(reason):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": reason}}))


def strip_heredocs(cmd):
    """Drop here-document bodies: their text is data, not commands."""
    out, pending = [], []
    for line in cmd.split("\n"):
        if pending:
            if line.strip() == pending[0]:
                pending.pop(0)
            continue
        out.append(line)
        pending.extend(m.group(2) for m in HEREDOC.finditer(line))
    return "\n".join(out)


def simple_commands(cmd):
    """Best-effort split of a shell command into (argv, output_shown) per simple command. Quotes are respected.
    Output is not shown when piped on, sent to a file, or captured by $( ) or <( )."""
    lex = shlex.shlex(strip_heredocs(cmd).replace("\\\n", " "), posix=True, punctuation_chars=PUNCT)
    lex.whitespace = " \t\r"
    lex.whitespace_split = True
    lex.commenters = ""
    out, stack = [], []
    cur = {"argv": [], "shown": True, "capture": False}
    skip = None   # "drop": skip the next word; "file": the next word is an input file
    comment = False

    def flush(piped):
        if cur["argv"] and not cur["capture"] and not any(s["capture"] for s in stack):
            out.append((cur["argv"], cur["shown"] and not piped))
        cur["argv"], cur["shown"] = [], True

    for tok in lex:
        punct = bool(tok) and all(c in PUNCT for c in tok)
        if comment:
            if not (punct and "\n" in tok):
                continue
            comment = False
        if not punct:
            if skip == "drop":
                skip = None
                continue
            if skip is None and tok.startswith("#"):
                comment = True
                continue
            skip = None
            cur["argv"].append(tok)
            continue
        for op in OPS.findall(tok):
            argv = cur["argv"]
            if op in ("|", "|&"):
                flush(True)
            elif op in (";", "\n", "&&", "||", "&", ";;"):
                flush(False)
            elif op in ("(", "<(", ">("):
                capture = op != "(" or bool(argv and argv[-1].endswith("$"))
                if op == "(" and capture:
                    argv[-1] = argv[-1][:-1]
                    if not argv[-1]:
                        argv.pop()
                stack.append(dict(cur))
                cur = {"argv": [], "shown": True, "capture": capture}
            elif op == ")":
                flush(False)
                if stack:
                    cur = stack.pop()
            elif op in (">", ">>", ">|", "&>", "&>>"):
                if op in (">", ">>") and argv and argv[-1] == "2":
                    argv.pop()   # 2> FILE: only errors go to the file
                else:
                    if argv and argv[-1] == "1":
                        argv.pop()
                    cur["shown"] = False
                skip = "drop"
            elif op == ">&":
                if argv and argv[-1] == "2":
                    argv.pop()   # 2>&1
                skip = "drop"
            elif op == "<":
                skip = "file"
            else:   # << <<< <& <>
                skip = "drop"
    flush(False)
    while stack:
        cur = stack.pop()
        flush(False)
    return out


def resolve(tok, base):
    tok = os.path.expandvars(os.path.expanduser(tok))
    if "$" in tok or not tok:
        return []
    if not os.path.isabs(tok):
        if not base:
            return []
        tok = os.path.join(base, tok)
    paths = sorted(glob.glob(tok))[:200] if any(c in tok for c in "*?[") else [tok]
    return [p for p in paths if os.path.isfile(p) and not EXEMPT.search(p) and not SKIP_TEXT.search(p)]


def scan_range(path, first=1, last=None):
    """(bytes, lines) printed for lines first..last (1-based; last None means to the end)."""
    size = os.path.getsize(path)
    if size > HUGE:
        n = (last - first + 1) if last else MAX_LIMIT_LINES + 1
        return (size if n > MAX_LIMIT_LINES else 0), n
    b = ln = 0
    with open(path, "rb") as f:
        for i, line in enumerate(f, 1):
            if i < first:
                continue
            if last is not None and i > last:
                break
            b += len(line)
            ln += 1
            if b > MAX_TEXT_BYTES and ln > MAX_LIMIT_LINES:
                break
    return b, ln


def scan_tail(path, n):
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        f.seek(max(0, size - 2000000))
        lines = f.read().splitlines(True)
    lines = lines[-n:] if n > 0 else []
    return sum(len(x) for x in lines), len(lines)


def too_much(b, ln):
    return b > MAX_TEXT_BYTES and ln > MAX_LIMIT_LINES


def count_args(args, is_tail):
    """head and tail options: (mode, n, from_start, files), or None to leave the command alone."""
    mode, n, plus, files, i = "n", 10, False, [], 0
    while i < len(args):
        a = args[i]
        m = re.match(r"^-([nc])?(\+?\d+)$", a) or re.match(r"^--(lines|bytes)=(\+?\d+)$", a)
        if a == "--":
            files += args[i + 1:]
            break
        if a in ("-n", "-c", "--lines", "--bytes") and i + 1 < len(args) and re.match(r"^\+?\d+$", args[i + 1]):
            mode, val = a.lstrip("-")[0], args[i + 1]
            i += 1
        elif m:
            mode, val = (m.group(1) or "n")[0], m.group(2)
        elif is_tail and re.match(r"^\+\d+$", a):
            mode, val = "n", a
        elif a in ("-f", "-F", "--follow") or a.startswith("--follow="):
            return None   # following a log is a wait, not a print
        elif a.startswith("-") and len(a) > 1:
            i += 1
            continue
        else:
            files.append(a)
            i += 1
            continue
        plus, n = val.startswith("+"), int(val.lstrip("+"))
        i += 1
    return mode, n, plus, files


def printer_issue(name, args, base):
    """(path, printed_bytes, whole_file) for the first print over the limit, else None."""
    if name == "cat":
        paths = [p for a in args if not (a.startswith("-") and len(a) > 1) for p in resolve(a, base)]
        total = sum(os.path.getsize(p) for p in paths)
        if total > MAX_TEXT_BYTES:
            big = max(paths, key=os.path.getsize)
            return big, total, True if len(paths) == 1 else "files"
        return None
    if name in ("head", "tail"):
        parsed = count_args(args, name == "tail")
        if not parsed:
            return None
        mode, n, plus, files = parsed
        for p in (q for a in files for q in resolve(a, base)):
            size = os.path.getsize(p)
            if size <= MAX_TEXT_BYTES:
                continue
            if mode == "c":
                printed = size - n + 1 if (name == "tail" and plus) else min(n, size)
                if printed > MAX_TEXT_BYTES:
                    return p, printed, printed >= size
                continue
            if name == "head":
                b, ln = scan_range(p, 1, n)
            elif plus:
                b, ln = scan_range(p, max(n, 1), None)
            else:
                b, ln = scan_tail(p, n)
            if too_much(b, ln):
                return p, b, b >= size
        return None
    if name == "sed":
        quiet, scripts, files, i = False, [], [], 0
        while i < len(args):
            a = args[i]
            if a.startswith("-i") or a.startswith("--in-place") or a in ("-f", "--file") or a.startswith("--file="):
                return None   # an in-place edit or a script file: nothing printed we can size
            if a in ("-e", "--expression") or re.match(r"^-[nErsuz]*e$", a):
                quiet = quiet or ("n" in a and not a.startswith("--"))
                if i + 1 < len(args):
                    scripts.append(args[i + 1])
                i += 2
                continue
            if a.startswith("--expression="):
                scripts.append(a.split("=", 1)[1])
            elif a in ("-n", "--quiet", "--silent"):
                quiet = True
            elif re.match(r"^-[nErsuz]+$", a):
                quiet = quiet or "n" in a
            elif a.startswith("-") and len(a) > 1:
                pass
            elif not scripts:
                scripts.append(a)
            else:
                files.append(a)
            i += 1
        scripts = [s.strip() for s in scripts]
        for p in (q for a in files for q in resolve(a, base)):
            size = os.path.getsize(p)
            if size <= MAX_TEXT_BYTES:
                continue
            if quiet:
                b = ln = 0
                for s in scripts:
                    if s == "p":
                        return p, size, True
                    m = SED_RANGE.match(s)
                    if not m:
                        return None   # a pattern or a program: output size unknown, leave it
                    a1, a2 = m.group(1), m.group(2) or m.group(1)
                    if a1 == "$":
                        sb, sl = scan_tail(p, 1)
                    else:
                        sb, sl = scan_range(p, int(a1), None if a2 == "$" else int(a2))
                    b, ln = b + sb, ln + sl
                if too_much(b, ln):
                    return p, b, b >= size
                continue
            if len(scripts) == 1 and SED_QUIT.match(scripts[0]):
                b, ln = scan_range(p, 1, int(SED_QUIT.match(scripts[0]).group(1)))
                if too_much(b, ln):
                    return p, b, b >= size
                continue
            return p, size, True   # sed without -n prints every line
    return None


def bash_print_issue(data, cmd):
    base = str(data.get("cwd") or os.getcwd())
    for argv, shown in simple_commands(cmd):
        i = 0
        while i < len(argv) and (PREFIX.match(argv[i]) or argv[i] in ("time", "command", "builtin", "exec", "nice",
                                                                      "nohup")):
            i += 1
        argv = argv[i:]
        if not argv:
            continue
        name = os.path.basename(argv[0])
        if name == "cd":
            tgt = os.path.expanduser(argv[1]) if len(argv) > 1 and argv[1] != "-" else None
            base = None if not tgt else (tgt if os.path.isabs(tgt) else (os.path.join(base, tgt) if base else None))
            continue
        if shown and name in PRINT_CMDS:
            hit = printer_issue(name, argv[1:], base)
            if hit:
                return hit
    return None


SLEEP_ARG = re.compile(r"^(\d+(?:\.\d+)?)([smhd]?)$")
LEAD_WORDS = {"do", "then", "else", "{", "!", "time", "command", "exec", "nohup", "caffeinate", "nice"}
SLEEP_UNITS = {"": 1, "s": 1, "m": 60, "h": 3600, "d": 86400}


def longest_sleep(cmd, depth=0):
    """The longest sleep this command waits for in the foreground, in seconds. Text inside quotes or a heredoc
    and jobs sent to the background with & never count. Unclear text falls back to a plain search."""
    if depth > 2:
        return 0
    try:
        lex = shlex.shlex(strip_heredocs(cmd).replace("\\\n", " "), posix=True, punctuation_chars=PUNCT)
        lex.whitespace = " \t\r"
        lex.whitespace_split = True
        lex.commenters = ""
        toks = list(lex)
    except ValueError:
        return max([float(n) * SLEEP_UNITS[u] for n, u in SLEEP.findall(cmd)] or [0])
    segs, cur, groups, last_group = [], [], [], None
    for tok in toks:
        if not (tok and all(c in PUNCT for c in tok)):
            cur.append(tok)
            continue
        for op in OPS.findall(tok):
            if op == "&":
                segs.append([cur, True])
                if last_group is not None:
                    for s in segs[last_group:]:
                        s[1] = True     # ( ... ) & sends the whole group to the background
                cur, last_group = [], None
                continue
            last_group = None
            if op in ("(", "<(", ">("):
                segs.append([cur, False])
                cur = []
                groups.append(len(segs))
            elif op == ")":
                segs.append([cur, False])
                cur = []
                last_group = groups.pop() if groups else None
            elif op in (";", "\n", "&&", "||", "|", "|&", ";;"):
                segs.append([cur, False])
                cur = []
    segs.append([cur, False])
    best = 0
    for argv, background in segs:
        if background or not argv:
            continue
        i = 0
        while i < len(argv) and (argv[i] in LEAD_WORDS or PREFIX.match(argv[i])):
            i += 1
        if i < len(argv) and argv[i] == "timeout":
            i += 2
        argv = argv[i:]
        if not argv:
            continue
        name = os.path.basename(argv[0])
        if name == "sleep":
            total = 0.0
            for a in argv[1:]:
                m = SLEEP_ARG.match(a)
                if m:
                    total += float(m.group(1)) * SLEEP_UNITS[m.group(2)]
            best = max(best, total)
        elif name in ("sh", "bash", "zsh", "dash") and "-c" in argv[1:]:
            k = argv.index("-c")
            if k + 1 < len(argv):
                best = max(best, longest_sleep(argv[k + 1], depth + 1))
    return best


def check_bash(data, ti):
    if ti.get("run_in_background"):
        return
    cmd = str(ti.get("command") or "")
    t = ti.get("timeout")
    long_wait = isinstance(t, (int, float)) and not isinstance(t, bool) and t > MAX_BASH_MS
    long_sleep = longest_sleep(cmd) > MAX_SLEEP_S
    if long_wait or long_sleep:
        if not seen_before(data, "bash|%s|%s" % (t, cmd)):
            deny(WAIT_REASON)
        return
    hit = bash_print_issue(data, cmd)
    if not hit or seen_before(data, "print|" + cmd):
        return
    path, printed, kind = hit
    name, kb = os.path.basename(path), printed // 1000
    if kind == "files":
        what = "%d KB from several files (%s is the biggest)" % (kb, name)
    elif kind:
        what = "all of %s (%d KB)" % (name, kb)
    else:
        what = "over %d lines and %d+ KB of %s" % (MAX_LIMIT_LINES, kb, name)
    tokens = int(round(min(printed, BASH_OUT_CAP) / 4.0))
    deny("Cheaper way first: this command prints %s. Up to about %s tokens of it would reach you and ride along in "
         "every later step. Find what you need first (grep -n PATTERN FILE), then print a slice of %d lines or less "
         "(sed -n 'START,ENDp' FILE) or use Read with an offset and a limit. For long command output, pipe it "
         "through tail or grep. If you truly need all of it, send the same command again unchanged and it will "
         "pass." % (what, "{:,}".format(tokens), MAX_LIMIT_LINES))


def check_read(data, ti):
    path = os.path.expanduser(str(ti.get("file_path") or ""))
    if not path or not os.path.isfile(path):
        return
    if IMG.search(path):
        try:
            wh = image_size(path)
        except Exception:
            wh = None
        if not wh or max(wh) <= MAX_IMG_EDGE:
            return
        if seen_before(data, "img|" + path):
            return
        deny("Cheaper way first: this image is %dx%d pixels. Look at a smaller copy, about 1280 pixels on the long "
             "side, or one sheet of small previews (on a Mac: sips -Z 1280 IMAGE --out SCRATCH/small.png). Open the "
             "full size only as a crop of one named detail, and check colors and pixel sizes with a script, never by "
             "eye. If you truly need this full image, ask for it again and it will pass." % (wh[0], wh[1]))
        return
    if SKIP_TEXT.search(path) or EXEMPT.search(path):
        return
    size = os.path.getsize(path)
    limit = ti.get("limit")
    if size <= MAX_TEXT_BYTES or (isinstance(limit, int) and not isinstance(limit, bool)
                                  and limit <= MAX_LIMIT_LINES):
        return
    if seen_before(data, "read|%s|%s|%s" % (path, ti.get("offset"), limit)):
        return
    deny("Cheaper way first: this file is %d KB (about %s tokens) and would ride along in every later step. Find "
         "what you need first (grep -n PATTERN FILE), then use Read with an offset and a limit of %d lines or less. "
         "If you truly need the whole file, ask for it again unchanged and it will pass."
         % (size // 1000, "{:,}".format(size // 4), MAX_LIMIT_LINES))


def main():
    data = json.load(sys.stdin)
    if not isinstance(data, dict) or not is_helper(data):
        return
    ti = data.get("tool_input") or {}
    if not isinstance(ti, dict):
        return
    tool = data.get("tool_name")
    if tool == "Bash":
        check_bash(data, ti)
    elif tool == "Read":
        check_read(data, ti)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
