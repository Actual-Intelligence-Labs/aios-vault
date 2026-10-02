"""Auto-capture: runs every time you send a message, before the AI answers.

WHAT IT DOES
  It watches for a loose thought. When you type something like
  "oh I should follow up with the accountant at some point", this tells the
  AI to file it in the right place instead of just replying "got it".
  Starting a message with "inbox:" or "capture:" forces that behavior.

  It stays QUIET when your message is clearly an instruction, a question, or
  an answer, because a reminder that fires on every message becomes noise and
  the AI learns to skim past it. See THE QUIET PATH below.

SAFETY
  Never blocks a turn and never fails loudly. If the input is odd or anything
  goes wrong, it prints nothing and gets out of the way. Read only.
  Runs on Python 3.9 or newer, standard library only, through run.sh.
"""

import json
import os
import re
import sys
import time

FORCED_MSG = (
    'FORCED CAPTURE. This message begins with "inbox:" or "capture:", so run the capture skill '
    "(.claude/skills/capture/SKILL.md) now, no matter what else it looks like. Read that skill and follow it. "
    "Strip the prefix. Clean up dictation noise (filler words, false starts, run-on phrasing) without changing "
    "the meaning. Check every name against context/who-and-what.md first and use the name as written there. "
    "Route it to exactly ONE home: a calendar event if it is time-bound, a project note if it belongs to a "
    "project, a decision in decisions/log.md, a preference in memory/taste.md (with a scope tag and the "
    "principle behind it), a no-rush to-do in tasks.md, a new fact in context/about-me.md or "
    "context/about-business.md, a new person or company as a row in context/who-and-what.md (how to reach "
    "them goes in context/contacts.md), an idea in ideas.md, or just do it now if it is small and doable. "
    "If no calendar is reachable (see connections.md), say so in one line and put the item in tasks.md "
    "instead. Never pretend an event was created. Log one line in inbox.md. End with a single sentence saying "
    "what you did and where it went."
)

SOFT_MSG = (
    "This message looks like a loose thought, a half-formed idea, a reminder, or a to-do rather than an "
    "instruction. Do not merely acknowledge it. Read the capture skill (.claude/skills/capture/SKILL.md) and "
    "follow it: check names against context/who-and-what.md, clean up the wording, file it in exactly ONE home "
    "(calendar event, project note, decisions/log.md, memory/taste.md with a scope tag and its principle, "
    "tasks.md, context/about-me.md, context/about-business.md, a row in context/who-and-what.md for a new "
    "person or company, ideas.md, or just do the small thing now), log one line in inbox.md, and end with a "
    "single sentence saying what you did and where it went. If no calendar is reachable (see connections.md), "
    "say so in one line and put the item in tasks.md instead. Never pretend an event was created. If this "
    "message does after all carry a clear instruction or a direct question, answers a question you just "
    "asked, or continues the task already in progress, ignore this reminder entirely and respond normally."
)

# ---------------------------------------------------------------------------
# THE QUIET PATH
#
# Say nothing at all when the message is plainly an instruction, a question
# or an answer. Cheap tests, in order:
#   1. It starts with a slash, so it is a command.
#   2. It ends with a question mark, so it is a question.
#   3. It is a greeting or an acknowledgement ("thanks", "ok cool").
#   4. It is a short answer ("yes, the second one", "1, 3 and 5", "none").
#   5. It starts with a phrase one of this vault's skills listens for
#      ("map my files", "hand this off"), or another phrase aimed at the AI
#      ("I connected my email").
#   6. Its first word is a verb aimed at the AI ("draft", "fix", "make"),
#      after any "please", "ok" or "let's" in front of it.
#   7. It holds pasted code (a ``` block).
#   8. The computer wrote it, not you (a finished background task).
#   9. Setup is in progress, so it is an answer to a setup question.
#
# Note what is deliberately NOT on the verb list: remind, note, need, add,
# and "don't forget". "remind me to call the accountant Thursday" is a thing
# to file, not a job to do this turn, and the capture skill treats it that way.
# ---------------------------------------------------------------------------

