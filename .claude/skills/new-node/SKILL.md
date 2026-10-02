---
name: new-node
description: Create a new note for a client, company, project or person and wire it into the vault properly, with the other names it goes by, a dated status line, a Files section and its row in the people-and-companies index. Use when the owner says "new client", "we signed X", "start a project note for Y", "make a note for Z", "I have a new engagement", or names a company or person with ongoing work that has no note yet. Also called by /capture when a stray thought has no project home.
---

# new-node

## What this is

A new client, company, project or person shows up. This creates their note and connects it to everything else, so the vault stays a web instead of a pile of loose files.

A "node" is just a note that other notes point at. In Obsidian's graph view, a well-wired node has lines running to it. An orphan node sits alone in the corner, and an orphan note is a note you will never find again.

## When it runs

Any of these, and anything that sounds like them:

- "new client"
- "we signed Acme"
- "start a project note for the spring photoshoot"
- "make a note for Jordan, she's our new bookkeeper"
- "I have a new engagement starting Monday"
- a company or person with ongoing work, named, that has no note yet

It is also called by `/capture` when a stray thought has no project home. In that case, the offer is made first, and the note is only created if the person says yes.

**Not every name needs a note.** Someone mentioned once, or a contact you only need to reach, gets a row in `context/who-and-what.md` (and their channel in `context/contacts.md`) and nothing more. A note is for ongoing work or an ongoing relationship.

## Ask at most three short questions

Ask them **in one batch**, and only the ones you cannot infer from what was already said.

1. Is this a client, a company, a project, or a person?
2. What is it called?
3. One line: what is it?

Infer everything else. If the person already said enough, **skip the questions entirely** and say what was assumed.

> Heard: "we signed Acme Corp for monthly bookkeeping starting next month"
> Assumed: client, called Acme Corp, engagement is monthly bookkeeping. Say so, do not ask.

Never ask a fourth question. Never ask for a status, a budget, a stage, or a category the template can hold as a blank.

## What it does

### 1. Check it does not exist already

A second note for the same thing splits its history in two. Look in three places before creating anything:

- `context/who-and-what.md`, both the **Name** and the **Also called** columns. Match loosely: "Acme Corporation", "Acme" and "Akme" are all the same company.
- `projects/`, by file name and by the title inside each note.
- The whole vault, for the file name you are about to use. File names must be unique across the vault, including `memory/claude/`, because a link like `[[acme-corp]]` has to point at exactly one note:

```bash
find . -name "acme-corp.md" -not -path "./.git/*"
```

If a note exists, do not create a duplicate. Offer to extend it instead.

> There is already a note at `projects/acme-corp.md`. Want me to add this to that one instead of starting a second note?

If the name has an index row but no note of its own (its **Home** is `[[context/contacts]]` or a company note), the new note becomes its home. Step 4 updates the row.

### 2. Work out the file name

Kebab-case, from the real name. Kebab-case means all lowercase with hyphens between words and no punctuation.

- "Acme Corp" becomes `acme-corp.md`
- "Spring Photoshoot (Q2)" becomes `spring-photoshoot.md`
- "Jordan Lee" becomes `jordan-lee.md`

Every node lives in `projects/`, people included. One folder for live things keeps them easy to find.

### 3. Copy the template and fill in what is known

Copy `projects/_TEMPLATE.md` to `projects/<name>.md`.

**The frontmatter** is the small block fenced by `---` lines at the very top. Obsidian reads it as the note's properties, which is what lets you filter and sort notes later.

- `aliases`: every other name this thing goes by. Short forms, nicknames, a person's first name, and any spelling the owner said or dictated that differs from the real one. Write them as one list: `aliases: [Acme, Acme Co, Akme]`. Aliases help Obsidian's search and the vault's name matching find the note. They are not link targets: a link has to use the file name.
- `type`: client, company, project, or person.
- `status`: active.
- `started`: today's date, as `YYYY-MM-DD`.
- `tags`: one or two plain tags, or leave the list empty.

**The title** (the `#` line) is the name the owner actually says: `# Acme Corp`.

**The status line** sits right under the title. Write what is true today, with today's date:

