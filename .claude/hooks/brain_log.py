"""Brain log: runs at the end of every reply, just before the AI stops.

WHAT IT DOES
  If, since your last message, the AI sent or drafted an email, created or
  changed a calendar event, or saved a file to cloud storage, and it did NOT
  update any note about it, this check holds the reply ONE time and tells the
  AI to log it: one short dated line on the person or company note, the
  note's status line updated, and for a file, its link (never the file
  itself) on the note. That is how the vault keeps up with what went out
  without you having to remember.

  Only notes under projects/, context/, references/ or decisions/ count as
  logging it. A line in inbox.md, tasks.md, ideas.md or memory/ does not:
  those are not where anyone looks for a person or a company.

  A new calendar block with nobody else invited (time you set aside for
  yourself) is not held: nothing went out to anyone.

THE LISTS BELOW ARE MEANT TO BE EDITED
  Tool names differ from one email, calendar or storage connection to the
  next. Each list holds pieces of tool names. A tool counts when its name
  contains any piece (capitals, dashes, dots and underscores do not matter).
  A tool on none of the lists still counts when its own name pairs an action
  word with a thing word, such as "reply" with "mail" or "upload" with "file"
  (the FALLBACK lists further down). Connect something new that is still
  missed? Ask Claude to add its tool names here.

SAFETY
  Reads the session transcript and file dates only. Never writes, never
  touches the network. It holds a reply at most once in a row (Claude Code's
  stop_hook_active flag), and on any error it lets the reply finish.
  Runs on Python 3.9 or newer, standard library only, through run.sh.
"""

import calendar
import json
import os
import re
import shlex
import sys

# Email: sending, drafting, replying, forwarding.
# Gmail, Outlook and Microsoft 365, Apple Mail, and the common connector styles.
EMAIL_TOOLS = (
    "send_message", "send_email", "send_mail", "sendmail", "send_gmail", "send_serial_email",
    "send_draft", "send_reply",
    "create_draft", "update_draft", "save_draft", "draft_email", "draft_gmail", "create_email_draft",
    "gmail__reply", "gmail__forward", "reply_to_message", "reply_message", "reply_email", "reply_mail",
    "reply_all", "reply_to_email", "reply_to_thread", "create_reply", "forward_message", "forward_email",
    "forward_mail", "create_forward",
)

# Calendar: creating, changing, answering or cancelling an event.
# Google Calendar, Outlook calendar, and the common connector styles.
CALENDAR_TOOLS = (
    "create_event", "update_event", "patch_event", "delete_event", "cancel_event", "move_event",
    "manage_event", "respond_to_event", "accept_event", "decline_event", "tentatively_accept",
    "create_calendar_event", "update_calendar_event", "delete_calendar_event", "cancel_calendar_event",
    "accept_calendar_event", "decline_calendar_event", "calendar_quick_add", "quick_add_event",
)

# Cloud storage: a file saved, uploaded, copied or changed.
# Google Drive, OneDrive and SharePoint, Dropbox, Box.
STORAGE_TOOLS = (
    "google_drive__create_file", "google_drive__copy_file", "google_drive__update_file",
    "google_drive__upload", "googledrive_upload", "googledrive_create_file", "googledrive_copy_file",
    "create_drive_file", "copy_drive_file", "update_drive_file", "upload_drive_file",
    "gdrive__create", "gdrive_create", "gdrive__upload", "gdrive_upload",
    "import_to_google_doc", "import_to_google_sheets", "import_to_google_slides",
    "upload_file", "upload_new_file", "upload_large_file", "upload_to_drive",
    "onedrive__upload", "onedrive_upload", "one_drive_upload", "onedrive_create", "one_drive_create",
    "sharepoint__upload", "sharepoint_upload", "share_point_upload", "upload_to_onedrive",
    "upload_to_sharepoint", "create_drive_item",
    "dropbox__upload", "dropbox_upload", "dropbox__save", "dropbox_save", "dropbox__create_file",
    "dropbox_create_file", "dropbox__copy", "dropbox_copy",
    "box__upload", "box_upload",
)

# Sharing a cloud file with someone (the service usually emails them).
SHARE_TOOLS = (
    "share_file", "share_folder", "share_drive_item", "manage_drive_access", "set_drive_file_permissions",
    "create_permission", "add_permission", "create_sharing_link", "create_shared_link", "add_file_member",
    "add_folder_member", "invite_to_file",
)

