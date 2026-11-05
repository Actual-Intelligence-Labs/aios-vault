# Memory index

Claude's own memory for this vault: what it has learned about working with the owner. Claude Code loads only the first 200 lines or 25 KB of this file (whichever comes first) when a session starts. Anything past that never loads.

- One line per memory, under the closest heading: `- [Title](file-name.md): a few trigger words`. The detail lives in the memory file, never here.
- One lesson per memory file, kebab-case name, with the date it was learned and why it matters.
- Memory holds how to work: corrections, gotchas and their fixes, how a tool behaves. Facts about the business (who someone is, what was agreed, where a deal stands) live in the vault's notes, and a memory line points at the note. Likes and dislikes about output go in `memory/taste.md`.
- Keep this file under 75 lines and 10,000 characters (Claude Code stops loading at 200 lines or 25 KB). Never move, merge, shorten or reword a line that states a rule, a default, an always or a never, and give every new memory like that its own line here. Only lines that just say where to find a note may be grouped onto a hub note, and only by "optimize my vault" after the owner has seen each one. A hub takes only new lines of that plain kind.
- Never store a password, key, token or account number here.

## How to work with the owner

## Gotchas and fixes

## Tools and connections

## Where things are