```markdown
**Status (2026-03-14):** New client. Monthly bookkeeping starts next month, scope not signed yet.
```

This is the line that answers "where are we with Acme?" in one glance. Whenever something changes (signed, sent, paused, lost, done, a date moved), it gets rewritten with the new date. Change the `status:` property too when the overall state flips to paused or done.

**The `## Files` section** stays in place, empty, with its format comment. Files are never stored in the vault; this section points at them. One dated line per file:

```markdown
- 2026-03-14 [Signed proposal](https://link-to-the-file)
- 2026-03-14 Kickoff notes: `~/Documents/Clients/Acme/kickoff-notes.pdf`
```

If a file already came up in the conversation (a contract, a proposal, a shared folder), add its line now, and put the client's folder on the `Folder:` line, following `context/where-files-live.md`.

Leave every other placeholder blank. Never invent facts to make the note look finished. A note with four blanks is honest. A note with four confident guesses is a trap.

### 4. Add its row to the index, in the same turn

`context/who-and-what.md` is the index of every person, company, project and tool. A hook reads it on every message, so a row there is how a brand new session knows the name the moment the owner says it. Add one row in the right section:

| The node is | Section |
| --- | --- |
| A person | `## People` |
| A client, vendor, partner or any other organization | `## Companies and organizations` |
| A project, product or internal workstream | `## Projects and products` |

```markdown
| Acme Corp | Acme, Acme Co, Akme | Client. Monthly bookkeeping, starting next month | [[projects/acme-corp]] |
```

- **Also called** repeats the aliases, separated by commas.
- **What** is one line: what it is and how it connects to the owner.
- **Home** is the new note, as a plain path link. Never put a `|` inside a cell; it splits the table.
- If the name already had a row, update that row instead (new Home, any new spellings).
- For each person named alongside the node (the client's contacts, say), add a `## People` row whose Home is this note, unless they already have one.

For a client or project, also add a row to the index table in `projects/README.md`, the at-a-glance board of what is live.

### 5. If it is a client or a company, look them up

- If a website URL was given, fetch it.
- If none was given, try to find one from the company name.
- Fill in what they do, who is there, and how to reach them.

**Say plainly where each fact came from.**

```markdown
- What they do: commercial landscaping for office parks (source: their homepage)
- Main contact: not found
```

If nothing can be found, leave it blank rather than guessing. A wrong industry, a wrong headcount, or a wrong contact name gets repeated in every document produced from that note for months.

### 6. People get their channel recorded

For a person (or the people at a new client), add how to reach them and how they like to be talked to in `context/contacts.md`, if that is known. Skip anything that is not.

### 7. Wikilink it from anywhere it is already mentioned

Search the vault for the name and its aliases. Wherever it appears as plain text in `inbox.md`, `tasks.md`, `ideas.md`, `decisions/log.md`, or another note, turn it into a wikilink: `[[projects/acme-corp]]`.

This is the step that stops the vault from filling with orphans. The graph view should show a line into the new node the moment it exists.

### 8. Log one line in `inbox.md`

At the bottom, under `## Log`:

```markdown
- 2026-03-14 11:20 - Created client note -> [[projects/acme-corp]]
```

## Also handles a person or a workstream

The same procedure works for a node that is not a client company.

**When the node is a person**, drop these template sections, they do not apply:

- `## What we agreed`, the scope, price, and payment schedule block
- `## Taste for this client`

Keep the status line, `## What this is`, `## Who`, `## Files`, `## Open threads`, `## Meetings`, and `## Notes`.

**When the node is an internal workstream** (no client, just a body of work), keep the whole template but leave the client fields blank and note that it is internal.

## Finish with one line

```
Created projects/acme-corp.md and its index row. Linked from projects/README.md and inbox.md. Still blank and worth filling in: main contact, start date, scope.
```

Three parts: what was created, where it is linked from, what is still blank.

## The closing rule

Never fabricate a client's details, a person's role, or a number.

A blank field is fine. Someone will fill it in later, or it will never matter.

A confident wrong fact will get repeated for months, in proposals, in emails, and in every document built on top of that note. It is much harder to unlearn than to leave empty.
