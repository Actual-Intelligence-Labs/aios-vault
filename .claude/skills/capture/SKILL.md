---
name: capture
description: Brain inbox. Takes a loose thought, half-formed idea or messy dictated to-do and files it in exactly one place (a calendar event, a project note, the to-do list, or done on the spot), using the right name for every person and company and adding an index row for anyone new. Runs automatically when a message is a loose thought with no clear instruction, and is forced by an "inbox:" or "capture:" prefix. Never hijacks a message that already carries a clear instruction or question.
---

# capture

## What this is

You say a half-formed thought out loud, or type it messily, and it ends up in the right place.

No command. No filing decision. You do not have to know where anything lives.

You say: "oh I should probably follow up with the accountant about the new printer quote at some point"

The vault does the rest: cleans up the wording, decides that this is a no-rush to-do, adds it to `tasks.md`, logs one line in `inbox.md`, and tells you in one sentence what it did.

## When it runs

Automatically. A hook (a small script that runs before the AI answers) watches every message. If a message looks like a loose thought, idea, or to-do with no other clear instruction, the hook tells the AI to run this routing instead of just replying "got it."

You can also force it. Start a message with `inbox:` or `capture:`.

```
inbox: call the landlord about the lease renewal
```

When the prefix is used, strip it before doing anything else. Route the rest of the message normally.

## When it must NOT run

A message that already carries a clear instruction or a clear question runs normally. Answer it. Do the thing. Do not file it.

**Capture these (loose thoughts, no instruction):**

- "we should really put together a case study for that last project"
- "note to self, the invoice template is missing the payment terms line"
- "I keep forgetting the client prefers phone calls over email"
- "idea: a short weekly email to past customers"
- "need to renew the domain before it lapses"
- "remind me to call the accountant Thursday"
- "don't let me forget the quote for the new client"

**Do NOT capture these (clear instruction or question):**

- "draft an email to the client about the delay"
- "what did we decide about pricing?"
- "read `projects/acme-corp.md` and summarize it"
- "fix the typo in the second paragraph"
- "make me a one-pager on the new offer"

**The test: is the message asking you to produce or change something in this turn?** Then it is an instruction. Do it. Otherwise it is a thought, and a thought gets filed.

"Draft the email" wants an email now. "Fix the typo" wants an edit now. Both are instructions.

**"Remind me", "note that", "don't let me forget", and "need to" are not instructions**, even though they open with a verb aimed at you. They are asking for something to be *held*, which is exactly what filing it does. Route them.

The hook that starts this skill uses the same line. It stays quiet on questions, on slash commands, on thanks and short answers, on messages that open with a produce-or-change verb, on phrases another skill listens for ("map my files"), and while setup is asking its questions. It deliberately does not treat "remind", "note" or "don't forget" as instructions.

If it is genuinely ambiguous, ask exactly ONE short question, then act. Do not ask two. Do not ask for a category. Ask the one thing that changes the routing.

> Ambiguous: "the pricing thing"
> Ask: "File this as a note on a project, or is it something you want to do?"

## Clean up the input first

Dictated input arrives rough. Transcription noise, wrong homophones, run-on sentences, no punctuation, filler words.

Fix the obvious:

- Add punctuation and sentence breaks.
- Fix clear homophone errors ("there" for "their", "to" for "two").
- Drop filler ("um", "uh", "like", "you know").
- Fix mangled names, using the index (next section).

Do not:

- Editorialize. The person's own words and meaning survive.
- Expand a short thought into a paragraph. A one-line thought stays one line.
- Add reasoning, framing, or next steps they did not say.
- Change a hedge into a commitment. "Maybe we should" is not "we will".

## Names first

Dictation mangles names, and a misspelled name files a thought in the wrong place. Before routing, check every person, company, project or tool the thought mentions.

1. Look it up in `context/who-and-what.md`, the vault's index of people, companies, projects and tools. Match against both the **Name** and the **Also called** columns, and be forgiving: "Akme" is probably Acme Corp, "Jordon" is probably Jordan.
2. Found it: use the canonical name (the **Name** column) in everything you write, and read its **Home** note if the routing depends on it. If the owner said or dictated it differently, add their spelling to that row's **Also called** cell in the same turn, so it matches next time.
3. Not in the index: search the vault before deciding it is new (`grep -ril "the name" . --include="*.md" --exclude-dir=.git --exclude-dir=.claude`). It may sit in a note nobody indexed. If it does, add the row now.
4. Genuinely new: it gets a row (see "A new person or company" below).

The index row is bookkeeping, not a second home for the thought. It always gets written for a new name, alongside whatever home the thought itself gets.

## Pick exactly ONE home

One thought, one home. Never file the same thought in two places. Pick the strongest signal and commit.

### Route 1: time-bound, or needs a block of focus, goes on the calendar

**Signals:** a date, a day name, a time, a deadline, "by Friday", "before the call", "tomorrow", "next week", "this needs a couple of hours", "I need to sit down and do X".

