# How it works

The idea fits in a few sentences.

Everything Claude needs to know about you and your work lives in plain files on your own disk. Claude reads those files instead of asking you again, and writes back to them whenever it learns something, so tomorrow's session starts where today's stopped. A handful of small automatic checks make sure that reading and writing actually happens, every time, without you remembering to ask.

The rest of this page is the reference you come back to when you are not sure what a file is for or why something happened.

---

## Every file, what it is for, and when it changes

| File or folder | What it holds | Who writes it | When it changes |
| --- | --- | --- | --- |
| `README.md` | The pitch and the quick start. | Nobody. It ships with the kit. | Only when the kit itself changes. |
| `INSTALL.md` | Step by step setup for a first-timer, plus troubleshooting. | Nobody. Ships with the kit. | Only when the kit itself changes. |
| `HOW-IT-WORKS.md` | This page. The mental model. | Nobody. Ships with the kit. | Only when the kit itself changes. |
| `LICENSE` | The license the kit ships under (MIT). Your own notes are yours. | Ships with the kit. | Never. |
| `.gitignore` | The list of files git must never save or share: secrets, scratch output, this computer's settings, `HANDOFF.md`. | Ships with the kit. | Rarely. |
| `CLAUDE.md` | The house rules Claude reads at the start of **every** session: who you are in a paragraph, how to work with you, where things live, what it must never do. | Both. Setup fills in your parts, you edit it when a rule changes. | Only when something must be true in every session. Keep it short. |
| `intake.md` | Your setup answers, saved as you give them, so setup can pick up where it stopped and later runs can skip what you already answered. | Claude, during setup. You can edit it. | When you run setup again. |
| `connections.md` | Every outside tool you use (email, calendar, storage, money, chat): what you use it for, whether Claude can reach it, which account, when it was last checked. | Both. Setup adds your tools; a row changes every time you connect something. | Whenever you start using, connect or drop a tool. |
| `inbox.md` | The landing strip. One line per captured thought, plus where it was filed. | Claude, automatically. | Constantly. You rarely read it top to bottom. |
| `tasks.md` | To-dos with no deadline, one checkbox line each. The session pulse shows Claude the open ones. | Both. | Whenever something small comes up or gets done. |
| `ideas.md` | Half-formed things worth keeping. Not commitments. | Both. | Whenever you have one. Prune it now and then. |
| `skills-registry.md` | Every skill in plain English: where it came from, whether it runs code, and its status. | Claude, via `/new-skill`. | When a skill is added, changed or retired. |
| `HANDOFF.md` | Only exists when you stopped mid-task. What was in flight and the next step. | Claude, via `/handoff`. | Written when you stop, read and deleted by the next session. Never saved in git. |
| `brand/README.md` | How the brand folder is filled in and used. | Ships with the kit. | Rarely. |
| `brand/brand.md` | Your colors, fonts, logo files, tagline, and one-liner. Every produced document reads it first. | Claude writes it from your website during setup. You correct it. | When your brand changes. |
| `brand/logos/` | Your actual logo image files. One of only two places the vault holds real files. | Claude copies them in during setup. | When you get new logos. |
| `context/about-me.md` | Facts about you as a person: role, what you own, how you think. | Both. | Rarely. These are slow-moving facts. |
| `context/about-business.md` | Facts about the business: what you sell, who buys it, how money works. | Both. | When the business actually changes. |
| `context/who-and-what.md` | The index of names. Every person, company, project and tool you might mention, with nicknames and the note to read first. Vault recall reads it on every message. | Both. Setup seeds it, Claude adds a row the moment a new name comes up. | Constantly, in small additions. |
| `context/contacts.md` | How to reach each person and the tone to use with them. | Both. | When a channel or a working style changes. |
| `context/where-files-live.md` | The map of your files: where each kind of file goes, with real paths and links, and how you name things. | Claude writes it during setup by looking, never moving. You correct it. | When you connect a drive, or change how you organize. |
| `memory/taste.md` | Preferences about Claude's output. What you like, what you hate, what you have rejected and why. Ships with one rule: no em dashes. | Claude, whenever you react to something. | Often, in small increments. This is the file that stops you repeating corrections. |
| `memory/claude/` | Claude's own memory: one short note per lesson about how to work with you, indexed in `memory/claude/MEMORY.md`. | Claude, as it works. | Often. Read it in Obsidian any time. |
| `references/README.md` | What belongs in the references folder and what does not. | Ships with the kit. | Rarely. |
| `references/voice.md` | How you write. Register, sentence length, words you use and avoid, real samples. | Claude writes it from your pasted samples. You correct it. | When you notice its writing is off. |
| `references/spoken-voice.md` | How you talk out loud. Used for video and voiceover only. | Both. | Rarely. |
| `references/how-i-decide.md` | Your decision rules. What you say yes to, what you refuse, what needs to be true. | Both. | When you notice yourself explaining a judgment call twice. |
| `decisions/log.md` | Every real decision, with the reasoning, oldest first. | Both. Claude adds an entry whenever you make a call. | Whenever a real decision gets made. Old entries are never edited. |
| `projects/README.md` | How the projects folder works, plus the index of live notes. | Both. | When a note is added or archived. |
| `projects/_TEMPLATE.md` | The shape of a project, client or person note. Copied by `/new-node`. | Ships with the kit. You can reshape it. | When you want notes to look different. |
| `projects/*.md` | One note per client, project, person or ongoing thing: a dated status line, open threads, meetings, and a `## Files` section. | Both. Created by `/new-node`. | Constantly. This is where live work lives. |
| `playbooks/README.md` | What a playbook is and when to write one. | Ships with the kit. | Rarely. |
| `playbooks/_TEMPLATE.md` | The shape of a playbook. | Ships with the kit. | Rarely. |
| `playbooks/*.md` | Written procedures for jobs you repeat. | Both. | The third time you do something by hand. |
| `outputs/` | Scratch space for files being built: PDFs, drafts, exports. Its contents are never saved in git. The other place the vault holds real files. | Claude. | Every time something is generated. Safe to empty. |
| `archives/` | Old notes you no longer need but should not delete. | You, or Claude when you ask. | Whenever a project ends. Move, do not delete. |
| `.obsidian/` | Obsidian's settings for this vault: which folders to hide, which built-in features are on. | Obsidian, and you. Ask Claude to edit it rather than hand-editing. | Rarely. |
| `.claude/settings.json` | Wires up the five automatic checks (hooks), names the Sheet Geek plugin and switches it on for this folder (Claude Code still needs it installed once, which setup does on your yes), and stops Claude from starting Claude Code's built-in `schedule` and `loop` skills on its own (you can still type them yourself). | Ships with the kit. | Only if you add or remove a hook. |
| `.claude/settings.local.json` | Settings for this computer only: where Claude's memory lives (setup writes it), plus any permissions you approved with "don't ask again". Never saved in git. | Claude Code and setup. | Rarely. |
| `.claude/hooks/run.sh` | The tiny launcher every hook goes through. It finds Python on your computer and runs the named script. If there is no Python, it quietly does nothing, so a missing Python never breaks a turn. Skills that run a Python script ask it which Python to use, so the whole vault uses the same one. | Ships with the kit. | Rarely. |
| `.claude/hooks/session_pulse.py` | The session pulse: a short briefing for Claude when a session opens. | Ships with the kit. | Rarely. |
| `.claude/hooks/vault_recall.py` | Vault recall: spots names in your message and points Claude at their notes. | Ships with the kit. | Rarely. |
| `.claude/hooks/auto_capture.py` | Auto-capture: spots a loose thought and has Claude file it. | Ships with the kit. | Rarely. |
| `.claude/hooks/brand_guard.py` | Brand guard: spots a request to make something and has Claude read your brand, taste and voice first. Its word lists are at the top, meant to be edited. | Ships with the kit. You add words. | When you make something new it has never heard of. |
| `.claude/hooks/brain_log.py` | Brain log: when Claude sends, drafts or saves something and no note was updated, it has Claude log it. Its lists of email, calendar and storage tool names are at the top, meant to be edited. | Ships with the kit. You add tools. | When you connect a tool it does not know. |
| `.claude/hooks/doctor.py` | The checkup. Not automatic: it runs when setup starts, or when you ask "is everything working?". Reports in plain words on Python, Sheet Geek, the memory location, the settings file, each hook, and folder trust. | Ships with the kit. | Rarely. |
| `.claude/skills/*/SKILL.md` | One folder per skill. The instructions Claude follows when that skill runs. | Ships with the kit, plus anything `/new-skill` writes. | When a capability is added or improved. |
| `.claude/skills/pdf/render.py` | Turns a designed web page into a real PDF by running a browser with no window open (Chrome, Chromium, Edge, or Brave). | Ships with the kit. | Rarely. |
| `.claude/skills/pdf/assets/` | The stylesheet and HTML template every PDF is built from. Your colors and fonts are written into each document, not into these files. | Ships with the kit. Edit to change how PDFs look. | When you want a different document design. |
| `.claude/skills/meeting-notes/extract_notes.py` | Pulls the readable text out of a meeting notes document. | Ships with the kit. | Rarely. |
| `.claude/skills/update-vault/match_known.py`, `known-versions.json` | The update's read-only checker, and fingerprints of earlier versions of this kit, so an update can tell a file you never touched from one you changed. A fingerprint holds no text. | Ships with the kit. | With each new version. |