# FALLBACK: a tool on none of the lists above still counts when its own name
# (the part after the connection's name) pairs an action word with a thing word.
FALLBACK = (
    ("email", ("send", "reply", "forward", "compose"), ("mail", "email", "emails", "gmail", "outlook",
                                                         "message", "messages", "letter")),
    ("email", ("create", "save", "update", "compose", "write", "new"), ("draft",)),
    ("calendar", ("create", "update", "patch", "delete", "cancel", "move", "reschedule", "respond", "accept",
                  "decline", "add", "book"), ("event", "events", "meeting", "meetings", "invite", "invitation",
                                              "appointment", "appointments", "booking")),
    ("share", ("share", "set", "add", "grant", "manage", "update", "create"), ("permission", "permissions",
                                                                               "access", "sharing", "share")),
    ("file", ("upload", "create", "save", "copy", "update", "write", "put", "move", "import", "replace"),
     ("file", "files", "document", "documents", "doc", "docs", "item", "items", "attachment", "drive")),
)
# A tool whose own name starts with one of these only reads, so the fallback skips it.
READ_WORDS = {"get", "list", "search", "read", "fetch", "find", "query", "download", "check", "count", "describe",
              "view", "show", "watch", "lookup", "browse", "preview", "export"}

# Never counted, even when a piece above matches: chat tools, and tools that
# only touch files on this computer. Remove a word here if you want those held
# for logging too.
IGNORE_TOOLS = ("slack", "discord", "telegram", "whatsapp", "teams_chat", "chat_message", "channel_message",
                "imessage", "sms", "twilio", "filesystem", "desktop_commander", "obsidian")

# Folders that sync to the cloud. A file the AI writes into one of these
# (outside this vault) counts as saved to cloud storage.
CLOUD_FOLDERS = ("/library/cloudstorage/", "/google drive/", "/my drive/", "/shared drives/",
                 "/dropbox/", "/dropbox (", "/onedrive", "/sharepoint", "/box/",
                 "/mobile documents/com~apple~clouddocs/", "/iclouddrive/", "/icloud drive/")

# Calendar tools that make a new event. A new event with nobody else on it is
# time the owner set aside for themselves, so it is not held.
CALENDAR_CREATE = ("create", "quick_add", "add_event", "new_event", "insert_event", "book")
ATTENDEE_KEYS = ("attendee", "guest", "invitee", "participant", "required", "optional")

# In a shell command, only these count as saving into a cloud folder: the
# destination of a copy or move, the path after an output option, or a ">"
# redirect. A path a command only reads (a spreadsheet in Drive) never counts.
COPY_COMMANDS = {"cp", "mv", "rsync", "ditto", "install", "scp", "rclone"}
OUTPUT_OPTIONS = {"-o", "--out", "--output", "--out-dir", "--output-dir", "--dest", "--destination", "--to",
                  "--save-to", "--target"}

# Where a logged line counts.
LOG_DIRS = ("projects", "context", "references", "decisions")
SKIP_DIRS = {".git", ".obsidian", ".claude", ".trash", "outputs", "archives", "node_modules", "__pycache__"}

MARKER = "BRAIN LOG (automatic)"
CHUNK_BYTES = 1 << 20     # the transcript is read backwards, a block at a time
MAX_SCAN_BYTES = 64 << 20 # never read more than this far back
MACHINE_TURNS = {"task_notification", "peer", "scheduled", "system", "loop_wakeup", "schedule_wakeup",
                 "poll_event"}
MACHINE_PREFIXES = ("<task-notification", "<local-command", "<system-reminder")


def vault_root():
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(os.path.dirname(here))
    if os.path.isdir(os.path.join(root, ".claude")):
        return root
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    return env if env and os.path.isdir(env) else os.getcwd()


def tool_key(name):
    """sendEmail, send-email, SEND_EMAIL and send__email all become send_email."""
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    return re.sub(r"_+", "_", re.sub(r"[-\s.]", "_", name.lower()))


def pieces(items):
    return tuple(tool_key(x) for x in items)


EMAIL_KEYS, CALENDAR_KEYS, STORAGE_KEYS, SHARE_KEYS, IGNORE_KEYS = (
    pieces(EMAIL_TOOLS), pieces(CALENDAR_TOOLS), pieces(STORAGE_TOOLS), pieces(SHARE_TOOLS), pieces(IGNORE_TOOLS))


