"""Secrets and money lock: runs before Claude uses a tool.

WHAT IT DOES
  1. Stored secrets stay unseen. Claude may USE a password, key or token
     inside a script, but it never reads or prints one. This blocks the
     usual ways a secret ends up in the chat:
       - asking the computer's password store for a password (on a Mac:
         "security find-generic-password" or "find-internet-password" with
         -w or -g, and "security dump-keychain"; on Linux: "secret-tool
         lookup"), and command-line tools that print a sign-in token
         (for example "gh auth token" or "gcloud auth print-access-token")
       - printing a key file: .env files, *.pem, *.key, id_rsa and other
         private keys, credentials.json, token files, .netrc and similar,
         with cat, head, grep, sed and the like, or with the Read tool
       - printing a variable named like a secret (KEY, TOKEN, SECRET,
         PASSWORD), or a variable filled from the password store earlier in
         the same command, or printing every variable at once (env,
         printenv, set)
       - the same things done inside a small script (python -c, node -e,
         perl -ne, osascript -e, or a script fed in with <<EOF)
       - a folder search (grep -r, rg) that would also read a key file; it
         says how to leave that file out
     A $NAME inside single quotes is plain text, so it never counts.
     The block message tells Claude how to do the job without seeing the
     value: test that a key is set, or run the script that uses it.
  2. Money needs a yes. Before any tool whose name says it pays, charges,
     refunds, buys, orders, reimburses or sends money (or creates a bill or
     invoice on a payment, accounting or spend service), Claude Code asks the
     owner first. It looks at connector tool names only, not shell commands.

  Normal work passes: git, python, ls, codesign, "security find-identity",
  reading README.env.md or .env.example, loading a .env file into a script
  (source .env), and using a key in a command (curl with "$API_KEY").
  A search pattern is never taken for a file: grep -n "\\.env" .gitignore
  reads only .gitignore, so it passes (the same for the script of sed and
  awk, the filter of jq, and git grep or git log --grep).

SAFETY
  This is a seatbelt for honest mistakes, not a wall against a determined
  attacker. It changes nothing, stores nothing and logs nothing.
  On any error it prints nothing and gets out of the way.
  Runs on Python 3.9 or newer, standard library only, through run.sh.
"""

import glob
import json
import os
import re
import shlex
import sys

SECRET_REASON = (
    "Blocked: this would show a stored secret (a password, key or token) in the chat, and Claude never sees "
    "one. Claude may use a secret inside a script or command without printing it. To check that a key is set: "
    "test -n \"$NAME\" && echo set. To check that a key works: run the script or command that uses it and look "
    "at its result, not at the key. To check that a .env file has a name in it: grep -q NAME= .env && echo found. "
    "If the owner needs to see the value, they open it themselves.")
MONEY_REASON = (
    "This step looks like it moves money (it pays, charges, refunds, buys or sends money). Say yes only if you "
    "asked for this exact payment.")

# ---------------------------------------------------------------- secret files
SECRET_FILE = re.compile(
    r"""(?ix)^(?:
        \.env | \.env\..+ | .+\.env | \.envrc
      | .+\.(?:pem|key|p12|pfx|keystore|jks|ppk|keychain|keychain-db)
      | id_(?:rsa|dsa|ecdsa|ed25519)(?:_sk)?
      | client_secret.*\.json | .*credentials.*\.json | .*service[-_]account.*\.json
      | token\.json | .+\.token
      | \.netrc | _netrc | \.pgpass | \.git-credentials | \.pypirc | \.npmrc | \.yarnrc\.yml
      | secrets?\.(?:json|ya?ml|toml|ini|env|txt)
    )$""")
# Names that hold secrets even though their ending looks harmless (checked before SAFE_SUFFIX).
EXPLICIT_SECRET = re.compile(r"(?i)^(?:secrets?\.(?:json|ya?ml|toml|ini|env|txt)|.+\.env\.txt)$")
# Example and template files hold placeholders, not real secrets.
SAFE_SUFFIX = re.compile(r"(?i)\.(?:example|sample|template|dist|defaults?|schema|md|txt|pub)$")
SECRET_PATH = re.compile(r"(?i)(?:^|/)(?:\.aws/credentials|\.config/gh/hosts\.ya?ml|\.docker/config\.json"
                         r"|library/keychains/|proc/[^/]+/environ$)")


def secret_file(path):
    p = str(path).replace("\\", "/")
    if SECRET_PATH.search(p):
        return True
    name = p.rstrip("/").rsplit("/", 1)[-1]
    if not name or name.startswith("$"):
        return False
    if EXPLICIT_SECRET.match(name):
        return True
    if SAFE_SUFFIX.search(name):
        return False
    return bool(SECRET_FILE.match(name))


FILTER_OPTS = {"--exclude", "--include", "--exclude-dir", "--include-dir", "-g", "--glob", "--iglob", "--ignore",
               "--ignore-file"}


