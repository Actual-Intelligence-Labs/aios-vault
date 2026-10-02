---
name: map-files
description: Learn how the owner already organizes their files and write it down as the file map, context/where-files-live.md, so every file Claude makes or saves lands in the right place, named their way, with a link on the right note. Use when the owner says "map my files", "learn my folders", "where do my files live", "redo my file map" or "I connected my Google Drive" (or OneDrive, SharePoint, Dropbox), when setup reaches the files topic, and when update-vault drafts the map for an older vault. Looks at folder and file names only, never inside files, and never moves, renames or deletes anything unless the owner asks.
---

# Map my files

Learn the owner's filing system by looking, write it down as a map, and follow it from then on.

## The one rule

Never move, rename, delete, merge or tidy the owner's files or folders, on this computer, in cloud storage or in this vault, and never create a new top-level folder, unless the owner asks for that change. The job is to learn their system and follow it, not to improve it. A system you would not have chosen is still their system. The vault's own folders count too: never reorganize the notes either.

## When it runs

- **Setup reaches "Where your files live"** (the onboard skill sends you here): run in setup mode, described in each step below.
- **The owner asks:** "map my files", "learn my folders", "redo my file map".
- **A drive or file tool was just connected** ("I connected my Google Drive"): map that place and take it off the "Not reachable yet" list.
- **update-vault** is drafting the map for a vault set up with an older version: setup answers already in `intake.md` and the storage tools in `connections.md` count as answers, so ask only what is still unclear.

Not for saving one file (that is just following the map's rules), or for "where is the Acme contract?" (search the map and the notes first).

## Step 1. Look, names only

**What you may do:** list folder and file names, and dates when they help. **What you never do:** open, read, preview, search inside, copy or download any file. Never touch files that are stored only in the cloud (iCloud's "Optimize Mac Storage", OneDrive's Files On-Demand, Dropbox online-only files, Google Drive streaming): listing their names is fine, opening one downloads it.

Before you look, tell the owner in one line. This is not a question:

> I'm going to look at how your folders are organized, names only, never what's inside a file. Your computer may ask whether VS Code can see Documents, Desktop or Downloads: OK lets me look, and Don't Allow is fine too, I'll just ask you about that folder instead.

**Where to look, in this order:**

1. **Connectors available in this session** for Google Drive, OneDrive, SharePoint or Microsoft 365, Dropbox, or Box. Some tools only show up after you search your tools for the service's name. Use their list or search tools for folder names: the top level and two levels down, plus shared drives and "Shared with me".
2. **Cloud folders synced to this computer:**
   - Mac: everything inside `~/Library/CloudStorage/` (Google Drive, OneDrive, Dropbox and Box each sync there; synced SharePoint libraries show up as `OneDrive-SharedLibraries-<company>`), plus `~/Dropbox` and iCloud Drive at `~/Library/Mobile Documents/com~apple~CloudDocs`.
   - Windows: `OneDrive`, `OneDrive - <company>`, `Dropbox` and `Google Drive` inside the home folder, and a folder named for the company that holds synced SharePoint libraries. Through WSL the home folder is `/mnt/c/Users/<name>/`.
   - Linux: `~/Dropbox`, or wherever the owner says.
3. **The main local folders:** Documents and Desktop, and the top level of Downloads. Plus any folder the owner names.

**How deep:** two or three levels. Use a command that prints names and stops early, and skip hidden folders, app bundles, photo libraries and code dependencies:

```sh
find "$HOME/Documents" -maxdepth 3 \( -name '.*' -o -name node_modules -o -name '*.app' -o -name '*.photoslibrary' \) -prune -o -print 2>/dev/null | head -n 400
```

Use `-maxdepth 2` for the Desktop and `-maxdepth 1` for Downloads. On a Mac, never walk `~/Library` itself; look only inside `~/Library/CloudStorage` and the iCloud Drive folder. If a folder answers "Operation not permitted", the owner declined access: mark it, do not retry.

**Microsoft Teams:** files shared in a Teams channel live in that team's SharePoint document library (the channel's Files tab). Files shared in a one-to-one or group chat live in the sender's OneDrive, in a folder called `Microsoft Teams Chat Files`. So "it's all in Teams" means mapping those two places.

**A place you cannot reach** (a cloud drive with no connector and no synced folder, a work laptop, a shared drive at the office): never guess. Put it under "Not reachable yet" with what the owner said about it and how to finish: connect that service's connector, or sync it to this computer with the provider's desktop app, then say "map my files". If they want it mapped now, a screenshot of the folder or a quick description works, and you map from that.

**What to notice:**

- How work is split: by client, by project, by year, by kind of file, or a mix, and at which level.
- Where drafts live and where finals live (a Drafts folder, "final" in names, a Sent folder, a separate drive).
- How names are written: dates (`2026-03-14`, `03.14.26`, `March 2026`), versions (`v2`, `rev B`, `final`), client names, separators.
- Where particular things go: proposals, contracts and their signed copies, invoices and receipts, client deliverables, brand files, meeting recordings and transcripts, spreadsheets, photos and video, templates.
- Money files only as places. Never open one.

