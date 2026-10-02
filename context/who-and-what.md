---
aliases: [who and what, people and companies, index of names]
---
# Who and what

Every person, company, project and tool you are likely to mention, one row each, with the note to read first. A hook (a small script that runs each time you send a message) checks your message against this table. When it finds a name, or a nickname from "Also called", Claude reads that row's Home note before it answers, so you never have to explain who someone is twice.

**How this note stays alive** (Claude does this for you, in the same turn the name comes up):

- A new person, company, project or tool: add a row in the right section.
- A name said, typed or dictated differently than the row: add that spelling to "Also called". Misheard names count.
- One row per thing. If it already has a row, update that row. Never add a second row, and never start a second note, for the same person or company.
- **What** is one line: who or what it is and how it connects to the owner. If it mentions a status, refresh it when the Home note's status changes. The note is the truth.
- **Home** is the note to read first: the thing's own note in `projects/` when it has one, the company's note for someone who works there, `[[context/contacts]]` for a person or company with no note yet, and `[[connections]]` for a tool. Write it as a plain path link, like `[[projects/acme-corp]]`.
- Never put a `|` character inside a cell. It splits the table.
- How to reach each person, and the tone to use, lives in [[context/contacts]].

Example of a finished row, for the shape only: `| Jordan Lee | Jordan, Jordon | Ops lead at Acme Corp, approves every invoice | [[projects/acme-corp]] |`

**Email contacts pass:** not run yet. Once your email is connected, say "import my contacts" and Claude suggests more names from your recent mail. Nothing is added without your yes.

## People

| Name | Also called | What | Home |
| --- | --- | --- | --- |

## Companies and organizations

| Name | Also called | What | Home |
| --- | --- | --- | --- |

## Projects and products

| Name | Also called | What | Home |
| --- | --- | --- | --- |

## Tools and systems

| Name | Also called | What | Home |
| --- | --- | --- | --- |

## Related

- [[context/contacts]] how to reach each person, and the tone to use
- [[projects/README]] the board of live clients and projects
- [[connections]] the tools Claude can reach
- [[context/about-business]] the business these people orbit