def secret_args(args, cwd):
    """True when one of these command words names a secret file (globs are expanded in cwd)."""
    prev = ""
    for a in args:
        before, prev = prev, a
        if not a or a == "-" or before in FILTER_OPTS:
            continue     # the value of --exclude=.env or -g '!.env' leaves a file out, it does not read it
        if a.startswith("--") and "=" in a:
            if a.split("=", 1)[0] in FILTER_OPTS:
                continue
            a = a.split("=", 1)[1]
        elif a.startswith("-"):
            continue
        a = a.lstrip("@")
        if any(c in a for c in "*?["):
            pattern = os.path.expanduser(a)
            if not os.path.isabs(pattern) and cwd:
                pattern = os.path.join(cwd, pattern)
            if any(secret_file(p) for p in sorted(glob.glob(pattern))[:200]):
                return True
            continue
        if secret_file(a):
            return True
    return False


# ---------------------------------------------------------------- secret variables
UPPER_SECRET = re.compile(r"(?:^|_)(?:API_?KEY|ACCESS_?KEY|SECRET(?:_?KEY)?|PRIVATE_?KEY|TOKEN|PASSWORD|PASSWD|"
                          r"PASSPHRASE|CREDENTIALS?|KEY|PAT)(?:_|$)")
LOWER_SECRET = re.compile(r"(?i)api_?key|secret|private_?key|access_?key|password|passwd|passphrase|"
                          r"(?:auth|access|refresh|bearer|api)_?token|credential")
VAR_USE = re.compile(r"\$\{([#!]?)([A-Za-z_][A-Za-z0-9_]*)([^}]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)")


def secret_name(name):
    if name in ("PWD", "OLDPWD"):
        return False
    if name.upper() == name:
        return bool(UPPER_SECRET.search(name))
    return bool(LOWER_SECRET.search(name))


def prints_secret_var(text, tainted=()):
    """True when this word expands a variable named like a secret (or one filled from a password store
    earlier in the same command) to its value. A $ inside single quotes was masked earlier and never counts."""
    for m in VAR_USE.finditer(text):
        if m.group(4):
            if secret_name(m.group(4)) or m.group(4) in tainted:
                return True
            continue
        mark, name, rest = m.group(1), m.group(2), m.group(3)
        if mark:              # ${#NAME} is its length, ${!NAME} an indirection: no value shown
            continue
        if rest.startswith((":+", "+", ":?", "?")):
            continue          # ${NAME:+set} shows the word, not the value
        if secret_name(name) or name in tainted:
            return True
    return False


# ---------------------------------------------------------------- shell parsing
PUNCT = ";&|()<>\n"
OPS = re.compile(r"\|\||&&|;;|\|&|&>>|&>|>>|>&|>\||<<<|<<|<&|<>|[;&|()<>\n]")
HEREDOC = re.compile(r"(?<!<)<<-?(?!<)\s*(['\"]?)([A-Za-z_][\w.-]*)\1")
ASSIGN = re.compile(r"^[A-Za-z_]\w*=")
SUBST = re.compile(r"__S(\d+)__")
WRAPPERS = {"sudo", "doas", "command", "builtin", "exec", "nohup", "time", "nice", "caffeinate", "stdbuf",
            "timeout", "xargs"}
VALUE_OPTS = {"sudo": ("-u", "-g", "-h", "-p", "-C", "-D", "-U"), "nice": ("-n",), "doas": ("-u",),
              "timeout": ("-s", "-k", "--signal", "--kill-after"), "xargs": ("-I", "-n", "-L", "-P", "-d", "-E", "-s")}
READERS = {"cat", "head", "tail", "less", "more", "bat", "batcat", "nl", "tac", "rev", "strings", "xxd", "od",
           "hexdump", "base64", "sed", "awk", "gawk", "grep", "egrep", "fgrep", "rg", "ag", "cut", "sort", "uniq",
           "diff", "column", "fold", "pr", "jq", "yq", "plutil", "paste", "fmt", "expand", "openssl"}
QUIET_FLAGS = re.compile(r"^-(?:[a-zA-Z]*[qlLc][a-zA-Z]*)$|^--(?:quiet|silent|files-with-matches|"
                         r"files-without-match|count)$")
PASSTHROUGH = READERS | {"echo", "printf", "tr", "tee", "python", "python3", "node", "ruby", "perl", "pbcopy", "xclip"}
INTERPRETERS = re.compile(r"^(?:python[0-9.]*|node|nodejs|ruby|perl|deno|bun|php)$")
SHELLS = {"sh", "bash", "zsh", "dash", "ksh", "fish"}
PRINT_CALL = re.compile(r"\b(?:print|pprint|puts|console\.log|console\.error|say|echo|printf|p|pp|write|dump|"
                        r"var_dump|print_r)\s*[\(\s]")
ENV_READ = re.compile(r"environ|getenv|process\.env|\bENV\b|\$_ENV|\$ENV")


class Blocked(Exception):
    """Raised when a command would show a secret. args[0], when given, is a more exact reason."""
    pass


SQ_DOLLAR = "\x01"   # stands in for a $ inside single quotes, where the shell never expands it


