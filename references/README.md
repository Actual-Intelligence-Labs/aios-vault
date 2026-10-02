# References

*What belongs in `references/`, and what does not. Read this before adding a file here.*

A reference is something already worked out and written so it can be used straight away: how you write, how a tool behaves, the words you use for your own products. Raw material (an email thread, a transcript, an export, a saved web page) is what a reference gets written *from*. It is not a reference itself.

The test: if the AI read this file once, could it act on it correctly without digging through it first? Then it belongs here.

## What belongs here

- **How you write and speak.** [[references/voice]] and [[references/spoken-voice]].
- **How you make judgment calls.** [[references/how-i-decide]].
- **Notes on a tool that took effort to get working.** A short page on what finally worked and what tripped you up, so nobody has to figure it out twice. Name it after the tool, like `stripe-notes.md`. Whether Claude can reach the tool is recorded in [[connections]].
- **Your house terms.** The names of your products and services, how you write prices and dates, words you always use and words you never do.
- **Research that stays useful.** What you learned, in a page, with links to the sources.

## What goes somewhere else

| It is | It goes |
| --- | --- |
| An email thread, transcript, export or saved page | Leave the original where it lives. Write what you learned from it here, or on the note it is about. |
| A meeting | `/meeting-notes` files a summary under the right note. |
| Anything about one client, person or project | That note, in `projects/`. See [[projects/README]]. |
| Steps someone follows for a recurring job | A playbook, in `playbooks/`. See [[playbooks/README]]. |
| A loose thought, to-do or idea | [[inbox]], [[tasks]] or [[ideas]]. Just say it and it gets routed. |
| A file: PDF, deck, spreadsheet, image | Wherever [[context/where-files-live]] says, with a link on the right note. The vault links files, it does not hold them. |
| A password, key, token or account number | Nowhere in this vault. Not in this folder, not in any folder. |

## Naming

Lowercase words joined by hyphens: `pricing-words.md`, `invoice-steps.md`, `stripe-notes.md`. Every file name in the vault is unique, so check nothing else already has the name.

If people call it something else too, add those names to the top of the file so search and the vault's name matching find it:

```yaml
---
aliases: [price list wording, how we write prices]
---
```

## Linking

Link a reference from the notes that use it, like `[[references/voice]]`. A note nothing links to is a note nobody finds, and Obsidian's graph view shows it as a lonely dot.

## Related

- [[playbooks/README]] a playbook is steps you follow, a reference is knowledge you look up
- [[skills-registry]] when the AI uses a reference the same way a second time, it may turn that into a skill