# Words that make up a greeting or an acknowledgement. A short message made
# only of these is never a thought to file.
ACK_WORDS = set("""
hi hey hello morning good evening afternoon thanks thank you thx ty ok okay k kk cool nice great perfect awesome
sounds looks lgtm got it yes yeah yep yup no nope sure so much all right alright fine love that this works
noted makes sense brilliant amazing excellent wonderful lovely cheers appreciate appreciated very much
""".split())

# A short reply that opens with one of these is an answer to a question,
# unless it also carries a word that marks something to hold ("remind").
ANSWER_STARTS = set("""
yes yeah yep yup no nope nah sure ok okay correct right exactly both all none neither either option
""".split())
CAPTURE_CUES = set("""
remind reminder forget need needs should todo idea note remember someday sometime eventually must gotta
""".split())
ANSWER_PHRASES = ("the first", "the second", "the third", "the last", "the other", "go ahead", "do it",
                  "go for it", "not now", "not yet", "skip it", "skip that", "all of them", "none of them",
                  "sounds good", "looks good", "that works", "that one", "this one")

# Courtesy and filler words that can sit in front of the real first word.
LEAD_WORDS = {"please", "pls", "plz", "kindly", "ok", "okay", "so", "and", "also", "now", "then", "hey",
              "hi", "oh", "um", "uh", "alright", "right", "cool", "great", "claude"}

# Verbs and question words that mean "do this now" rather than "hold this".
INSTRUCTIONS = set("""
analyze analyse answer append archive ask build can change check clean compare compile connect convert copy
correct could create cut delete describe design did do does draft edit explain export file fill find finish
fix format generate get give go hand handle handoff help hide how implement import improve install is list
look make map merge move onboard open organize organise outline pick plan prepare print process pull put read
rebuild recap redo refactor refresh reload remove rename render replace research resend restart resume review
rewrite run save search send set should show simplify sort split start summarise summarize tell test
translate turn undo unhide update upgrade upload use verify walk was what whats when where which who why will
would write
stop continue proceed retry revert cancel skip approve approved confirm
""".split())

# Phrases aimed at the AI that do not start with a verb. Matched at the start
# of the message (after any lead words), lowercase.
AIMED_PREFIXES = (
    "i just downloaded", "i downloaded this", "i just cloned", "i cloned this", "i connected", "i just connected",
    "i added my logo", "i added my logos", "i just added my logo", "i just added my logos", "i added the logos",
    "i put my logos", "i dropped my logos", "is everything working",
    "everything working", "where were we", "pick up where", "this chat is getting long",
)
# Phrases aimed at the AI anywhere in the message: editing the vault's own lists.
AIMED_ANYWHERE = ("brand guard list", "brain log list", "brand guard's list", "brain log's list")

# Skills whose trigger phrases never silence this check, and first words that
# make a quoted phrase too general to count ("I need to close this").
NOT_TRIGGERS = {"capture"}
TOO_GENERAL = {"i", "we", "this", "that", "it", "they", "he", "she", "you", "my", "our"}

MACHINE_SOURCES = {"system", "loop_wakeup", "schedule_wakeup", "poll_event"}
MACHINE_PREFIXES = ("<task-notification", "<local-command", "<system-reminder")

SETUP_FRESH_SECONDS = 3 * 3600   # setup saves each answer as it goes; older than this, it was abandoned


def vault_root():
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(os.path.dirname(here))
    if os.path.isdir(os.path.join(root, ".claude")):
        return root
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    return env if env and os.path.isdir(env) else os.getcwd()


def words_of(text):
    """Lowercase words, apostrophes dropped: "don't" becomes "dont", "let's" becomes "lets"."""
    return [w.replace("'", "") for w in re.findall(r"[a-z0-9]+(?:'[a-z]+)?", text)]


def is_ack(lower):
    w = words_of(lower)
    return 0 < len(w) <= 6 and all(x in ACK_WORDS for x in w)


def is_answer(lower):
    """A short reply to a question: "yes, the second one", "1, 3 and 5", "none"."""
    w = words_of(lower)
    if not w or any(x in CAPTURE_CUES for x in w):
        return False
    # only numbers or single letters, with commas and "and": "1, 3 and 5", "a", "#2"
    if len(w) <= 8 and all(x.isdigit() or len(x) == 1 or x in ("and", "or", "both", "all") for x in w):
        return True
    if len(w) > 6:
        return False
    return w[0] in ANSWER_STARTS or " ".join(w).startswith(ANSWER_PHRASES)