def fallback_kind(name):
    """The tool's own name, after the connection's name: "reply-to-mail-message" is email."""
    own = name.split("__")[-1] if "__" in name else name
    words = [w for w in tool_key(own).split("_") if w]
    if not words or words[0] in READ_WORDS:
        return ""
    ws = set(words)
    for kind, actions, things in FALLBACK:
        hit = ws.intersection(things)
        if ws.intersection(actions) and hit:
            # "send_message" or "create_draft" alone could be a chat or notes tool: email only with a mail hint.
            if kind == "email" and hit <= GENERIC_EMAIL_THINGS and not any(h in tool_key(name) for h in MAIL_HINTS):
                continue
            return kind
    return ""


# Generic action names that many non-email tools also use (chat apps, agent messaging).
# They count as email only when the tool's full name also says it is a mail tool.
AMBIGUOUS_EMAIL = pieces((
    "send_message", "send_draft", "send_reply", "create_draft", "update_draft", "save_draft",
    "reply_to_message", "reply_message", "reply_all", "reply_to_thread", "create_reply",
    "forward_message", "create_forward",
))
MAIL_HINTS = ("mail", "outlook", "inbox", "exchange", "imap", "smtp", "m365", "ms365", "o365", "office365",
              "office_365", "microsoft365", "microsoft_365")
GENERIC_EMAIL_THINGS = {"message", "messages", "draft", "letter"}


def kind_of(name):
    if not name.startswith("mcp__"):
        return ""
    key = tool_key(name)
    if any(w in key for w in IGNORE_KEYS):
        return ""
    email_hits = [w for w in EMAIL_KEYS if w in key]
    if email_hits:
        if any(w not in AMBIGUOUS_EMAIL for w in email_hits) or any(h in key for h in MAIL_HINTS):
            return "email"
    if any(w in key for w in CALENDAR_KEYS):
        return "calendar"
    if any(w in key for w in SHARE_KEYS):
        return "share"
    if any(w in key for w in STORAGE_KEYS):
        return "file"
    return fallback_kind(name)


def has_attendees(inp):
    """True when a calendar call names anyone besides the owner."""
    if not isinstance(inp, dict):
        return False
    for k, v in inp.items():
        lk = str(k).lower()
        if (lk == "to" or any(a in lk for a in ATTENDEE_KEYS)) and v:
            return True
        if isinstance(v, dict) and has_attendees(v):
            return True
    return False


def self_block(name, inp):
    """A new calendar event with nobody else on it: time the owner set aside for themselves."""
    key = tool_key(name.split("__")[-1] if "__" in name else name)
    action = str(inp.get("action") or inp.get("operation") or "").lower() if isinstance(inp, dict) else ""
    creates = any(c in key for c in CALENDAR_CREATE) or (action in ("create", "insert", "add", "new"))
    if action and action not in ("create", "insert", "add", "new"):
        creates = False
    return creates and not has_attendees(inp)


def epoch(ts):
    """ISO time from the transcript ("2026-10-02T17:14:38.313Z") to seconds."""
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})(\.\d+)?(Z|[+-]\d{2}:?\d{2})?", str(ts or ""))
    if not m:
        return 0.0
    y, mo, d, h, mi, s = (int(m.group(i)) for i in range(1, 7))
    t = calendar.timegm((y, mo, d, h, mi, s, 0, 0, 0)) + (float(m.group(7)) if m.group(7) else 0.0)
    tz = m.group(8)
    if tz and tz != "Z":
        sign = 1 if tz[0] == "+" else -1
        digits = tz[1:].replace(":", "")
        t -= sign * (int(digits[:2]) * 3600 + int(digits[2:4]) * 60)
    return t


def lines_backwards(path):
    """The transcript's lines, last first, read a block at a time so a long session stays fast."""
    with open(path, "rb") as fh:
        fh.seek(0, 2)
        pos = fh.tell()
        scanned = 0
        carry = b""
        while pos > 0 and scanned < MAX_SCAN_BYTES:
            step = min(CHUNK_BYTES, pos)
            pos -= step
            scanned += step
            fh.seek(pos)
            parts = (fh.read(step) + carry).split(b"\n")
            carry = parts[0]            # may be the end of a line that starts in the previous block
            for raw in reversed(parts[1:]):
                if raw.strip():
                    yield raw.decode("utf-8", errors="ignore")
        if pos == 0 and carry.strip():
            yield carry.decode("utf-8", errors="ignore")


