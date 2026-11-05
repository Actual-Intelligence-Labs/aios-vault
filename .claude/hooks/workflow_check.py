"""Helper type check: runs before Claude starts a workflow script.

WHAT IT DOES
  A workflow script starts helper agents with agent(...). A helper that names
  no type runs at full size: it loads the whole list of skills and connectors
  on every step, which costs far more tokens than it needs. Most helpers only
  read, search, write code or run tests, and the slim "lean-worker" type
  (.claude/agents/lean-worker.md) does those jobs for much less.
  So when a script calls agent() and never says "agentType", this check sends
  it back once with the fix. The same script sent again, unchanged, passes,
  so nothing ever gets stuck.

  It also sends a script back once when its instructions give a helper a
  Bash time limit over 270000 ms (4.5 minutes), or tell it never to let a time
  limit cut a run short. A wait that long makes Claude re-read the whole
  conversation at full price. The message says to run long jobs in the
  background writing a log and to wait in slices of 250 seconds or less.

SAFETY
  It never blocks for good, never changes the script, and logs nothing. It
  remembers only a short fingerprint of each script it sent back, in the
  computer's temp folder, so the second try passes.
  On any error it prints nothing and gets out of the way.
  Runs on Python 3.9 or newer, standard library only, through run.sh.
"""

import hashlib
import json
import os
import re
import sys
import tempfile

AGENT_CALL = re.compile(r"\bagent\s*\(")
MAX_SCRIPT_BYTES = 2000000
MAX_BASH_MS = 270000
TIME_LIMIT = re.compile(r"time limit cut", re.I)
# A number of 6 to 12 characters (digits, with _ or , between them) that is not part of a longer run. The bounded
# repeat and the lookarounds keep the search fast on any text.
NUM = r"(?<![\d_,])(\d[\d_,]{4,10}\d)(?![\d_,])"
TIMEOUT_NEAR = re.compile(r"(?i)\btimeout\b[^\d\n]{0,24}" + NUM + r"|" + NUM + r"[ \t]*(?:ms)?[^\d\n]{0,12}\btimeout\b")

WAIT_REASON = ("This script tells helpers to wait too long in one step: a Bash time limit over 270000 ms, or never "
               "letting a time limit cut a run short. A wait past about 5 minutes makes Claude re-read the whole "
               "conversation at full price. Tell helpers to start long jobs in the background writing a log, then "
               "wait in slices of 250 seconds or less and read the end of the log. Fix the instructions, or send the "
               "script again with these lines unchanged and it will pass.")

REASON = ("Pick a helper type for the agent() calls in this script first. Helpers that only read, search, check, "
          "write code, run tests or write local files: add agentType: 'lean-worker' to their options (it skips the "
          "skill and connector lists, so every step costs far fewer tokens). Helpers that need a skill, a connector, "
          "writing a client will read, or outreach: agentType: 'general-purpose'. To run this script as it is, send "
          "it again unchanged and it will pass.")


def state_dir():
    base = os.environ.get("VAULT_HOOKS_TEMP") or os.path.join(tempfile.gettempdir(), "aios-vault-hooks")
    return os.path.join(base, "workflow-check")


def long_wait_hits(script):
    """The bits of the script that ask for a wait over the limit."""
    hits = [m.group(0) for m in TIME_LIMIT.finditer(script)]
    for line in script.splitlines():
        if "timeout" not in line.lower():
            continue
        for m in TIMEOUT_NEAR.finditer(line):
            n = int((m.group(1) or m.group(2)).replace("_", "").replace(",", ""))
            if n > MAX_BASH_MS:
                hits.append(m.group(0).strip())
    return hits


def seen_before(data, script, kind=""):
    """True when this session already sent back this exact script; otherwise remember it."""
    who = hashlib.sha256(("%s|%s" % (data.get("session_id"), data.get("agent_id"))).encode()).hexdigest()[:24]
    mark = hashlib.sha256((kind + script).encode("utf-8", "replace")).hexdigest()[:24]
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


def script_of(tool_input):
    script = tool_input.get("script")
    if isinstance(script, str) and script:
        return script
    path = tool_input.get("scriptPath")
    if isinstance(path, str) and path:
        path = os.path.expanduser(path)
        if os.path.isfile(path) and os.path.getsize(path) < MAX_SCRIPT_BYTES:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                return fh.read()
    return ""


def main():
    data = json.load(sys.stdin)
    if not isinstance(data, dict) or data.get("tool_name") != "Workflow":
        return
    tool_input = data.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return
    script = script_of(tool_input)
    if not script:
        return  # a saved workflow called by name: leave it alone
    reason = None
    if AGENT_CALL.search(script) and "agentType" not in script and not seen_before(data, script):
        reason = REASON
    if reason is None:
        hits = long_wait_hits(script)
        # remembered by the lines that ask for the long wait, so the same lines sent again pass
        if hits and not seen_before(data, "\n".join(sorted(hits)), "wait|"):
            reason = WAIT_REASON
    if reason:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                 "permissionDecisionReason": reason}}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