**What to do:**

1. Infer the time from the words. "Thursday morning" means Thursday at 9:00 local.
2. If no time is given, choose a sensible near-future slot inside working hours (roughly 9:00 to 17:00, weekdays) and **say out loud which slot was chosen**. The person must be able to correct it in one reply.
3. Default duration is one hour unless the words say otherwise.
4. **Anchor the timezone explicitly.** Pass the event with the local timezone attached so a stated hour lands at that hour locally, not in UTC. A 9am block that shows up at 4am is a broken feature. If the local timezone is not known, check `context/about-me.md`; if it is not there, ask once and record it there.

**If no calendar is reachable yet** (no calendar in `connections.md` that Claude can reach): say so plainly, in one line, and put the item in `tasks.md` instead. Do not pretend an event was created. Do not silently drop it.

> No calendar is connected yet, so this went to [[tasks]] instead.

A block like this, with nobody else invited, is a note to self: the end-of-reply brain log does not hold it, so the one-line reply stands.

### Route 2: a note, fact or idea about something that already has a note

**Signals:** it names a client, a company, a person, a project, or a piece of work that already has a note. The **Home** column in `context/who-and-what.md` says which note. Search `projects/` too, since a brand new note may not be indexed yet.

This route is for things to *know* about the work. A to-do the owner has to *do* goes to `tasks.md` (or the calendar, if it has a date), with a link to the note.

**What to do:**