def text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        for x in content:
            if isinstance(x, dict) and x.get("type") == "text":
                return str(x.get("text") or "")
    return ""


def is_tool_result(e):
    c = (e.get("message") or {}).get("content")
    return isinstance(c, list) and any(isinstance(x, dict) and x.get("type") == "tool_result" for x in c)


def is_owner_message(e):
    """A message the owner typed, not a tool result, a reminder or a background notice."""
    if e.get("type") != "user":
        return False
    if e.get("isMeta") or e.get("isCompactSummary") or e.get("isSidechain") or e.get("isVisibleInTranscriptOnly"):
        return False
    origin = e.get("origin")
    if isinstance(origin, dict) and origin.get("kind") not in (None, "human"):
        return False
    if e.get("turnOrigin") in MACHINE_TURNS or e.get("promptSource") == "system":
        return False
    if is_tool_result(e):
        return False
    c = (e.get("message") or {}).get("content")
    if isinstance(c, list) and not any(isinstance(x, dict) and x.get("type") in ("text", "image") for x in c):
        return False
    text = text_of(c).lstrip()
    if isinstance(c, str) and not text:
        return False
    return not text.startswith(MACHINE_PREFIXES)


def is_earlier_hold(e, line):
    """This check's own earlier message, as the transcript recorded it."""
    if MARKER not in line or e.get("type") == "assistant" or is_tool_result(e):
        return False
    att = e.get("attachment")
    if isinstance(att, dict) and not str(att.get("type", "")).startswith("hook"):
        return False  # a file the AI opened or edited, not the hold itself
    return True