def strip_lead(lower):
    """Drop courtesy and filler words in front of the real first word."""
    w = words_of(lower)
    i = 0
    while i < len(w) - 1 and w[i] in LEAD_WORDS:
        i += 1
    return w[i:]


def opens_with_instruction(lower):
    w = strip_lead(lower)
    if not w:
        return False
    first = w[0]
    nxt = w[1] if len(w) > 1 else ""
    if first == "dont" or (first == "do" and nxt == "not"):
        rest = w[1:] if first == "dont" else w[2:]
        if rest[:1] == ["forget"] or rest[:3] == ["let", "me", "forget"]:
            return False                     # "don't forget to send the invoice": a thing to hold
        return True                          # "don't send that yet"
    if first == "lets" or (first == "let" and nxt == "us"):
        verb = nxt if first == "lets" else (w[2] if len(w) > 2 else "")
        return verb in INSTRUCTIONS          # "let's draft it" yes, "let's circle back on pricing" no
    if first == "let":
        return False                         # "let me think about raising prices"
    return first in INSTRUCTIONS


def skill_phrases(root):
    """Trigger phrases quoted in this vault's skill descriptions ("map my files")."""
    out = []
    sk = os.path.join(root, ".claude", "skills")
    try:
        names = sorted(os.listdir(sk))
    except OSError:
        return out
    for n in names:
        if n in NOT_TRIGGERS or n.startswith("."):
            continue
        try:
            with open(os.path.join(sk, n, "SKILL.md"), "r", encoding="utf-8", errors="ignore") as fh:
                head = fh.read(4000)
        except OSError:
            continue
        m = re.search(r"^description:\s*(.+)$", head, re.M)
        if not m:
            continue
        for q in re.findall(r'"([^"]{3,80})"', m.group(1).replace('\\"', '"')):
            p = q.lower().strip()
            p = re.sub(r"\.\.\.$", "", p.replace(chr(0x2026), "...")).strip()
            # drop a trailing stand-in such as X, Y, Z or <name>
            p = re.sub(r"(\s+(x|y|z|<[^>]*>|\{\{[^}]*\}\}))+$", "", p).strip()
            pw = words_of(p)
            # three words or more: a two-word phrase ("new client") is too easy to say in passing
            if len(pw) >= 3 and pw[0] not in TOO_GENERAL and not pw[0].startswith(("inbox", "capture")):
                out.append(" ".join(pw))
    return out


def starts_with_phrase(lower, phrases):
    text = " ".join(strip_lead(lower))
    for p in phrases:
        p = " ".join(words_of(p))
        if text == p or text.startswith(p + " "):
            return True
    return False


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


def emit(text):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": text}}))


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    if not isinstance(data, dict):
        return
    prompt = data.get("prompt") or data.get("user_prompt") or data.get("userPrompt") or ""
    if not isinstance(prompt, str):
        return
    trimmed = prompt.strip()
    if not trimmed:
        return
    if str(data.get("source") or "") in MACHINE_SOURCES or trimmed.startswith(MACHINE_PREFIXES):
        return
    lower = trimmed.lower().replace(chr(0x2019), "'")   # a curly apostrophe counts as a straight one

    if lower.startswith(("inbox:", "capture:")):
        emit(FORCED_MSG)
        return
    if lower.startswith("/"):
        return                      # a slash command
    if lower.rstrip(" .!)\"'*_`").endswith("?"):
        return                      # a question
    if is_ack(lower):
        return                      # a greeting or an acknowledgement, nothing to file
    if is_answer(lower):
        return                      # a short answer to something the AI asked
    if "```" in trimmed:
        return                      # pasted code is context for a task, not a loose thought
    if any(p in lower for p in AIMED_ANYWHERE):
        return                      # "add show notes to the brand guard list"
    if starts_with_phrase(lower, AIMED_PREFIXES):
        return                      # "I connected my email", "I just downloaded this"
    if opens_with_instruction(lower):
        return                      # an instruction for this turn
    root = vault_root()
    if starts_with_phrase(lower, skill_phrases(root)):
        return                      # "map my files", "import my contacts": a skill's own trigger
    if setup_in_progress(root):
        return                      # setup is asking questions; this is an answer
    emit(SOFT_MSG)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