def mask_single_quoted(cmd):
    """Swap each $ inside single quotes for SQ_DOLLAR, so '$TOKEN' (plain text) is not read as a variable."""
    out, quote, i, n = [], None, 0, len(cmd)
    while i < n:
        c = cmd[i]
        if quote == "'":
            if c == "'":
                quote = None
            out.append(SQ_DOLLAR if c == "$" else c)
            i += 1
            continue
        if c == "\\" and i + 1 < n:
            out.append(cmd[i:i + 2])
            i += 2
            continue
        if c == "'" and quote is None:
            quote = "'"
        elif c == '"':
            quote = None if quote == '"' else '"'
        out.append(c)
        i += 1
    return "".join(out)


def unmask(text):
    return text.replace(SQ_DOLLAR, "$")


def find_substs(cmd):
    """Swap each $( ), <( ), >( ) and backtick block for a __S<n>__ placeholder. Returns (text, inner texts)."""
    out, subs, i, n, quote = [], [], 0, len(cmd), None
    while i < n:
        c = cmd[i]
        if quote == "'":
            out.append(c)
            if c == "'":
                quote = None
            i += 1
            continue
        if c == "\\" and i + 1 < n:
            out.append(cmd[i:i + 2])
            i += 2
            continue
        if c == "'" and quote is None:
            quote = "'"
        elif c == '"':
            quote = None if quote == '"' else '"'
        elif c in "$<>" and cmd[i + 1:i + 2] == "(" and cmd[i + 2:i + 3] != "(":
            depth, j, q = 0, i + 1, None
            while j < n:
                d = cmd[j]
                if q:
                    if d == q:
                        q = None
                    elif d == "\\" and q == '"':
                        j += 1
                elif d in "'\"":
                    q = d
                elif d == "(":
                    depth += 1
                elif d == ")":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            subs.append(cmd[i + 2:j])
            out.append("__S%d__" % (len(subs) - 1))
            i = j + 1
            continue
        elif c == "`":
            j = cmd.find("`", i + 1)
            j = n if j < 0 else j
            subs.append(cmd[i + 1:j])
            out.append("__S%d__" % (len(subs) - 1))
            i = j + 1
            continue
        out.append(c)
        i += 1
    return "".join(out), subs


def strip_heredocs(cmd, bodies=None):
    """The command text without heredoc bodies. When bodies is a list, (start line, body) pairs are added to it."""
    out, pending, cur = [], [], None
    for line in cmd.split("\n"):
        if pending:
            if line.strip() == pending[0][0]:
                tag, start = pending.pop(0)
                if bodies is not None:
                    bodies.append((start, "\n".join(cur)))
                cur = []
            else:
                cur.append(line)
            continue
        out.append(line)
        pending.extend((m.group(2), line) for m in HEREDOC.finditer(line))
        cur = []
    if pending and bodies is not None and cur:
        bodies.append((pending[0][1], "\n".join(cur)))
    return "\n".join(out)


def segments(text):
    """Split shell text into simple commands: dicts with argv, redir (stdout to a file) and pipe (piped on)."""
    lex = shlex.shlex(text.replace("\\\n", " "), posix=True, punctuation_chars=PUNCT)
    lex.whitespace = " \t\r"
    lex.whitespace_split = True
    lex.commenters = ""
    segs, cur, skip, comment = [], {"argv": [], "redir": False, "pipe": False, "stdin": []}, None, False

    def end(pipe):
        if cur["argv"]:
            cur["pipe"] = pipe
            segs.append(dict(cur))
        cur["argv"], cur["redir"], cur["pipe"], cur["stdin"] = [], False, False, []

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
            if skip == "keep":
                cur["stdin"] = cur["stdin"] + [tok]
            skip = None
            cur["argv"].append(tok)
            continue
        for op in OPS.findall(tok):
            argv = cur["argv"]
            if op in ("|", "|&"):
                end(True)
            elif op in (";", "\n", "&&", "||", "&", ";;", "(", ")"):
                end(False)
            elif op in (">", ">>", ">|", "&>", "&>>"):
                if op in (">", ">>") and argv and argv[-1] == "2":
                    argv.pop()
                else:
                    if argv and argv[-1] == "1":
                        argv.pop()
                    cur["redir"] = True
                skip = "drop"
            elif op == ">&":
                if argv and argv[-1] == "2":
                    argv.pop()
                skip = "drop"
            elif op in ("<", "<<<"):
                skip = "keep"      # the next word is read: keep it as an argument
            else:
                skip = "drop"
    end(False)
    return segs


def unwrap(argv):
    """Drop leading NAME=value words and wrappers such as sudo, nohup or timeout 30."""
    i = 0
    while i < len(argv):
        w = argv[i]
        if ASSIGN.match(w):
            i += 1
            continue
        base = os.path.basename(w)
        if base in WRAPPERS:
            i += 1
            while i < len(argv) and argv[i].startswith("-"):
                i += 2 if argv[i] in VALUE_OPTS.get(base, ()) else 1
            if base == "timeout" and i < len(argv):
                i += 1
            continue
        if base == "env":
            j = i + 1
            while j < len(argv) and (argv[j].startswith("-") or ASSIGN.match(argv[j])):
                j += 2 if argv[j] in ("-u", "-C", "-S") else 1
            if j >= len(argv):
                return argv[i:]   # a bare env prints every variable
            i = j
            continue
        break
    return argv[i:]