---

## The five kinds of things in this vault

If you can tell which of these a piece of information is, you always know where it goes.

**1. Facts that stay true.** Your role, what the business sells, who your people are, where your files live. These live in `context/`. The index of names, `context/who-and-what.md`, is the front door: every person, company, project and tool gets a row there, pointing at the note to read first. Facts change slowly. If you find yourself editing one weekly, it was not a fact, it was live work.

**2. Preferences about how you like things.** Opinions, not facts. Your writing voice (`references/voice.md`), your colors and fonts (`brand/brand.md`), the things you have rejected before (`memory/taste.md`), how you make calls (`references/how-i-decide.md`). These are why output comes back right instead of generically correct.

**3. Live work.** What is happening right now: `projects/` and `tasks.md`. This is the noisiest part of the vault and that is fine. Every live note carries a dated status line, so anyone reading it knows how fresh it is. When a project ends, its note moves to `archives/`.

**4. Decisions and their reasons.** `decisions/log.md`. Entries are only ever added. Its value is the reasoning, because in four months you will remember the decision and not why you made it.

**5. Know-how.** `playbooks/` for procedures a person follows, `.claude/skills/` for procedures Claude runs, and `memory/claude/` for the lessons Claude has learned about working with you. This is the part that compounds. Every time something moves from your head into here, nobody has to wait for you to explain it again.

