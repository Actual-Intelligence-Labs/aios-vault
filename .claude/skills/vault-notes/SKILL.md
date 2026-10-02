---
name: vault-notes
description: The house rules for notes in this vault, covering where a note goes, how it is named and linked, the status line and Files section every client, project and person note carries, and how to find things. Use before creating, renaming, moving or archiving a note, when adding a person, company, project or tool, when linking a file to a note, and when the owner asks "what do we have on X", "pull up X", "find the note about X", "where did we put X", or mentions Obsidian, wikilinks, backlinks or the graph. For a loose thought use capture; to start a note for a new client, project or person use new-node.
---

# Vault notes

The conventions every note in this vault follows. They are what let the owner find things in Obsidian, and what let a brand new session find them without being told.

Obsidian reads the files on disk and picks up changes as they happen, so writing a file here is writing to Obsidian. There is nothing to import or sync.

All paths below are relative to the vault folder (the folder that holds `CLAUDE.md`).

## Where a note goes

| It is | It goes in |
| --- | --- |
| A client, company, project, product, or a person with ongoing work | `projects/<name>.md`, made with `/new-node` |
| Any person, company, project or tool worth remembering, with or without a note | a row in `context/who-and-what.md` |
| How to reach someone, and how they like to be talked to | `context/contacts.md` |
| Facts about the owner, or about the business | `context/about-me.md`, `context/about-business.md` |
| Where files live and how they are named | `context/where-files-live.md` |
| How the owner writes, speaks or decides; notes on a tool; research worth keeping | `references/` |
| Steps a person follows for a recurring job | `playbooks/` |
| A decision and the reason for it | `decisions/log.md` (add entries, never edit old ones) |
| A like or dislike about the AI's output | `memory/taste.md` |
| Something the AI learned about how to work with the owner | `memory/claude/`, one note per lesson, plus a line in `memory/claude/MEMORY.md` |
| A loose thought | one line in `inbox.md`, then its real home (`/capture` does this) |
| A to-do with no date | `tasks.md`, as a `- [ ]` line |
| An idea with no home yet | `ideas.md` |
| Something finished or out of date | `archives/` (move it, never delete it) |
| A file: PDF, document, deck, spreadsheet, image, recording | not in the vault (see "Files" below) |

If the owner already has their own way of arranging notes, that is their system: follow it. Never reorganize notes unless they ask.

## The index: `context/who-and-what.md`

One row for every person, company, project and tool, in four sections: `## People`, `## Companies and organizations`, `## Projects and products`, `## Tools and systems`. A hook reads this file on every message, so a name in the owner's message pulls up the right note before the AI answers. A row is how a new session knows a name.

```markdown
| Name | Also called | What | Home |
| --- | --- | --- | --- |
| Jordan Lee | Jordan, Jordon | Operations lead at Acme Corp, approves scope | [[projects/acme-corp]] |
```

- **Name**: the real, full name. **Also called**: nicknames, first names, short forms, and every spelling the owner has said or dictated, separated by commas. **What**: one line on who or what it is and how it connects to the owner. **Home**: the note to read first.
- Home is the thing's own note, the company's note for someone who works there, `[[context/contacts]]` for a person or company with no note yet, or `[[connections]]` for a tool.
- A new name gets its row in the same turn it first comes up. A new spelling gets added to Also called in the same turn.
- Never put a `|` inside a cell, because it splits the table. That rules out `[[note|display text]]` links here; write the plain `[[projects/acme-corp]]`.
- The note is the truth. If the row's What line mentions a status, refresh it when the note's status changes.

## Naming

- File names are kebab-case: all lowercase, words joined by hyphens, no punctuation. `acme-corp.md`, `jordan-lee.md`, `spring-photoshoot.md`.
- **File names are unique across the whole vault**, including `memory/claude/`, so a link always points at exactly one note. Check before creating one:

  ```bash
  find . -name "acme-corp.md" -not -path "./.git/*"
  ```

- The title inside the note (the `#` line) is the name people actually say: `# Acme Corp`.
- Other names go in the note's frontmatter, the small block between `---` lines at the very top, as one list:

  ```yaml
  ---
  aliases: [Acme, Acme Co, Akme]
  ---
  ```

  Aliases help Obsidian's search and the vault's name matching. They are not link targets: `[[Acme]]` does not open `acme-corp.md`. A link always uses the file name.
- A note about one moment in time ends with its date: `pricing-research-2026-03-14.md`.