def secret_source(argv):
    """"always" when this command prints a stored secret wherever its output goes, "shown" when it prints one
    to its output (fine when that output is captured into a variable or piped into a program), else None."""
    name = os.path.basename(argv[0])
    args = argv[1:]
    if name == "security":
        k = 0      # security [-hilqv] [-p prompt] command [options]
        while k < len(args) and args[k].startswith("-"):
            k += 2 if args[k] == "-p" else 1
        args = args[k:]
    sub = args[0] if args else ""
    if name == "security":
        if sub in ("find-generic-password", "find-internet-password"):
            flags = [a for a in args[1:] if re.match(r"^-[A-Za-z]+$", a)]
            if any("g" in f for f in flags):
                return "always"      # -g prints the password to the error output, even when captured
            return "shown" if any("w" in f for f in flags) else None
        if sub == "dump-keychain":
            return "always"
        if sub == "export":
            kinds = [args[k + 1] for k, a in enumerate(args[:-1]) if a == "-t"]
            return "always" if not kinds or any(k not in ("certs", "pubKeys") for k in kinds) else None
        return None
    return "shown" if token_cli(name, args, sub) else None


def token_cli(name, args, sub):
    if name == "secret-tool":
        return sub == "lookup"
    if name == "keyring":
        return sub == "get"
    if INTERPRETERS.match(name) and "-m" in args:
        k = args.index("-m")
        return args[k + 1:k + 3] == ["keyring", "get"]
    if name == "gh":
        return args[:2] == ["auth", "token"] or (args[:2] == ["auth", "status"]
                                                  and ("-t" in args or "--show-token" in args))
    if name == "gcloud":
        return any(a in ("print-access-token", "print-identity-token", "print-refresh-token") for a in args)
    if name == "az":
        return "get-access-token" in args
    if name == "heroku":
        return sub == "auth:token"
    if name == "op":
        return sub == "read" or (args[:2] == ["item", "get"] and "--reveal" in args)
    if name == "pass":
        return sub == "show"
    if name == "git":
        return args[:2] == ["credential", "fill"]
    if name.startswith("docker-credential-"):
        return sub == "get"
    if name == "aws":
        return args[:2] == ["configure", "get"] and any(secret_name(a.upper().replace(".", "_")) for a in args[2:])
    return False


GIT_PRINTERS = ("show", "diff", "cat-file", "log", "grep", "blame")


def env_dump(argv):
    name = os.path.basename(argv[0])
    rest = argv[1:]
    if name in ("env", "printenv") and not rest:
        return True
    if name == "env" and all(a.startswith("-") for a in rest):
        return True
    if name == "printenv":
        return any(secret_name(a) for a in rest if not a.startswith("-"))
    if name == "set" and not rest:
        return True
    if name in ("export", "declare", "typeset") and (not rest or all(re.match(r"^-[px]+$", a) for a in rest)):
        return True
    return False


def code_prints_secret(code):
    if not PRINT_CALL.search(code):
        return False
    if ENV_READ.search(code):
        names = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", code)
        if any(secret_name(x) for x in names if x.upper() == x and len(x) > 2):
            return True
        if re.search(r"(?:print|console\.log|puts|pp|p)\s*\(?\s*(?:dict\()?\s*(?:os\.environ|process\.env|ENV)\s*\)?\s*\)?\s*$",
                     code.strip().rstrip(";")) or re.search(r"print\s*\(\s*(?:dict\()?os\.environ\)?\s*\)", code):
            return True
    for s in re.findall(r"['\"]([^'\"]{1,300})['\"]", code):
        if secret_file(s):
            return True
    return False


# A call to a password store or a sign-in token tool written inside a small script.
STORE_CALL = re.compile(r"find-(?:generic|internet)-password|dump-keychain|secret-tool\W+lookup|keyring\W+get\b|"
                        r"\bgh\W+auth\W+token|print-(?:access|identity|refresh)-token|get-access-token|auth:token|"
                        r"credential\W+fill|\bop\W+read\b|\bpass\W+show\b")
SHOW_FLAG = re.compile(r"(?<![\w-])-[A-Za-z]*[wg][A-Za-z]*(?![\w-])")


def code_reads_store(code):
    """True when script text asks a password store for a secret (the lesson: never read a key "to test it")."""
    m = STORE_CALL.search(code)
    if not m:
        return False
    if m.group(0).startswith("find-") and not SHOW_FLAG.search(code):
        return False      # without -w or -g the password store prints no password
    return True


