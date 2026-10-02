# Projects

This folder holds your **nodes**.

## What a node is

A node is **one markdown note for one live thing that has its own context**.

A client. A company you work with. A project. A product. A recurring engagement. A person you deal with often.

Not a folder. One file. If you find yourself making a folder for a client, stop. Make one note instead. (The client's actual files, such as contracts and proposals, stay wherever you keep files. The note links to them.)

## Why nodes exist

Two reasons, and they are both practical.

1. **The AI gets a place to put what it learns.** Every time you talk about that client, something true comes out: a price, a deadline, a name, a preference. Without a node, that fact evaporates when the session ends. With a node, it lands in a file the AI reads next time.
2. **You get one page to read before a call.** Open the note. Scan it. You are caught up in thirty seconds. No hunting through email.

## What every node has

`/new-node` sets all of this up for you, from `_TEMPLATE.md`.

- **Other names it goes by**, in the frontmatter (the small block between `---` lines at the top): `aliases: [Acme, Acme Co]`. Short forms, nicknames, and the spellings you tend to dictate. Search and the vault's name matching use them.
- **A dated status line** right under the title: `**Status (2026-03-14):** Proposal sent, waiting on their answer.` Whenever something changes, this line gets rewritten with the new date, so "where are we with Acme?" always has a current answer.
- **A `## Files` section**: one dated line per file, with a link or the path on your computer. The files themselves stay where you keep files (see [[context/where-files-live]]). The note only points at them.
- **A row in [[context/who-and-what]]**, the index of everyone and everything the vault knows. A hook reads it on every message, so when you mention Acme in a brand new session, the AI already knows which note to open.

## Naming rule

File names are **kebab-case** and match the real name.

- Kebab-case means all lowercase, words joined by hyphens, no spaces.
- `Acme Corp` becomes `acme-corp.md`
- `Q4 Brand Photoshoot` becomes `q4-brand-photoshoot.md`
- `Jordan Lee` becomes `jordan-lee.md`

Every file name in the vault is unique, so a link always points at exactly one note. Stick to this. Consistent names are what make links work without thinking.

## Wikilinks, in one example

A **wikilink** is a link between two notes. You write it with double square brackets around the note's path:

```
[[projects/acme-corp]]
```

Write that anywhere in the vault (a task, a decision, a meeting summary, an idea) and it becomes a live link to `projects/acme-corp.md`. The short form `[[acme-corp]]` works too.

That single mechanic is what turns a pile of files into a system:

- A meeting summary in the node says `[[projects/jordan-lee]]`
- A decision in [[decisions/log]] says `[[projects/acme-corp]]`
- A to-do in [[tasks]] says `[[projects/acme-corp]]`

All three now point at the same client. Open the node and look at the **backlinks** panel, which Obsidian shows at the bottom of a note, listing every other note that links to it. You see every place that client was mentioned, in one list, without searching.

In Obsidian, the **graph view** (the constellation-looking icon in the left sidebar) draws these links as a picture. Dense clusters are where your real work is. Lonely dots are things you started and dropped. It is a surprisingly honest read on your own attention.

## Making one

Ask for a new node and the AI creates it correctly wired, using the `/new-node` skill: right file name, frontmatter filled in, status line dated, index row written, links back to the vault already in place. You do not have to remember the format.

Say it plainly, for example: "make a node for Acme Corp, new client, monthly bookkeeping."

A node does not have to be a client. Make one for:

- a **project** with no outside client (an internal build, a rebrand)
- a **company** you deal with that is not a client (a supplier, a partner)
- a **person** you work with constantly (a contractor, a partner, a key contact)
- a **workstream** that keeps coming back (hiring, monthly reporting, content)

If it has its own context and it keeps coming up, it earns a node. Someone you only need to reach does not: a row in [[context/who-and-what]] and their channel in [[context/contacts]] is enough.

## Index

Keep this table current. It is the fastest map of what is live right now.

| Project | What it is | Status |
| --- | --- | --- |
<!-- Example row (write the link without the backticks): | `[[projects/acme-corp]]` | Monthly bookkeeping | active | -->

## When a project is done

Rewrite its status line one last time, then move the note to `archives/`. **Do not delete it.** Say "archive Acme" and the AI does both, and updates every link that pointed at the old place.

Finished work is the most useful reference you own: what you scoped, what you charged, what went wrong, how you fixed it. That is what makes the next proposal fast. Obsidian hides `archives/` from its graph and search to keep the view clean, but every file is still there, and the AI looks in it when you ask about old work.