## Linking

- A wikilink is a note's path in double square brackets. This vault writes the path from the vault folder, without `.md`: `[[projects/acme-corp]]`, `[[context/where-files-live]]`. The short form `[[acme-corp]]` also works, because file names are unique. Both show up in Obsidian's backlinks and graph.
- To show different text, add it after a pipe: `[[projects/acme-corp|Acme]]`. Never inside a table cell.
- Every new note links to the notes it belongs with, and they link back, so nothing lands as a lonely dot in the graph. When a name appears as plain text in other notes, turn it into a link.
- Link to a note, never to a folder. A folder of many notes gets one hub note that the rest link to.
- `.claude/` (skills and hooks), `outputs/` and `archives/` are hidden from Obsidian's search and graph (set in `.obsidian/app.json`). Refer to a skill by its name in plain text, like `/capture`, not as a wikilink.

## The status line and the Files section

Every client, company, project and person note carries both. `projects/_TEMPLATE.md` already has them.

**The status line** sits right under the title, with the date it was last true:

```markdown
**Status (2026-03-14):** Proposal sent, waiting on their answer. Follow up Friday.
```

When something changes (signed, sent, paused, lost, done, a date moved), rewrite the line with today's date, and tick off or update any matching item in `tasks.md`, in the same turn. Update the `status:` property in the frontmatter too when the overall state flips (active, paused, done). A stale status line is how a later session gives a confident wrong answer.

**The `## Files` section** has one dated line per file, oldest first:

```markdown
## Files

- 2026-03-14 [Acme proposal v2](https://link-to-the-file)
- 2026-03-14 Kickoff notes: `~/Documents/Clients/Acme/kickoff-notes.pdf`
```

The first shape is for a cloud link, the second for a file on this computer. When a newer version replaces a draft, update the draft's line rather than adding a second; keep the lines for anything that was sent or signed.

## Files live outside the vault

The vault links to files. It never holds them. A file the AI makes or saves goes where `context/where-files-live.md` says, named the way the owner names things, and gets a line in the right note's `## Files` section. If there is no clear home, ask one question with a suggested spot. Never move, rename, or tidy the owner's existing files or folders unless they ask.

Two folders are the exceptions: `brand/logos/` holds the logo images every document uses, and `outputs/` is the workbench for drafts and renders (ignored by git, safe to empty once finals are filed).

## Finding things

1. **A name:** look it up in `context/who-and-what.md` (Name and Also called), then read its Home note.
2. **Anything else:** search the notes, leaving out the hidden and old folders:

   ```bash
   grep -ril "acme" . --include="*.md" --exclude-dir=.git --exclude-dir=.claude --exclude-dir=outputs --exclude-dir=archives
   ```

   Drop `--exclude-dir=archives` when looking for old work.
3. **A file by name:** `find . -iname "*acme*" -not -path "./.git/*"`.
4. **Everything that links to a note** (its backlinks):

   ```bash
   grep -rlE "projects/acme-corp|\[\[acme-corp" . --include="*.md" --exclude-dir=.git
   ```

5. **Read the note before stating anything from it.** Status lines carry dates: if one is weeks old, say how old it is, and check the live source if it is connected.
6. **Not found anywhere:** say so, ask the owner, then add the row (and the note, if there is ongoing work) so the next session knows.

## Changing notes

- **Update in place.** Never start a second note for something that already has one.
- **Facts carry their date and their source**: "2026-03-14, from their email" or "(source: the signed proposal)".
- **Renaming or moving a note** from here does not update the links pointing at it. In the same turn, find every link to the old path (the backlinks search above), update each one along with its index row, and search again to confirm none are left. The same goes for moving a finished note into `archives/`.
- **Prefer a new note over a new folder.** Add a folder only when a group of notes clearly belongs together, such as a large project with many notes, and give it one hub note.
- Write in the owner's style. `memory/taste.md` holds their rules; out of the box its one rule is no em dashes.

## The AI's own memory

`memory/claude/` is where the AI keeps what it learns about working with the owner: one short note per lesson or gotcha. `memory/claude/MEMORY.md` is the index, one line per note. Only its first 200 lines or 25 KB load when a session starts, so keep it under 180 lines and 22 KB: merge duplicates and shorten lines when it gets close.

Business facts (who someone is, where a deal stands, what was agreed) belong in the vault's notes, not in memory. A memory note holds the how-to and points at the note that holds the facts.