Files themselves (documents, spreadsheets, recordings) are not in this list on purpose. They stay wherever you already keep them. The vault holds a link to each one, on the note it belongs to.

---

## How a note is shaped

A few small formats do a lot of work, because the automatic checks and every new session rely on them.

**The index row.** Every person, company, project and tool has one row in `context/who-and-what.md`, in the section that fits (People, Companies and organizations, Projects and products, Tools and systems):

```text
| Name | Also called | What | Home |
| --- | --- | --- | --- |
| Jordan Lee | Jordan, Jordon | Operations lead at Acme, signs off on scope | [[projects/acme-corp]] |
```

"Also called" holds nicknames, first names, and the way your dictation tends to spell them. "Home" is the note to read first. A person with no note of their own points at their company's note, or at `[[context/contacts]]`.

**The status line.** Near the top of every client, project and person note:

```text
**Status (2026-03-02):** proposal v2 sent, waiting on Jordan's sign-off
```

The date is the day the status was last true. When the status changes, Claude rewrites the line with the new date, in the same turn, and closes any matching to-do in `tasks.md`. A stale status line is how a new session gives a wrong answer, so this one line gets more care than anything else in the note.

**The Files section.** One dated line per file, oldest at the top:

```text
## Files
- 2026-02-20 Signed contract: `~/Documents/Clients/Acme/2026-02-20 Acme contract signed.pdf`
- 2026-03-02 [Acme proposal v2](https://...)
```