def who(inp):
    """A few words on who or what an action was about, for the message."""
    if not isinstance(inp, dict):
        return ""
    for k in ("to", "toRecipients", "to_recipients", "recipients", "recipient", "attendees", "subject",
              "summary", "title", "name", "file_name", "fileName", "filename", "path", "file_path",
              "destination"):
        v = inp.get(k)
        if not v:
            continue
        raw = json.dumps(v) if not isinstance(v, str) else v
        emails = re.findall(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", raw)
        if emails:
            return ", ".join(sorted(set(emails)))[:80]
        if k in ("path", "file_path", "destination") and isinstance(v, str):
            return os.path.basename(v.rstrip("/"))[:80]
        return re.sub(r"\s+", " ", raw if isinstance(v, str) else str(v)).strip()[:80]
    return ""


def cloud_path(path, root):
    """True when a path is in a cloud-synced folder and not inside this vault."""
    if not path or not isinstance(path, str):
        return False
    if path.startswith("-") and "=" in path:
        path = path.split("=", 1)[1]  # --out=/some/path
    try:
        full = os.path.expanduser(os.path.expandvars(path))
        if not os.path.isabs(full):
            full = os.path.join(os.getcwd(), full)
        full = os.path.realpath(full)
    except Exception:
        return False
    if full == root or full.startswith(root + os.sep):
        return False  # the vault itself may live in a synced folder; its own files never count
    low = full.lower().replace("\\", "/") + "/"
    return any(c in low for c in CLOUD_FOLDERS)


def bash_saves_to_cloud(cmd, root):
    """The file name when a shell command saves into a cloud-synced folder, else ""."""
    if not isinstance(cmd, str) or not any(c in cmd.lower() for c in CLOUD_FOLDERS):
        return ""
    for seg in re.split(r"&&|\|\||[;|\n]", cmd):
        if not any(c in seg.lower() for c in CLOUD_FOLDERS):
            continue
        try:
            words = shlex.split(seg, comments=True)
        except ValueError:
            words = seg.split()
        while words and ("=" in words[0] or words[0] in ("sudo", "env", "nohup", "time", "command")):
            words = words[1:]
        if not words:
            continue
        targets = []
        if os.path.basename(words[0]) in COPY_COMMANDS:
            args = [w for w in words[1:] if not w.startswith("-")]
            if len(args) >= 2:
                targets.append(args[-1])
        for i, w in enumerate(words):
            if w in OUTPUT_OPTIONS and i + 1 < len(words):
                targets.append(words[i + 1])
            elif "=" in w and w.split("=", 1)[0] in OUTPUT_OPTIONS:
                targets.append(w.split("=", 1)[1])
            elif w in (">", ">>") and i + 1 < len(words):
                targets.append(words[i + 1])
            elif w.startswith(">") and len(w.lstrip(">")) > 0:
                targets.append(w.lstrip(">"))
        saved = [t for t in targets if cloud_path(t, root)]
        if saved:
            return os.path.basename(saved[-1].rstrip("/"))[:80] or "a file"
    return ""


def notes_changed_since(root, t0):
    for d in LOG_DIRS:
        for dp, dns, fns in os.walk(os.path.join(root, d)):
            dns[:] = [x for x in dns if x not in SKIP_DIRS and not x.startswith(".")]
            for f in fns:
                if not f.endswith(".md") or f.startswith("_"):
                    continue
                try:
                    if os.path.getmtime(os.path.join(dp, f)) > t0:
                        return True
                except OSError:
                    pass
    return False


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    if not isinstance(data, dict) or data.get("stop_hook_active"):
        return
    tp = data.get("transcript_path")
    if not tp or not os.path.isfile(tp):
        return
    root = os.path.realpath(vault_root())

    # Walk back from the end to the owner's last message (or to this check's
    # own earlier hold, so the same action is never held twice), collecting
    # every outward action on the way.
    emails, events, files, shares = [], [], [], []
    t0 = 0.0
    for line in lines_backwards(tp):
        if MARKER not in line:
            if '"user"' not in line and '"tool_use"' not in line:
                continue
            if '"tool_result"' in line and '"tool_use"' not in line:
                continue                    # a tool's output: never the owner's message, never an action
        try:
            e = json.loads(line)
        except Exception:
            continue
        if not isinstance(e, dict):
            continue
        if is_earlier_hold(e, line):
            t0 = epoch(e.get("timestamp"))
            break
        if is_owner_message(e):
            t0 = epoch(e.get("timestamp"))
            break
        if e.get("type") != "assistant" or e.get("isSidechain"):
            continue
        content = (e.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for c in content:
            if not isinstance(c, dict) or c.get("type") != "tool_use":
                continue
            name = str(c.get("name") or "")
            inp = c.get("input") if isinstance(c.get("input"), dict) else {}
            kind = kind_of(name)
            if kind == "email":
                emails.append(who(inp))
            elif kind == "calendar":
                if not self_block(name, inp):
                    events.append(who(inp))
            elif kind == "share":
                shares.append(who(inp) or "a file")
            elif kind == "file":
                files.append(who(inp) or "a file")
            elif name == "Write" and cloud_path(str(inp.get("file_path") or ""), root):
                files.append(os.path.basename(str(inp.get("file_path"))))
            elif name == "Bash":
                saved = bash_saves_to_cloud(inp.get("command"), root)
                if saved:
                    files.append(saved)
    if not (emails or events or files or shares) or not t0:
        return
    if notes_changed_since(root, t0):
        return

    def listing(items):
        named = sorted({i for i in items if i})
        return " (" + "; ".join(named)[:200] + ")" if named else ""

    parts = []
    if emails:
        parts.append("sent or drafted " + str(len(emails)) + " email(s)" + listing(emails))
    if events:
        parts.append("created or changed " + str(len(events)) + " calendar event(s)" + listing(events))
    if files:
        parts.append("saved " + str(len(files)) + " file(s) to cloud storage" + listing(files))
    if shares:
        parts.append("shared " + str(len(shares)) + " file(s) with someone" + listing(shares))
    reason = (
        MARKER + ": since the owner's last message you " + ", and ".join(parts) + ", but no note under "
        "projects/, context/, references/ or decisions/ changed. Before you finish: add one short dated line "
        "to the note of each person or company involved (context/who-and-what.md says which note; someone new "
        "gets a row there, and a note in projects/ only if there is ongoing work), saying what went out and "
        "what happens next, and update that note's **Status (YYYY-MM-DD):** line if things moved. If a line "
        "for this same thread already exists today, edit it instead of adding another. For a file: put its "
        "link or path on the note as one dated line under ## Files, never the file itself, placed and named "
        "the way context/where-files-live.md says. inbox.md, tasks.md, ideas.md and memory/ do not count. "
        "If nobody but the owner is involved (a note to self, a test), say so in one line instead. Then tell "
        "the owner in one line where you logged it."
    )
    print(json.dumps({"decision": "block", "reason": reason}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
