# Memory index

Claude's own memory for this vault: what it has learned about working with the owner. Claude Code loads only the first 200 lines or 25 KB of this file (whichever comes first) when a session starts. Anything past that never loads.

- One line per memory, under the closest heading: `- [Title](file-name.md): a few trigger words`. The detail lives in the memory file, never here.
- One lesson per memory file, kebab-case name, with the date it was learned and why it matters.
- Memory holds how to work: corrections, gotchas and their fixes, how a tool behaves. Facts about the business (who someone is, what was agreed, where a deal stands) live in the vault's notes, and a memory line points at the note. Likes and dislikes about output go in `memory/taste.md`.
- Keep this file under 180 lines and 22 KB. When it gets close, merge duplicates, shorten lines, and drop what is stale.
- Never store a password, key, token or account number here.

## How to work with the owner

## Gotchas and fixes

## Tools and connections

## Where things are
