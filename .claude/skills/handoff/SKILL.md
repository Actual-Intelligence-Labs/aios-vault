---
name: handoff
description: Save where the work stopped so the next session picks it up without anyone re-explaining. Use when the owner says "hand this off", "handoff", "let's stop here", "let's pick this up later", "save where we are", "I need to close this", "this chat is getting long", or is ending a session with work still in progress. Writes HANDOFF.md at the vault root; the next session reads it first, then deletes it.
---

# Handoff

## What this is

Work does not always finish in one sitting. The chat gets long, the day ends, something else comes up. A handoff is a short note from this session to the next one: what we were doing, where it stopped, and what comes next.

It lives in one file, `HANDOFF.md`, at the top of the vault folder. When the next session starts, the session pulse (the summary every new session opens with) sees the file and says to read it before anything else. The next session reads it, deletes it, and carries on. Nobody has to re-explain anything.

`HANDOFF.md` is ignored by git, so it is never saved into the vault's history or shared.

## When it runs

- The owner asks: "hand this off", "save where we are", "let's stop here", "this chat is getting long".
- The owner is about to stop while work is half done. Offer it in one line: "Want me to write a handoff so the next session picks this up?"

Not needed when everything is finished and filed. A handoff is for work in flight.

## Step 1: put lasting facts in their real homes first

`HANDOFF.md` is deleted once it is read. Anything that must outlast it goes where it belongs before the handoff is written:

- Something changed status: the note's dated status line, and `tasks.md`.
- A decision was made: `decisions/log.md`.
- A file was made or saved: a dated line in the note's `## Files` section.
- A new person or company came up: their row in `context/who-and-what.md`.
- A to-do the owner still has: `tasks.md`, as a `- [ ]` line.

The handoff then holds only what is not written down anywhere else: the state of the work in progress.

## Step 2: check before you claim

Re-read the files you are about to call done. Re-run whatever showed it working. A handoff that states something stale sends the next session the wrong way, which is worse than no handoff at all.

## Step 3: write HANDOFF.md

At the vault root. If a `HANDOFF.md` is already there (another session left one), do not overwrite it: add your section underneath, with its own heading and time.

Use this shape:

```markdown
# Handoff, 2026-03-14 16:40

Next session: read this whole file first, then delete it. It is a bridge between two sessions, not a record, and it is never committed.

## What we were doing
One or two lines: the goal, in the owner's words.

## Where it stopped
What is done (and checked), what is half done, what has not started.

## Next step
The first concrete thing to do. Then the one after, if it is known.

## Waiting on the owner
Questions or decisions only the owner can settle, numbered, one per line. Or "none".

## Files touched
- `projects/acme-corp.md`: added the March meeting, status updated
- `outputs/acme-proposal.html`: draft v2, pricing table still open

## Watch out for
Anything the next session could trip on: a draft that has not been sent, a file half edited, a step that must not be done twice. Or "none".
```

Rules for the file:

- **No secrets.** No passwords, keys, tokens or account numbers. If one matters, say where it lives, never what it is.
- **Point, do not copy.** If something is already written in a note, link the note instead of repeating it.
- **Keep it short.** A page at most. It is read once.
- Write in the owner's style: `memory/taste.md` holds their rules (out of the box, no em dashes).

## Step 4: tell the owner in one line

> Saved a handoff. The next session in this folder will pick it up on its own, or just say "pick up where we left off".

## The receiving end

When a session starts and `HANDOFF.md` exists (the session pulse says so, or the owner says "pick up where we left off"):

1. Read the whole file before doing anything else.
2. Delete it straight away. Its contents are now in this session, and a stale handoff left lying around misleads the session after this one.
3. Tell the owner in one line what was in flight and what the next step is.
4. If their first message already says what to do, do that. Otherwise ask whether to carry on with the next step.
5. Never commit it, never copy it into a note. Facts that matter were filed in Step 1.

If a session starts with no session pulse at all (for example, the hooks are switched off on this machine), the owner can still say "read HANDOFF.md" and the same steps apply.
