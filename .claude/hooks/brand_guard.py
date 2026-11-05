"""Brand guard: runs every time you send a message, before the AI answers.

WHAT IT DOES
  It is the reason your documents come out right the first time. When your
  message asks for something to be made (a PDF, a proposal, a post, an email,
  a deck), it adds one instruction to the turn: read brand/brand.md,
  memory/taste.md and references/voice.md BEFORE writing a word. That is why
  you never have to say "use my colors" or "sound like me". It does not load
  those files itself. It tells the AI to.

  It stays quiet while setup is asking its questions: a writing sample you
  paste in during setup is an answer, not a request to make something.
  It also stays quiet inside helper agents, and on messages the computer
  wrote rather than the owner (a finished background job, a timer, a
  message passed on from another agent).
  It stays quiet when the message asks to update, upgrade or clean up the
  vault ("update my vault ... tell me in plain words what changed", or an
  older paste's "give me the plain report"): that report is about the
  vault, not a document. A real request to make something in the same
  message (a proposal, a post, an email) still brings the reminder.

SAFETY
  Never blocks a turn. Never fails loudly. On any error it prints nothing.
  Runs on Python 3.9 or newer, standard library only, through run.sh.
"""

import json
import os
import re
import sys
import time

# ---------------------------------------------------------------------------
# THE TRIGGER LISTS. THESE ARE MEANT TO BE EDITED.
#
# Add whatever you actually make. If you produce podcast show notes every
# week, add "show notes" to ARTIFACTS and this starts branding those too.
# Separate entries with a pipe character. Each entry matches as a whole word,
# so "doc" never fires on "doctor".
#
# ARTIFACTS   things that are always a produced document. These fire on
#             their own, because "one pager" only ever means "make me one".
# LOOSE       words that are sometimes a document and sometimes just talk.
#             "email" is a document in "write me an email" and ordinary
#             conversation in "did you see the email from the client".
#             These fire ONLY when an ACTION word is in the message too.
# ACTIONS     words that mean "produce it".
#
# Firing on every message is the failure mode to avoid. An instruction that
# arrives on every single turn becomes wallpaper, and the AI skims past it on
# the turn that actually mattered.
# ---------------------------------------------------------------------------
ARTIFACTS = ("pdf|one pager|onepager|one-pager|two pager|two-pager|proposal|deck|sell sheet|sell-sheet|"
             "leave behind|leave-behind|case study|newsletter|landing page|brochure|flyer|press release|"
             "white paper|whitepaper|slide deck|pitch deck|one sheet|one-sheet|rate sheet|handout")

LOOSE = ("doc|docs|document|letter|memo|report|post|linkedin|tweet|thread|email|draft|caption|script|invoice|"
         "quote|estimate|slides?|presentation|write up|write-up|summary|agenda|bio|blurb|headline|"
         "subject line|outline|contract|statement of work|sow|update|recap")

ACTIONS = ("make|write|draft|create|build|design|produce|prepare|generate|compose|put together|turn this into|"
           "turn that into|turn it into|rewrite|redo|polish|format|lay out|layout|need a|need an|i need|"
           "send me|give me|do me|knock out|whip up|can you do|help me with|work up|spin up|mock up|mock-up")

CONTEXT = (
    "This message asks for something to be produced (a document, a post, an email, a deck, or similar). "
    "Before you write any of it, read these three files and match them: brand/brand.md for colors, fonts, "
    "logo files and document defaults; memory/taste.md for what the owner likes and hates; "
    "references/voice.md for the register and sentence rhythm. Use the real logo file from brand/logos/, never "
    "a generated or traced one, and pick the variant that suits the background (dark logo on a light page, "
    "light logo on a dark page). If a brand field you need is still a placeholder in double curly braces, ask "
    "ONE short question and then WRITE the answer back into brand/brand.md so it is never asked again. Never "
    "ask the owner to re-describe their brand from scratch. If the output is a PDF or any designed document, "
    "run the pdf skill (the Skill tool, or /pdf) and follow it."
)

# A message that asks to update, upgrade or clean up the vault itself. Its own words
# ("update", "the plain report") are not a document request. Any other document word
# in the same message (a proposal, an email, a post) still fires as usual.
UPKEEP = re.compile(
    r"(^|[^a-z])(update|upgrade|clean ?up|clean-up|tidy|tidy up|optimi[sz]e|de-?bloat|declutter)"
    r"\s+(?:[a-z']+\s+){0,2}?(my|the|this|our)\s+(?:obsidian\s+|second\s+)?(vault|brain)([^a-z]|$)"
    r"|(^|[^a-z])update how you work([^a-z]|$)"
    r"|(update|optimize)-vault"
    r"|github\.com/[^\s]*/aios-vault")
UPKEEP_WORDS = ("update", "upgrade", "report", "summary", "recap")
LOOSE_FOR_UPKEEP = "|".join(w for w in LOOSE.split("|") if w not in UPKEEP_WORDS)

MACHINE_SOURCES = {"system", "loop_wakeup", "schedule_wakeup", "poll_event"}
# Text the computer wrote, not the owner: background-task and timer notices, messages
# relayed from other agents or chats, and output pasted in by a shell command.
MACHINE_PREFIXES = ("<task-notification", "<local-command", "<system-reminder", "<agent-message",
                    "<teammate-message", "<cross-session-message", "<bash-stdout", "<bash-stderr",
                    "<bash-input", "<user-prompt-submit-hook")

SETUP_FRESH_SECONDS = 3 * 3600   # setup saves each answer as it goes; older than this, it was abandoned


def has(words, text):
    return re.search(r"(^|[^a-z])(" + words + r")([^a-z]|$)", text) is not None


def vault_root():
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(os.path.dirname(here))
    if os.path.isdir(os.path.join(root, ".claude")):
        return root
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    return env if env and os.path.isdir(env) else os.getcwd()


def setup_in_progress(root):
    """Setup saves each answer to intake.md as it goes, so a fresh "in progress" means setup is running."""
    path = os.path.join(root, "intake.md")
    try:
        if time.time() - os.path.getmtime(path) > SETUP_FRESH_SECONDS:
            return False
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            head = fh.read(6000)
    except OSError:
        return False
    return re.search(r"\*\*Setup status:\*\*\s*in progress", head, re.I) is not None


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    if not isinstance(data, dict):
        return
    if data.get("agent_id") or "/subagents/" in str(data.get("transcript_path") or "").replace("\\", "/"):
        return   # a helper agent's turn, not the owner's
    prompt = data.get("prompt") or data.get("user_prompt") or data.get("userPrompt") or ""
    if not isinstance(prompt, str) or not prompt.strip():
        return
    if str(data.get("source") or "") in MACHINE_SOURCES or prompt.lstrip().startswith(MACHINE_PREFIXES):
        return
    lower = prompt.lower()
    loose = LOOSE_FOR_UPKEEP if UPKEEP.search(lower) else LOOSE
    fire = has(ARTIFACTS, lower) or (has(loose, lower) and has(ACTIONS, lower))
    if not fire:
        return  # ordinary conversation, say nothing at all
    if setup_in_progress(vault_root()):
        return  # a setup answer, such as a pasted writing sample
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": CONTEXT}}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