SHELL_WORDS = {"done", "fi", "esac", "while", "until", "for", "read", "do", "then", "{", "}"}
RECURSIVE_GREP = re.compile(r"^-[A-Za-z]*[rR][A-Za-z]*$|^--(?:recursive|dereference-recursive)$")
GREP_VALUE_OPTS = {"-e", "-f", "-m", "-A", "-B", "-C", "-d", "-D", "--include", "--exclude", "--exclude-dir",
                   "--regexp", "--file", "-g", "--glob", "-t", "--type", "-T", "--type-not", "--max-count",
                   "--context", "--after-context", "--before-context", "-G", "--ignore", "--file-search-regex"}
WALK_CAP = 3000


def grep_parts(name, args):
    """(paths searched, include globs, exclude globs, recursive, hidden files searched, typed) for a search command."""
    paths, inc, exc = [], [], []
    head = args[:args.index("--")] if "--" in args else args
    has_pattern_opt = any(a in ("-e", "-f", "--regexp", "--file") or a.startswith(("--regexp=", "--file="))
                          for a in head) or (name == "rg" and "--files" in head)
    recursive = name in ("rg", "ag")
    hidden = name not in ("rg", "ag")
    typed = False
    k, pattern_seen, ended = 0, has_pattern_opt, False
    while k < len(args):
        a = args[k]
        val = None
        if ended or a == "--":
            if a == "--" and not ended:
                ended = True        # after "--" every word is the pattern or a path, even one starting with -
            elif not pattern_seen:
                pattern_seen = True
            else:
                paths.append(a)
            k += 1
            continue
        if a.startswith("--") and "=" in a:
            a, val = a.split("=", 1)
        if a in GREP_VALUE_OPTS:
            if val is None:
                k += 1
                val = args[k] if k < len(args) else ""
            if a == "--include":
                inc.append(val)
            elif a in ("--exclude", "--exclude-dir", "--ignore"):
                exc.append(val)
            elif a in ("-g", "--glob"):
                if val.startswith("!"):
                    exc.append(val[1:])
                else:
                    inc.append(val)
            elif a in ("-t", "--type", "-G", "--file-search-regex"):
                typed = True
            elif a == "-d" and val == "recurse":
                recursive = True
            k += 1
            continue
        if a.startswith("-") and a != "-":
            if name not in ("rg", "ag") and RECURSIVE_GREP.match(a):
                recursive = True
            if a in ("--hidden", "-.", "--unrestricted") or re.match(r"^-u{2,}$", a) or (name == "ag" and a == "-u"):
                hidden = True
            k += 1
            continue
        if not pattern_seen:
            pattern_seen = True
        else:
            paths.append(a)
        k += 1
    return paths, inc, exc, recursive, hidden, typed


def pattern_files(args):
    """Files a search reads its patterns from (-f FILE, --file=FILE)."""
    out, k = [], 0
    while k < len(args):
        a = args[k]
        if a == "--":
            break
        if a in ("-f", "--file") and k + 1 < len(args):
            out.append(args[k + 1])
            k += 2
            continue
        if a.startswith("--file="):
            out.append(a.split("=", 1)[1])
        k += 1
    return out


SCRIPT_VALUE_OPTS = {"sed": {"-e", "--expression", "-f", "--file", "-l", "--line-length"},
                     "awk": {"-F", "-v", "-f", "--field-separator", "--assign", "--file"},
                     "jq": {"-f", "--from-file", "--indent", "-L"}}
SCRIPT_VALUE_OPTS["gawk"] = SCRIPT_VALUE_OPTS["awk"]
SCRIPT_VALUE_OPTS["yq"] = SCRIPT_VALUE_OPTS["jq"]
SCRIPT_FILE_OPTS = {"-f", "--file", "--from-file"}
JQ_PAIR_OPTS = {"--arg", "--argjson", "--slurpfile", "--rawfile"}


def file_operands(name, args):
    """The words a reader opens as files. For a search the pattern is not one (grep -n "\\.env" .gitignore
    reads only .gitignore), and neither is the script of sed or awk or the filter of jq. Everything else a
    reader is given still counts, so cat .env, grep KEY .env and jq . .env stay blocked."""
    if name in ("grep", "egrep", "fgrep", "rg", "ag"):
        return grep_parts(name, args)[0] + pattern_files(args)
    opts = SCRIPT_VALUE_OPTS.get(name)
    if opts is None:
        return list(args)
    out, script_given, k, ended = [], False, 0, False
    while k < len(args):
        a = args[k]
        if not ended and a == "--":
            ended = True
            k += 1
            continue
        if not ended and name in ("jq", "yq") and a in JQ_PAIR_OPTS:
            if a in ("--slurpfile", "--rawfile") and k + 2 < len(args):
                out.append(args[k + 2])     # --rawfile NAME FILE reads that file
            k += 3
            continue
        if not ended and a.startswith("--") and "=" in a:
            key, val = a.split("=", 1)
            if key in opts:
                script_given = script_given or key in SCRIPT_FILE_OPTS or key == "--expression"
                if key in SCRIPT_FILE_OPTS:
                    out.append(val)
                k += 1
                continue
        if not ended and a in opts:
            script_given = script_given or a in SCRIPT_FILE_OPTS or a in ("-e", "--expression")
            if a in SCRIPT_FILE_OPTS and k + 1 < len(args):
                out.append(args[k + 1])
            k += 2
            continue
        if not ended and a.startswith("-") and a != "-":
            k += 1
            continue
        out.append(a)
        k += 1
    if name == "yq" and out and out[0] in ("e", "eval", "ea", "eval-all"):
        out = out[1:]
    return out if script_given else out[1:]