## Step 2. Write the map

Write `context/where-files-live.md`. Keep its section headings and its "The rules" section exactly as they are, and fill in the rest:

- **The status line,** under the title: `**Status (YYYY-MM-DD):** mapped from <places>; <places> not reachable yet.`
- **Where things go:** one line per kind of file, each naming a real folder, for example ``- Proposals: `Clients/<client>/Proposals` in Google Drive``. Cover what the owner actually has, plus the files this vault makes:
  - designed PDFs from the `pdf` skill: built in `outputs/`, and the final goes where client deliverables go;
  - Sheet Geek's guides and data dictionaries: the folder they should go to (often the folder of the client or project the spreadsheet belongs to);
  - meeting recordings and transcripts: where the meeting tool saves them (the summaries go on the project note).
  If a kind of file has no clear home, say so on its line and add a question with your best guess.
- **Locations:** each place with its real path or link and its shape, two or three levels deep. Summarize big folders instead of listing them ("about 40 client folders, one per client, named by company").
- **Naming:** each naming rule the owner actually follows, with two or three real examples copied from names you saw.
- **Questions for {{YOUR_NAME}}:** what you could not tell by looking, each with your best guess. If the heading still says `{{YOUR_NAME}}` and `context/about-me.md` has the owner's name, use their first name.
- **Not reachable yet:** each place you could not see, and how to finish.

**Secrets.** Never copy a password, key, account number or card detail into the map, even when it is part of a file or folder name. If a name suggests a file of passwords or keys, leave it out of the map and tell the owner in one line where it is, so they can deal with it.

Link the map to the notes it touches: a folder that belongs to a client with a note gets `[[projects/<note>]]` next to it. If a storage service you mapped has no row in `connections.md`, add one (Used for: files).

## Step 3. Check it with the owner

Show a short summary, about five to eight lines: the places you mapped, how their work is organized, their naming habits, and what you could not reach. Then: "Anything wrong?" That read-back does not count as a question.

Then ask only what you could not answer by looking, each with your best guess, so a yes settles it:

> I think signed contracts go in Clients/<client>/Contracts. Right?

- **Setup mode:** at most three of these, one per message. They count toward setup's 15 questions. Anything left stays under "Questions for" in the map, for later.
- **Asked directly:** a few at a time, in one message.

Write each answer into the map. Then the map is the reference: check it before asking the owner where anything goes.

## Step 4. Only when there is no system at all

Offer anything only when all four of these are true for every place you could see:

1. **Work files sit loose.** Most of the work files you saw (documents, spreadsheets, proposals, invoices, decks; not screenshots, installers or personal photos) are directly on the Desktop, in Downloads, or at the top level of Documents or a cloud drive, rather than in folders.
2. **Nothing is grouped.** No folder you saw is named for a client, a project, a year or a kind of file.
3. **No naming pattern.** The file names follow no consistent pattern: no dates, client names or version marks used the same way.
4. **Nowhere else.** The owner has not mentioned another place where they keep work in order, such as a work drive or a project tool.

If any one of these is false, or you are not sure, they have a system. Follow it, and never offer to change it. If the owner asks ("help me organize my files", "clean up my Downloads"), the test does not apply: do what they ask, with the same show-first rules below.

When the test passes, make two separate offers, once. In setup mode they wait for the readout at the end.

**(a) A starter layout for new files:** `Clients`, `Projects`, `Company`, `Brand`, `Content`, `Research`, `Archive`, created inside one place the owner picks (for example Documents, or their cloud drive). Show the folder list and exactly where it would go. Create it only on their yes. Their existing files stay where they are. Then point "Where things go" at the new folders.

**(b) A cleanup of existing files:** first, a move list, one line per file as `from -> to`, grouped by destination, with anything unclear left where it is. Nothing moves until they say yes to that list.

- Moves only. Nothing is renamed unless they ask, and nothing is ever deleted.
- Moves stay within one drive. Moving between this computer and a cloud drive is really a copy and a delete, so leave those out unless they ask.
- Save the list to `archives/file-cleanup-YYYY-MM-DD.md` before moving anything, so every file can be found or moved back.
- After moving, list the destination folders to confirm each file arrived, update any `## Files` line in the notes that pointed at a moved file, and update the map.

Write the outcome into the map's status line ("Starter layout and cleanup offered 2026-03-14, declined"), so neither is offered again unasked.

## From then on

The map's own rules apply to every file Claude makes or saves: put it where the map says, named the owner's way; no clear home, ask once with a suggested spot; then a dated line in the right note's `## Files` section. When the owner changes their folders, update the map. Never change their folders to match the map.

## Running it again

"Map my files" again, or a newly connected drive: copy the current map to `archives/where-files-live-YYYY-MM-DD-HHMM.md` first (in setup mode, setup's own backup covers this), look again (names only), compare with the map, change only what is different, keep every answer the owner already gave, and say in one line what changed.

## Sign-off

One line: "Mapped <places>. Not reachable yet: <places>. <N> questions left in the map." Drop the parts that are empty.