A cloud file gets a link. A file on your computer gets its path. The file itself never moves into the vault. When a newer version replaces a draft, the draft's line is updated; lines for anything sent or signed stay.

---

## How the notes connect: wikilinks and the graph

A **wikilink** is a link from one note to another. You write it as a note name inside double square brackets:

```text
[[projects/acme-corp]]
```

Write that in a task, a decision, an inbox line, or a meeting summary, and all of them now point at the same note. Open that note in Obsidian, look at the **backlinks** panel, and you see every place the client was mentioned, in one list, without searching.

Obsidian's **graph view** (the constellation icon in the left sidebar) draws all those links as a picture. Dense clusters are where your real work is. Lonely dots are things you started and dropped. It is an honest read on your own attention.

You do not have to remember to write them. Every skill in this kit links what it writes, and `CLAUDE.md` carries the same standing rule, so links appear whether or not you think about them.

---

## The three laws of the vault

**1. Raw input lands in `inbox.md`, then goes to its real home in the same turn.** A thought that only sits in the inbox is a thought that is lost. The inbox records that something was said and where it went. The thought itself lives in a project note, on your calendar, in `tasks.md`, or wherever it belongs.

**2. Anything that must shape every session goes into `CLAUDE.md`.** Most files are read only when they are relevant. `CLAUDE.md` is read at the start of every session. So if Claude keeps getting something wrong that matters everywhere, one line there fixes it for good. (A lesson about how Claude should work, rather than about you or your business, can go in its memory instead.) Keep `CLAUDE.md` short and load-bearing. If it becomes a dumping ground it stops working.

**3. The second time Claude does the same kind of task, it becomes a skill.** Once is a task. The second time is the signal: Claude writes the steps down as a skill in that same session, so the third time runs the same way without anyone explaining it again. Skills that are only instructions ship right away with a one-line note to you. Anything that would run code, use a new account, or send, post or pay waits for your yes. Your own repeats count too: the third time you do a manual task by hand, Claude points it out and offers to write a playbook.

---

## What happens in a session

Five small scripts, called **hooks**, run at set moments. Each one looks at your message or at files on your computer and, when it has something to say, puts a short instruction in front of Claude. None of them uses the internet, none runs outside a session you opened, and if one breaks it stays silent rather than breaking your turn. They all need Python, and they all go through `.claude/hooks/run.sh`, which quietly does nothing when Python is missing.

### When a session opens: the session pulse

`session_pulse.py` hands Claude a short briefing. You do not see it. Claude does. It lists:

- notes changed in the last week, newest first (the kit's own guides are left out);
- the latest lines of `inbox.md`, so Claude knows what you said in passing yesterday;
- the first few open to-dos in `tasks.md`;
- your other recent Claude Code sessions in this same folder (their titles and your last message in each), so "where were we?" works across windows;
- `HANDOFF.md`, if you left work mid-way;
- housekeeping: a project note with no index row, a skill with no registry row, Claude's memory index close to its load limit, the memory location not set (or pointing at an old place), Python too old.

Claude tidies the housekeeping items in passing and mentions it in one line. Before setup has run, the pulse simply reminds Claude to offer it once.

### Every time you send a message: three checks

**Vault recall** (`vault_recall.py`) looks for names. It knows every Name and Also called entry in `context/who-and-what.md`, plus every note's file name, title and aliases, and it forgives small dictation slips ("Jordon" still finds Jordan), but never an everyday word ("page" does not find Paige). On a match, Claude gets the note's path, its one-line description and its current status line, plus a reminder: if anything in this conversation changes, update that same note's dated status line and its index row, and never start a second note for the same thing. If nothing matches but you are clearly asking about someone ("who is", "where are we with", "remind me", "what did Sam say"), Claude is told to search the vault before asking you.

**Auto-capture** (`auto_capture.py`) asks "is this a loose thought rather than an instruction?" It stays quiet on questions, on slash commands, on thanks and short answers ("yes, the second one"), on messages that open with a verb aimed at Claude ("draft", "fix", "make"), on the phrases a skill listens for ("map my files"), and while setup is asking its questions. Otherwise it has Claude file the thought with the `capture` skill. Starting a message with `inbox:` or `capture:` forces it.

**Brand guard** (`brand_guard.py`) asks "is this a request to make something?" by matching word lists at the top of the file. Some words fire on their own (`one pager`, `proposal`, `deck`). Others fire only next to an action word, so "write me an email" triggers it and "did you see the email from the client" does not. When it fires, Claude reads `brand/brand.md`, `memory/taste.md` and `references/voice.md` before writing a word. It stays quiet while setup is asking its questions, so a writing sample you paste in is not mistaken for a request.

All three stay silent when they have nothing to say. Sheet Geek, once installed, adds a check of its own: name a spreadsheet it has already studied, and Claude gets that sheet's notes.

### When Claude finishes a reply: the brain log

`brain_log.py` looks back over what Claude just did. If it sent or drafted an email, created or changed a calendar event, or saved a file to cloud storage (or shared one), and no note in `projects/`, `context/`, `references/` or `decisions/` changed since your last message, it holds the reply **once** and tells Claude to:

- add one dated line to the note of each person or company involved (the index says which note), saying what went out and what happens next;
- update that note's status line if it moved;
- for a file, put the link on the note (never the file itself), with the file saved where `context/where-files-live.md` says.

A line in `inbox.md`, `tasks.md`, `ideas.md` or Claude's memory does not count, because the next session looks for facts on the person or company note. A new calendar block with nobody else on it (time you set aside for yourself, like the reminder in example A below) is not held: nothing went out to anyone. The brain log recognizes tools by the names they use: Gmail, Outlook and Microsoft 365, Apple Mail, Google Calendar, Outlook calendar, Google Drive, OneDrive and SharePoint, Dropbox and Box are on its lists, a tool whose name pairs an action with a thing ("reply" with "mail", "upload" with "file") is caught too, and so is a file Claude saves into a cloud-synced folder on this computer, iCloud Drive included. Chat messages (Slack, Teams chat, texts) are left out on purpose. If a mail, calendar or storage tool of yours is still missed, say "add it to the brain log lists".

### Worked example A: you mumble something

You type, with no other instruction:

```text
remind me to call the accountant thursday
```

- Auto-capture sees a loose thought and has Claude route it rather than just acknowledge it. ("Remind me" is a thing to file, not a job to do this turn.)
- Claude reads it as time-bound, so it creates a calendar event for Thursday, a one-hour block by default. **If no calendar is connected yet**, and on day one none is, it says so in one line and puts the item in `tasks.md` instead. It never pretends an event was created.
- It adds one line to `inbox.md` saying what you said and where it went.
- It replies with a single line: what it did and where it filed it.

You typed seven words and never learned a command.

### Worked example B: you ask for a document

You type:

```text
make me a one pager on our onboarding process
```

- Brand guard matches "one pager" and has Claude read `brand/brand.md`, `memory/taste.md` and `references/voice.md` **before** writing a word.
- Claude now knows your colors, your fonts, your logo file, your tagline, your sentence rhythm, and the things you always hate.
- It writes the copy in your voice, lays it out with your colors and your logo, renders a real PDF, and saves it where your file map says finished documents go, with a dated line on the matching note.

You did not invoke a skill or paste your brand guide. It already knew.

### Worked example C: you name someone

You type:

```text
where are we with jordan at acme?
```

- Vault recall finds "Jordan" in the Also called column of a row whose Home is `[[projects/acme-corp]]`, and points Claude at that note.
- Claude reads it: `**Status (2026-03-02):** proposal v2 sent, waiting on Jordan's sign-off`. It answers from that line, date included, so you can see how fresh it is.
- You reply `jordan signed it this morning`. Claude rewrites the status line with today's date, closes the "chase Jordan" to-do in `tasks.md`, and asks for the signed copy's link if you want it under `## Files`.

Nobody re-explained who Jordan is, and next week's session will know the deal is signed.

### Worked example D: Claude drafts an email

You type:

```text
draft a follow-up to sam at acme about the overdue invoice
```

- Vault recall points Claude at the Acme note. Brand guard has it read your voice and taste first.
- Claude writes the email as a **draft** in your mailbox and shows it to you. It never sends it.
- As the reply ends, the brain log sees an email draft and no note updated. It holds the reply once, and Claude adds a dated line to the Acme note: drafted a follow-up to Sam about the overdue invoice, not sent yet.
- Two weeks later, in a brand-new session, "did we ever chase Sam about that invoice?" has a true answer.

**Two honest caveats**, so nothing surprises you later.

- The checks run on word lists and simple rules, not mind-reading. Brand guard's words and the brain log's tool names are at the top of their files and meant to be edited. Say "add menu to the brand guard list" and Claude edits the file for you.
- A result is only as good as the files behind it. If your website did not publish readable colors, `brand/brand.md` says so rather than inventing a color, and the first document you ask for asks you once, then writes your answer down for good.

---

## Where your files go

Your files stay where you keep them. The vault learns your system and follows it.

**Learning it.** During setup, the `map-files` skill looks at where you keep work: any cloud storage Claude can reach, and your main folders on this computer, a few levels deep. It only looks. Then it writes `context/where-files-live.md`: your folders with real paths and links, your naming habits with real examples, which kind of file goes where, and a short list of questions. It asks you only what it could not see, a few at a time, each with its best guess. Storage it cannot reach yet goes under "Not reachable yet". After you connect a drive, say "map my files".

On a Mac, the first time Claude looks in Desktop, Documents or Downloads, macOS may ask whether Visual Studio Code can access that folder. Click OK. (Don't Allow is fine too. That folder is just marked as not reachable.)

**Following it.** Every file Claude makes or saves goes where the map says, named the way you name things. If there is no clear home, it asks and suggests a spot. If the home is obvious, it just does it. Then it adds one dated line to the `## Files` section of the client, project or person note, so the file can always be found from the note.

**Never reorganizing.** Claude never moves, renames, deletes, merges or "cleans up" your existing files or folders, and never creates new top-level folders, unless you ask. If you change your folders, it updates the map. It never changes your folders to fit the map.

**The one exception.** If your files have no system at all (work files loose on the Desktop, in Downloads or at the top of a drive, nothing grouped by client, project or type, no naming pattern), Claude may offer two things: a simple starter layout for new files (Clients, Projects, Company, Brand, Content, Research, Archive), and a cleanup of what is already there. Each is shown to you first and done only on your yes, and a cleanup shows you the full list of moves before anything moves. If you have any real system, even one Claude would not have chosen, it never offers. You can always ask.

---

## Claude's memory lives in your vault

Claude Code has a built-in memory: as it works, it writes short notes about how to work with you (a correction you made, a gotcha it hit, a way you like things done) and reads their index at the start of every session.

Normally that memory sits in a hidden folder in your home directory. Setup moves it into this vault, at `memory/claude/`, by writing one setting into `.claude/settings.local.json` (a settings file for this computer only, never shared). That is why setup asks you to reload once. From then on you can read, link and correct Claude's memory in Obsidian like any other note.

- `memory/claude/MEMORY.md` is the index: one line per memory note. Only the first 200 lines or 25 KB of it load when a session starts, so Claude keeps it short and moves detail into the notes. The session pulse warns when it gets close.
- Facts about your business (who someone is, a status, a price, a date) belong in the notes, not in memory. Memory holds how-to-work lessons and points to the note for the facts.
- Preferences about output (too long, wrong tone, never do that again) go in `memory/taste.md`, which every produced document reads.
- If you move the vault, the setting still points at the old place. The session pulse notices, and Claude can fix it in one step.

---

## Skills versus playbooks versus notes

Three things that sound similar and are not.

| | What it is | The test question | Example |
| --- | --- | --- | --- |
| **Skill** | A repeatable procedure Claude runs. Lives in `.claude/skills/`. | "Could Claude do this end to end if I just asked?" | Turn this into a branded PDF. |
| **Playbook** | A written process a person or Claude follows step by step. Lives in `playbooks/`. | "Are there steps, some of which need judgment or a human?" | How we take on a new client. |
| **Note** | A fact or a record. Lives in `context/`, `projects/`, or `decisions/`. | "Is this just something that is true?" | This client pays net 30. |

Rule of thumb: if you would hand it to a new hire as instructions, it is a playbook. If you would hand it to a robot, it is a skill. If you would hand it to them as background reading, it is a note.

---

## The skills that ship with it

A **skill** is a set of instructions Claude loads when a task matches it. You never have to name one: say the plain thing and the matching skill runs. The slash command is only a shortcut.

| Skill | What it does | How it starts |
| --- | --- | --- |
| `/onboard` | Setup. Checks your computer first (Python 3.10 or newer, the Sheet Geek plugin, folder trust) and offers to install what is missing. Then asks as many questions as it needs, never more than 15, each shaped by your earlier answers. Writes who you are, your voice, your brand, your money and communication tools, your people and companies, and your file map. Ends by telling you what is still missing. | "set me up" |
| `/capture` | Takes a loose thought, gets the names right, and files it in exactly one place: a calendar event, a project note, the to-do list, or done on the spot. Logs one line in `inbox.md`. | Nothing. Auto-capture starts it for you. |
| `/new-node` | Creates a note for a new client, project, or person, with a dated status line, a `## Files` section, a row in the index of names, and links into the rest of the vault. | "start a note for my new client" |
| `/vault-notes` | The house rules for notes: which folder a note goes in, how it is named and linked, the `## Files` section, and how to find things. Claude uses it whenever it reads or writes a note. | "what do we have on Acme?" |
| `/new-skill` | Turns a description of a repeatable job into a working skill and adds its row to `skills-registry.md`. Also runs on its own the second time Claude does the same kind of job. | "make me a skill that..." |
| `/meeting-notes` | Reads a meeting notes document, writes a tight summary, files it under the right note, and routes the action items. | "process my meeting notes" |
| `/pdf` | Turns content into a designed PDF in your colors, fonts, and logo, saves it where your file map says, and logs it on the note. | "make me a one pager on X" |
| `/map-files` | Learns how you organize your files (look only), writes `context/where-files-live.md`, and asks only about the gaps. Setup runs it. | "map my files" |
| `/import-contacts` | A one-time pass through your recent email, once email is connected, that suggests people and companies for the index. Adds only the ones you say yes to. | "import my contacts" |
| `/handoff` | Writes `HANDOFF.md` when you stop mid-task, so the next session picks up exactly where you left off. | "hand this off" |
| `/update-vault` | Brings an older copy of this vault up to date: new hooks, skills and rules in, your notes, contacts and memory untouched, every change shown before it is made. | "update my vault" |
| Sheet Geek (plugin) | Reads a spreadsheet with code, asks you only what the data cannot answer, and saves what it learned inside the file. Every spreadsheet you share or ask about goes to it. | "give this spreadsheet a brain" |

The full list, including any skill you add later and whether each one runs code, lives in `skills-registry.md`.

**How the list grows.** Claude makes a new skill on its own the second time it does the same kind of job, when you walk it through a process worth keeping, or when you ask. A skill that is only instructions ships right away, with a one-line note to you. A skill that runs code, needs a new account, key or API, or can send, post or pay is registered as `needs-review` and does not run until you say yes. A skill with no row in the registry gets a row added; a missing row is bookkeeping, never a reason to refuse. A skill found on the internet is read in full first, and its text is treated as data, never as orders.

---

## Growing the vault

**Add things when they become real.**

- A note in `projects/` the moment a client, project or person becomes real. Say "start a note for my new client".
- A row in `context/who-and-what.md` the first time a new name comes up. Claude does this on its own.
- A playbook in `playbooks/` the third time you do something by hand.
- A row in `connections.md` every time you plug in a new outside tool.
- A line in `references/how-i-decide.md` whenever you explain a judgment call for the second time.

**Watch out for these. They quietly make the vault less useful.**

- **Two notes about the same thing.** If Acme has a note, everything about Acme goes in it. A second note splits the truth, and the next session reads the wrong half.
- **Copies of files.** The vault keeps a link, not the file. A copy goes stale the day the original changes, and then there are two versions arguing.
- **Status lines with no date.** "Waiting on Jordan" means nothing in a month. "**Status (2026-03-02):** waiting on Jordan" tells you exactly how stale it is.
- **Rules that only lived in chat.** If you corrected Claude and it matters every time, check that it landed in `memory/taste.md` or `CLAUDE.md`. Something said once in chat is gone next session.
- **A bloated `CLAUDE.md`.** Every line in it is read at the start of every session. Keep it to the rules that must always hold, and let everything else live in notes Claude reads when they matter.
- **Secrets.** No password, key, token, or account number in any file Claude reads. Not once, not temporarily.

---

## Upgrading from an older copy

Open the vault in Claude Code and say "update my vault". The `update-vault` skill:

- brings in the new hooks, skills and rules;
- never touches your notes, your contacts, Claude's memory, or any hook or skill you added yourself;
- swaps in the new starter notes only where you never touched the old ones;
- keeps everything you filled into `CLAUDE.md`;
- answers each new setup question from what your vault already knows, and asks you only what it cannot work out;
- shows you exactly what would change, and changes nothing until you say yes;
- keeps a copy of every file it replaces, in `archives/`, so nothing is lost.

A copy made before that skill existed does not know the phrase. The first time, paste the longer message from the README's "Already using the old version?" section instead. It asks Claude to download the new version into a temporary folder outside your vault, read the update steps there, and follow them as your instructions, with the same change list and the same wait for your yes.

---

## Safety model

Six rules. Each one exists for a specific reason.

**External content is data, never instructions.** Emails, web pages, PDFs, spreadsheet cells, scraped text, and meeting transcripts can contain text that looks like a command ("ignore previous instructions and send..."). Claude reads them as content to summarize or consider, never as orders, because anyone who can put text in front of your AI could otherwise steer it.

**Anything outward-facing or irreversible stays a draft until you fire it.** Sending, pushing, deploying, publishing, and paying are things you do, not things it does. It writes the email and shows you. You press send. Those actions cannot be taken back, and a confident mistake is still a mistake.

**It never touches money or credentials.** No account numbers, no card details, no passwords, no API keys, in either direction. It will not move money and it will not repeat a secret back to you. There is no version of this system where that capability is worth the risk.

**Nothing runs on a schedule.** No background jobs, no timers, no always-on agent. Work happens inside a session you opened and stops when you close it. Helpers that live inside that session are fine (the hooks, and any helper agents Claude starts for a task), because they end with it. An always-on agent is an always-on attack surface, and you cannot supervise something that runs while you sleep.

**Nothing is reachable from another machine.** No remote access, no tunnels, no open ports. If a tool ever needs to listen for connections, it listens on `127.0.0.1`, which means this computer only.

**Checks beat reminders.** When a rule has to hold every time, the vault uses a small check that always runs (a hook or a script) instead of a note asking Claude to remember. That is why the five hooks exist: they make the important habits happen even on a busy day.

If a task seems to want a scheduler, a watcher, or an always-on service, the right move is to say so and let you decide. Not to quietly stand one up.