GIT_PATTERN_OPTS = {"--grep", "--author", "--committer", "-S", "-G", "--format", "--pretty"}


def git_operands(sub, args):
    """The words a git command that prints file text reads as revisions or paths. A search pattern
    (git grep PATTERN, git log --grep=, -S, -G) is not one."""
    if sub == "grep":
        return grep_parts("grep", args)[0] + pattern_files(args)
    out, k = [], 0
    while k < len(args):
        a = args[k]
        if a == "--":
            out.extend(args[k + 1:])
            break
        key = a.split("=", 1)[0] if a.startswith("--") else a
        if key in GIT_PATTERN_OPTS:
            k += 1 if "=" in a else 2
            continue
        out.append(a)
        k += 1
    return out


def secret_under(folder, cwd, inc, exc, hidden):
    """A secret file's path under folder that the search would read, or None. Looks at WALK_CAP files at most."""
    import fnmatch
    base = os.path.expanduser(folder)
    if not os.path.isabs(base):
        base = os.path.join(cwd or os.getcwd(), base)
    if not os.path.isdir(base):
        return None
    seen = 0
    for dp, dns, fns in os.walk(base):
        dns[:] = [d for d in dns if d not in (".git", "node_modules", "__pycache__", ".venv", "venv")
                  and (hidden or not d.startswith(".")) and not any(fnmatch.fnmatch(d, e) for e in exc)]
        for f in fns:
            seen += 1
            if seen > WALK_CAP:
                return None
            if not hidden and f.startswith("."):
                continue
            if any(fnmatch.fnmatch(f, e) for e in exc):
                continue
            if inc and not any(fnmatch.fnmatch(f, i) for i in inc):
                continue
            rel = os.path.relpath(os.path.join(dp, f), base)
            if secret_file(rel):
                return rel
    return None


def search_reads_secret(name, args, cwd):
    """For grep, rg and ag: the secret file a folder search would print lines from, or None."""
    paths, inc, exc, recursive, hidden, typed = grep_parts(name, args)
    if not recursive or typed:
        return None
    for folder in paths or ["."]:
        hit = secret_under(folder, cwd, inc, exc, hidden)
        if hit:
            return hit if folder in (".", "./") else os.path.join(folder, hit)
    return None


def check_code(name, flag, code, rest, shown, cwd, depth, tainted):
    """Inline script text given with -c, -e and the like (or a heredoc fed to the program)."""
    code = unmask(code)
    if name in SHELLS:
        check_text(code, shown, cwd, depth + 1, tainted)
        return
    if name == "osascript":
        for inner in re.findall(r'do shell script\s+"((?:[^"\\]|\\.)*)"', code):
            check_text(inner.replace('\\"', '"'), shown, cwd, depth + 1, tainted)
        if shown and code_reads_store(code):
            raise Blocked()     # osascript prints the value of its last line
        return
    if not shown:
        return
    printing = bool(PRINT_CALL.search(code)) or flag in ("-p", "--print") or (
        len(flag) > 1 and flag[0] == "-" and flag[1:2] != "-" and "p" in flag[1:])
    if code_prints_secret(code) or (code_reads_store(code) and printing):
        raise Blocked()
    if rest and secret_args(rest, cwd):
        raise Blocked()         # perl -ne print .env, ruby -ne 'puts $_' .env


CODE_FLAGS = ("-c", "-e", "-p", "--eval", "--print", "-E", "-r")