1. Open the matching note. (If the Home is `[[context/contacts]]`, the person has no note of their own: a one-off fact goes in their row's **What** cell in the index. If facts about them keep coming, offer `/new-node`.)
2. Append a dated bullet under its `## Notes` heading (create the heading if it is missing):

```markdown
## Notes

- 2026-03-14 Client prefers phone over email for anything time sensitive.
```

3. **If the thought changes where things stand** (signed, sent, paused, lost, done, a date moved), also rewrite the note's status line near the top with today's date, `**Status (2026-03-14):** ...`, and tick off any matching item in `tasks.md`. A stale status line is how a later session gives a wrong answer.
4. If **no note fits**, say so and OFFER to start one with `/new-node`. Never create a project note silently. A vault full of half-empty auto-generated notes is worse than no notes.
5. Only if the offer is declined does the thought go to `ideas.md`.

### Route 3: small and doable right now

**Signals:** it is a small concrete piece of work that can be finished in this turn. Draft an email. Make a list. Pull a number out of a file. Write three subject line options.

**What to do:** just do it. Then show the result and say where it was filed.

Anything that leaves the vault (an email, a message, a post, a push) is drafted, never sent. Show the draft. The person fires it.

## Edge routes

Do not force-fit these into the three main routes.

| The thought is | It goes to |
| --- | --- |
| A decision that got made, and why | `decisions/log.md` |
| A stated like or dislike ("I hate that font", "always lead with the number") | `memory/taste.md`, as a scoped rule with its principle |
| A to-do with no deadline and no urgency | `tasks.md`, as one `- [ ]` line (format below) |
| A durable fact about you or the business | `context/about-me.md` or `context/about-business.md` |
| A durable fact that belongs to one named project, client or person | that note (Route 2), not `context/` |
| A new person or company | a row in `context/who-and-what.md`, always (see below) |
| How to reach someone, or how they like to be talked to | `context/contacts.md` |
| Where a particular file is ("the signed contract is in the Acme folder") | a dated line in that note's `## Files` section |
| How you organize files in general | `context/where-files-live.md` |
| An idea with no home yet | `ideas.md` |

**The `tasks.md` format.** One line per to-do, under `## Open`, in the owner's words, with the date it was added and a link if it belongs to something:

```markdown
- [ ] Send Acme the revised quote (added 2026-03-14) [[projects/acme-corp]]
```

When it is done, tick the box (`- [x]`), add the date it was done, and move the line under `## Done`. The session pulse (the summary a new session starts with) lists the open `- [ ]` lines, so this exact format is what makes a to-do resurface. Keep anything else out of `## Open`.

**A new person or company.** Every new name gets a row in `context/who-and-what.md`, in the right section (`## People`, `## Companies and organizations`, `## Projects and products`, or `## Tools and systems`), in this shape:

```markdown
| Sam Rivera | Sam | Owns a bakery, met at a networking event 2026-03-14, might want a quote in the spring | [[context/contacts]] |
```

- **Name** is the real, full name. **Also called** holds nicknames, first names, and any spelling the owner said or dictated, separated by commas. **What** is one line: who they are and how they connect to the owner. **Home** is the note to read first.
- **Home** is their own note if they have one, the company's note if they work somewhere that has one (`[[projects/acme-corp]]`), or `[[context/contacts]]` if neither.
- Never put a `|` inside a cell. It splits the table. That rules out `[[note|display text]]` links in the index; write the plain `[[projects/acme-corp]]`.
- If a channel or tone came with it ("she only answers texts"), add that to `context/contacts.md` too.
- A full note of their own is only for someone with ongoing work or an ongoing relationship. Offer it (`/new-node`), never create it silently. A name mentioned once needs the row and nothing more.

**Taste entries carry a scope tag and their principle.** The exact format, which `memory/taste.md` also states, is one line:

```markdown
- [scope] the thing -> the principle behind it
```

The scope tag is `[global]`, `[client: NAME]`, or `[doc: TYPE]`. It is required. Without it, a rule set for one client leaks into every other client's work. The principle matters as much: it is what makes the rule generalize to a case nobody anticipated.

```markdown
- [doc: proposal] Lead with the outcome, not the process -> the buyer is paying for a result, and the method only gets interesting once they believe the result
```

## The calendar versus tasks tiebreaker

This is the routing mistake that happens most, so read it twice.

**Default anything with no deadline and no urgency to `tasks.md`.**

Cues that mean `tasks.md`, not the calendar:

- "sometime"
- "no rush"
- "at some point"
- "eventually"
- "I should probably"
- the total absence of any date, day, or deadline

Only use the calendar when there is real time pressure, or when the person would genuinely block time for it today or this week.

**Never fabricate a calendar slot for a someday item.** A calendar full of invented blocks for vague intentions makes the calendar useless, and a useless calendar gets ignored, and then the real blocks get ignored too.

## Several thoughts at once

Dictation often carries three things in one breath.

> "need to send the invoice, also the new client wants a kickoff call next week, and I think we should raise prices"

Split into one intent each. Route each independently.

1. Send the invoice, no date, no urgency, goes to `tasks.md`.
2. Kickoff call next week, time-bound, goes to the calendar.
3. Raise prices, an idea with no project home, offer `/new-node` or file to `ideas.md`.

Then give **ONE combined sign-off**, not one per item. Three separate "Did X. Filed here" lines is noise.

## Always

1. Log exactly one line in `inbox.md`, as the last line of the file (under the `## Log` heading), in this format:

```markdown
- 2026-03-14 09:40 - Client prefers phone over email -> [[projects/acme-corp]]
```

Format: `- YYYY-MM-DD HH:MM - summary -> where it went`. New lines go at the bottom, because the session pulse shows the last few.

2. Wikilink any project, company or person that has a note, so it connects in Obsidian's graph view instead of sitting there orphaned. A wikilink is double square brackets around a note's path: `[[projects/acme-corp]]`.

3. Write in the owner's style. `memory/taste.md` holds their rules; out of the box its one rule is no em dashes.

4. End with a single line:

```
Did X. Filed here: <path>
```

That is the whole reply. No preamble, no restating what was said, no summary of the routing logic.

5. **Speed over polish.** Capture is a reflex, not a project. If the routing is 80 percent right and took one second, that beats 100 percent right after three clarifying questions. The person can correct it in one reply, and the correction itself is captured.

## Worked examples

**Input:** `"uh we should probably ping the acme people about the phase two scope before the end of the month"`

**Action:** names first: "acme" matches Acme Corp in the index. A deadline is present (end of the month), so the calendar gets the block and nothing else does. No note append, no `tasks.md` line.

**Reply:**
```
Did it. Booked a 1-hour block Thursday 10:00 local to scope phase two with [[projects/acme-corp]]. Filed here: calendar + inbox.md
```

**Input:** `"jordon at akme says theyre pushing the launch to may"`

**Action:** names first: "akme" is Acme Corp (its Also called cell lists Akme) and "jordon" is Jordan Lee, whose Home is the Acme note. A fact about live work, so Route 2: a dated bullet under `## Notes` in `projects/acme-corp.md`. The launch date moved, so the status line gets rewritten with today's date too. "Jordon" goes into Jordan's Also called cell.

**Reply:**
```
Did it. Noted the launch moving to May and updated the status on Acme Corp. Filed here: projects/acme-corp.md
```

**Input:** `"met sam rivera at the networking thing, runs a bakery, might want a quote in the spring"`

**Action:** names first: no row, and a vault search finds nothing. New person: a row under `## People` in `context/who-and-what.md` with Home `[[context/contacts]]`. It is a possible lead with no work yet, so offer a note rather than make one.

**Reply:**
```
Did it. Added Sam Rivera to your people, no note yet. Want one to track the lead? Filed here: context/who-and-what.md
```

**Input:** `"capture: I really do not like when a deck opens with an agenda slide"`

**Action:** strip the prefix, this is a stated dislike. Goes to `memory/taste.md` as `- [doc: deck] Do not open with an agenda slide -> the first slide should earn attention, not spend it on housekeeping`.

**Reply:**
```
Did it. Added a taste rule about opening slides. Filed here: memory/taste.md
```

**Input:** `"note to self renew the domain sometime"`

**Action:** "sometime" means no urgency. `tasks.md`, not the calendar: `- [ ] Renew the domain (added 2026-03-14)`.

**Reply:**
```
Did it. Added to your to-do list, no date. Filed here: tasks.md
```
