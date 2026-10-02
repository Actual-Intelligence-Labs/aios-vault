---
aliases: [where files live, file map, filing system, where does this go, where should this go, where do files go]
---
# Where files live

How {{YOUR_NAME}} keeps files, written down so that every file Claude makes or saves lands in the right place, named the right way, with a link on the note it belongs to. The map follows the owner's own system. It never changes it.

**Status:** not mapped yet. Setup fills this in by looking (folder and file names only, never what is inside a file). Say "map my files" any time, and again after you connect a new drive.

## The rules

Every time a file is made or saved:

1. **Follow the owner's system.** Never move, rename, delete, merge or tidy their existing files or folders (on this computer, in cloud storage, or in this vault), and never create a new top-level folder, unless the owner asks for that change. A system you would not have chosen is still their system.
2. **Put it where "Where things go" says, named the way "Naming" says.** If the right home is obvious, just do it. If it is not, ask once and suggest a spot, then write the answer into this map so it is never asked again.
3. **The vault links files, it never holds them.** The only exceptions are logo files in `brand/logos/` and build scratch in `outputs/`. Add one dated line to the `## Files` section of the client, project or person note the file belongs to (add the section if the note has none):
   - a cloud file: `- YYYY-MM-DD [Title](link)`
   - a file on this computer: ``- YYYY-MM-DD Title: `path` ``
4. **A new version is a new file**, numbered the way the owner numbers versions. Never overwrite a file that was sent or signed.
5. **One copy per file.** If the file is already where it belongs, link it instead of saving it again.
6. **Drafts can stay wherever the owner keeps work in progress.** The final goes to the home this map names.
7. **Never file a secret.** No password, key, account number or card detail goes into any file or folder, and none goes into this map, even when it is part of a file name.
8. **Look here first.** Check this map and the notes before asking the owner where something is.
9. **The map follows the owner.** When they change their folders, update this map to match. Never change their folders to match the map.

A check runs at the end of every reply (the brain log hook): if a file went to cloud storage and no note changed, it holds the reply once until the link is on the right note.

## Where things go

One line per kind of file, each naming a real folder. Filled in from what setup saw, then from the owner's answers.

_Not mapped yet._

## Locations

Every place the owner keeps files, with its real path or link and its shape, two or three levels deep.

_Not mapped yet._

## Naming

How the owner names files and folders, each rule with two or three real examples copied from names that exist.

_Not mapped yet._

## Questions for {{YOUR_NAME}}

What the map could not answer by looking, each with a best guess, so a short reply settles it.

_None yet._

## Not reachable yet

Places the owner uses that Claude could not see from here (a cloud drive with no connector, a work laptop, a shared drive), each with how to finish: connect it or sync it to this computer, then say "map my files".

_None yet._

## Related

- [[context/who-and-what]] which note each client, project and person lives in
- [[connections]] the drives and tools Claude can reach
- [[projects/README]] the notes whose `## Files` sections point at these files