def check_segment(argv, shown, cwd, depth, stdin=(), tainted=()):
    argv = unwrap(argv)
    if not argv:
        return
    name = os.path.basename(argv[0])
    source = secret_source(argv)
    if source == "always" or (source and shown):
        raise Blocked()
    if shown and env_dump(argv):
        raise Blocked()
    if shown and any(secret_file(x) for x in stdin):
        # "$(<.env)", "while read l; do echo $l; done < .env", "xargs echo < .env"
        bare = all(w in stdin for w in argv)
        if bare or name in READERS or name in PASSTHROUGH or name in SHELL_WORDS:
            raise Blocked()
    if name in SHELLS and "-c" in argv[1:]:
        k = argv.index("-c")
        if k + 1 < len(argv):
            check_code(name, "-c", argv[k + 1], argv[k + 2:], shown, cwd, depth, tainted)
        return
    if name == "eval":
        check_text(unmask(" ".join(argv[1:])), shown, cwd, depth + 1, tainted)
        return
    if name == "osascript":
        for k, a in enumerate(argv[1:-1], 1):
            if a == "-e":
                check_code(name, a, argv[k + 1], [], shown, cwd, depth, tainted)
        return
    if INTERPRETERS.match(name):
        for k, a in enumerate(argv[1:-1], 1):
            cluster = name in ("perl", "ruby") and re.match(r"^-[A-Za-z]*e$", a)
            if a in CODE_FLAGS or cluster:
                check_code(name, a, argv[k + 1], argv[k + 2:], shown, cwd, depth, tainted)
                break
        return
    if not shown:
        return
    if name == "git" and len(argv) > 1 and argv[1] in GIT_PRINTERS and secret_args(git_operands(argv[1], argv[2:]),
                                                                                   cwd):
        raise Blocked()
    quiet = (name in ("grep", "egrep", "fgrep", "rg", "ag") and any(QUIET_FLAGS.match(a) for a in argv[1:])) or (
        name == "sed" and any(a.startswith("-i") or a.startswith("--in-place") for a in argv[1:]))
    if quiet:
        return           # it prints nothing, or only file names and counts
    if name in ("echo", "printf", "print") or name in READERS:
        if any(prints_secret_var(a, tainted) for a in argv[1:]):
            raise Blocked()
    if name in READERS:
        if name == "openssl":
            rest = argv[1:]
            if not rest or rest[0] not in ("rsa", "pkey", "ec", "dsa", "pkcs12", "pkcs8"):
                return   # certificates and the like are public
            if "-pubout" in rest or ("-noout" in rest and "-text" not in rest):
                return
        if secret_args(file_operands(name, argv[1:]), cwd):
            raise Blocked()
        if name in ("grep", "egrep", "fgrep", "rg", "ag"):
            hit = search_reads_secret(name, argv[1:], cwd)
            if hit:
                raise Blocked(
                    "Blocked: this search also reads " + hit + ", a file that holds keys, so a key could show in "
                    "the chat. Leave that file out (for example --exclude=" + os.path.basename(hit) + ", or name "
                    "the folders to search), or list matching files only with -l.")


def has_secret_source(text, depth=0):
    """True when this command text gets a value from a password store or a token tool."""
    if depth > 3 or not text:
        return False
    t, subs = find_substs(text)
    for seg in segments(strip_heredocs(t)):
        a = unwrap(seg["argv"])
        if a and secret_source(a):
            return True
    return any(has_secret_source(x, depth + 1) for x in subs)


def tainted_names(segs, subs):
    """Variables filled from a password store in this command, such as p=$(security ... -w)."""
    out = set()
    for seg in segs:
        for w in seg["argv"]:
            m = re.match(r"^([A-Za-z_]\w*)=(.*)$", w, re.S)
            if not m:
                continue
            for sm in SUBST.finditer(m.group(2)):
                if has_secret_source(subs[int(sm.group(1))]):
                    out.add(m.group(1))
    return out


def check_text(cmd, shown, cwd, depth=0, tainted=frozenset()):
    """Raise Blocked when this shell text would print a stored secret where Claude can see it."""
    if depth > 3 or not cmd:
        return
    text, subs = find_substs(cmd)
    bodies = []
    segs = segments(mask_single_quoted(strip_heredocs(text, bodies)))
    tainted = frozenset(tainted) | tainted_names(segs, subs)
    # heredoc bodies fed to a shell, a script runner or osascript are checked as that program's code
    for start, body in bodies:
        head = start.split("<<", 1)[0]
        if re.search(r"(?<![<0-9&])>", head):
            continue    # cat > file <<EOF writes a file, it shows nothing
        words = (segments(head) or [{"argv": []}])[-1]["argv"]
        first = unwrap(words)
        if first:
            nm = os.path.basename(first[0])
            if nm in SHELLS or nm == "osascript" or INTERPRETERS.match(nm):
                check_code(nm, "", body, [], shown, cwd, depth, tainted)
    # group into pipelines; a pipeline's output is seen when it is not sent to a file or captured unseen
    start = 0
    for idx, seg in enumerate(segs):
        if seg["pipe"] and idx + 1 < len(segs):
            continue
        pipe = segs[start:idx + 1]
        start = idx + 1
        end_seen = shown and not pipe[-1]["redir"]
        for k, s in enumerate(pipe):
            later = [os.path.basename((unwrap(x["argv"]) or [""])[0]) for x in pipe[k + 1:]]
            # what this command prints is seen if the pipeline ends on screen and only passes text along
            seen = end_seen and not s["redir"] and all(x in PASSTHROUGH for x in later)
            # a reader's text is seen if the pipeline ends on screen at all (grep, sed and the like show it)
            reader_seen = end_seen and not s["redir"]
            argv = s["argv"]
            first = unwrap(argv)
            first_name = os.path.basename(first[0]) if first else ""
            check_segment(argv, reader_seen if first_name in READERS else seen, cwd, depth, s.get("stdin", ()),
                          tainted)
            # command substitutions inside this command
            for w in argv:
                for m in SUBST.finditer(w):
                    inner = subs[int(m.group(1))]
                    lead = first_name if first else ""
                    printed_by_parent = (lead in ("echo", "printf", "print") or lead in READERS
                                         or bool(first and SUBST.fullmatch(first[0])))
                    check_text(inner, seen and printed_by_parent, cwd, depth + 1, tainted)


