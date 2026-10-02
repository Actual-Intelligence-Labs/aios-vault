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
    "read and follow .claude/skills/pdf/SKILL.md."
)

MACHINE_SOURCES = {"system", "loop_wakeup", "schedule_wakeup", "poll_event"}
MACHINE_PREFIXES = ("<task-notification", "<local-command", "<system-reminder")

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
    prompt = data.get("prompt") or data.get("user_prompt") or data.get("userPrompt") or ""
    if not isinstance(prompt, str) or not prompt.strip():
        return
    if str(data.get("source") or "") in MACHINE_SOURCES or prompt.lstrip().startswith(MACHINE_PREFIXES):
        return
    lower = prompt.lower()
    fire = has(ARTIFACTS, lower) or (has(LOOSE, lower) and has(ACTIONS, lower))
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