# ---------------------------------------------------------------- money
MONEY_WORDS = {"pay", "pays", "paying", "payment", "payments", "payout", "payouts", "payroll", "refund", "refunds",
               "refunding", "charge", "charges", "charging", "purchase", "purchases", "purchasing", "buy", "buying",
               "checkout", "withdraw", "withdrawal", "withdrawals", "donate", "donation", "reimburse",
               "reimbursement", "reimbursements"}
# Pairs that move money only together: "place order", "approve bill".
ORDER_WORDS = {"order", "orders"}
ORDER_ACTIONS = {"place", "submit", "checkout", "buy", "purchase", "confirm"}
BILL_WORDS = {"bill", "bills", "expense", "expenses"}
BILL_ACTIONS = {"create", "submit", "approve", "pay", "send", "new", "add"}
MOVE_WORDS = {"send", "sends", "transfer", "transfers", "wire", "move", "deposit", "remit", "pay"}
MONEY_NOUNS = {"money", "funds", "fund", "cash", "payment", "payments", "usd", "dollars", "balance", "bank", "ach",
               "crypto", "bitcoin", "btc", "eth", "usdc", "invoice", "invoices", "wire", "remittance"}
READ_WORDS = {"list", "get", "search", "find", "read", "fetch", "retrieve", "view", "show", "describe", "lookup",
              "query", "count", "check", "preview", "estimate", "calculate", "validate", "history", "status"}
ACTION_WORDS = {"create", "send", "issue", "capture", "execute", "submit", "approve", "confirm", "process", "make",
                "initiate", "start", "run", "pay", "refund", "charge", "transfer", "payout", "buy", "purchase",
                "withdraw", "donate", "post", "add", "new"}


def words_of(tool):
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", tool)
    return [w for w in re.split(r"[^A-Za-z0-9]+", spaced.lower()) if w]


PAY_SERVERS = {"stripe", "paypal", "square", "venmo", "wise", "transferwise", "plaid", "coinbase", "braintree",
               "adyen", "revolut", "payoneer", "razorpay", "mollie", "klarna", "cashapp", "zelle", "gocardless",
               "paddle", "lemonsqueezy", "payments", "payment", "banking", "bank", "wallet", "billing",
               # accounting, spend and payroll services
               "intuit", "xero", "ramp", "brex", "mercury", "gusto", "bill", "billcom", "expensify", "freshbooks",
               "netsuite", "sage", "zoho", "divvy", "airwallex", "deel", "rippling", "melio", "tipalti"}
PAY_SERVER_WORDS = {"order", "orders", "invoice", "invoices", "subscription", "subscriptions", "transfer",
                    "transfers", "payout", "payouts", "intent", "session", "bill", "bills", "reimbursement",
                    "reimbursements", "expense", "expenses", "purchase", "card", "cards", "payroll"}


def moves_money(tool):
    words, server = words_of(tool), set()
    if tool.startswith("mcp__") and tool.count("__") >= 2:
        server = set(words_of(tool.split("__", 2)[1]))
        words = words_of(tool.split("__", 2)[2])
    ws = set(words)
    money = bool(ws & MONEY_WORDS) or bool(ws & MOVE_WORDS and ws & MONEY_NOUNS)
    if (ws & ORDER_WORDS and ws & ORDER_ACTIONS) or (ws & BILL_WORDS and ws & BILL_ACTIONS):
        money = True
    if server & PAY_SERVERS and ws & PAY_SERVER_WORDS:
        money = True
    if not money:
        return False
    if ws & READ_WORDS and not ws & ACTION_WORDS:
        return False
    return True


# ---------------------------------------------------------------- main
def decide(data):
    tool = str(data.get("tool_name") or "")
    ti = data.get("tool_input") or {}
    if not isinstance(ti, dict):
        ti = {}
    cwd = str(data.get("cwd") or "")
    if tool == "Bash":
        cmd = ti.get("command")
        if isinstance(cmd, str) and cmd.strip():
            try:
                check_text(cmd, True, cwd)
            except Blocked as e:
                return "deny", (e.args[0] if e.args else SECRET_REASON)
        return None
    if tool == "Read":
        path = ti.get("file_path")
        if isinstance(path, str) and secret_file(os.path.expanduser(path)):
            return "deny", SECRET_REASON
        return None
    if tool == "Grep":
        if str(ti.get("output_mode") or "files_with_matches") != "content":
            return None
        path = ti.get("path")
        if isinstance(path, str) and secret_file(path):
            return "deny", SECRET_REASON
        pattern = ti.get("glob")
        if isinstance(pattern, str) and pattern and secret_file(pattern.replace("*", ".x")):
            return "deny", SECRET_REASON
        return None
    if moves_money(tool):
        return "ask", MONEY_REASON
    return None


def main():
    data = json.load(sys.stdin)
    if not isinstance(data, dict):
        return
    verdict = decide(data)
    if verdict:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": verdict[0],
                                                 "permissionDecisionReason": verdict[1]}}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
