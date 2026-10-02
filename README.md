# AIOS Vault

A folder of plain notes that teaches Claude who you are, so you stop explaining yourself.

You re-introduce yourself to the AI at the start of every session. You paste the same background over and over: what the business does, who your customers are, who "Sam from Acme" is, how you write, where last month's proposal lives. And when something finally comes out, it does not look like yours, because the AI never saw your brand or your voice.

This is one folder that fixes that. (It is a **repo**, short for repository, which just means a folder of files kept and shared together.) Your context lives in plain markdown files. You browse and edit them in Obsidian like a notebook, and you open the exact same folder in Claude Code inside VS Code, so the AI reads them every time you talk to it. Setup is one short conversation: it asks only what it needs, shapes each question by your last answer, and never asks more than 15. After that it already knows.

## What you get

- You stop pasting the same background at the top of every chat.
- It knows your people. Name a client or a colleague, even by a nickname or with a dictation typo, and Claude reads their note before it answers.
- Every new session starts with a short briefing on what moved this week, so "where were we?" has an answer.
- Documents come out in your colors, your fonts, and your voice, on the first try.
- Loose thoughts you mumble at it land in the right place instead of scrolling away.
- What goes out gets written down. Every email it drafts and every file it saves for you gets a dated line on the right person or project note, and a check at the end of each reply catches any email, calendar change or cloud save that was not logged.
- It learns how you already keep your files and follows your system. It never reorganizes anything unless you ask.
- Spreadsheets get read properly, with code, by Sheet Geek, a free plugin that setup helps you add.
- It grows. The second time it does the same kind of job for you, it writes itself a skill, so the job runs the same way every time after.
- Every decision, with the reason behind it, in one log you can search.

## How it works in one picture

```text
        YOU                         ONE FOLDER ON YOUR COMPUTER
   ------------               ------------------------------------------
                              context/     who you are, who you deal with
   Obsidian  <-- browse -->   brand/       colors, fonts, logos
   (see it,     edit it       memory/      what you like, what Claude learned
    link it,                  references/  how you write and decide
    search it)                projects/    live work, one note each
                              decisions/   what you chose and why
                                    ^
                                    | same files, no copy, no sync
                                    v
   VS Code with  <-- you talk -->  Claude reads the folder as context
   Claude Code                      |
                  small checks run on their own, inside your session
                                    |
     +-------------+-------------+--+----------+-------------+
     |             |             |             |             |
  session       you name      a loose       "make me a     it sent or
  opens: a      someone:      thought:      one pager":    saved something:
  briefing on   it reads      it files      it reads       it logs that on
  what moved    their note    it in one     brand, voice   the right note
                first         place         and taste
     |             |             |             |             |
     +-------------+-------------+------+------+-------------+
                                        v
               answers that sound like you and know your world
```

A **hook** is a small script Claude Code runs at a set moment: when a session opens, when you press Enter, or when Claude finishes a reply. Five ship in this folder, and they are what make the bottom half of that picture happen without you asking. More on them below.

## The quick start

About 15 minutes to install, then a 15 to 30 minute conversation. Works on a Mac, on Windows, and on Linux. To sign in to Claude Code you need a paid Claude plan (Pro, Max, Team or Enterprise) or a Claude Console account.

1. **Install three free apps.** [VS Code](https://code.visualstudio.com), the editor you will talk to Claude in. The **Claude Code** extension: in VS Code, open the Extensions view (`Cmd+Shift+X` on a Mac, `Ctrl+Shift+X` on Windows or Linux), search "Claude Code", and click **Install**. And [Obsidian](https://obsidian.md), the app you will read your notes in. On Windows, also install [Git for Windows](https://git-scm.com/downloads/win): the automatic parts of this vault run through the small command shell it brings.

2. **Get the folder.** On this page, click the green **Code** button, then **Download ZIP**. Unzip it and move the folder somewhere permanent, like your Documents folder. It is going to hold your real work.

3. **Open it in Obsidian.** Click **Open folder as vault** and pick the folder. A vault is just a folder of notes.

4. **Open the same folder in VS Code.** **File**, then **Open Folder** (on a Mac, **File**, then **Open** works too), and pick the folder itself, the one with `CLAUDE.md` directly inside. When VS Code asks whether you trust the authors of the files in this folder, click **Yes, I trust the authors**.

5. **Open Claude Code and sign in.** Click **Claude Code** in the status bar at the bottom right of the window. (Or click the Spark icon, a small starburst, in the bar on the far left, then start a new session.) Sign in the first time. If Claude Code asks whether you trust this folder, say yes. Trust is what switches on the automatic parts.

6. **Say "set me up".** Setup starts by checking three things: Python 3.10 or newer (a free program the automatic parts run on), the Sheet Geek plugin, and that Claude Code trusts this folder. If anything is missing, it tells you what it is and asks once whether to fix it. On your yes it installs what it can itself and walks you through anything that needs your own hands, like a Python installer. Then the conversation.

7. **Reload once at the end.** When setup says so, open the Command Palette (`Cmd+Shift+P` on a Mac, `Ctrl+Shift+P` on Windows or Linux), type **Developer: Reload Window**, and press Enter. That moves Claude's own memory into your vault, where you can read it in Obsidian.

What setup covers: your name, your business and who buys from you; a few things you have actually written, pasted in exactly as sent; your website and logos; where money lands and where you track it (names of tools only, never account numbers); the apps you use with customers, with your team and in public; the people and companies you deal with most; and where your files live, which it looks at first and only asks about the gaps. It ends by telling you what is still missing, so you know what to do next.

From then on, just talk to it normally. You never have to remember a command, because the important behavior runs on its own.

New to VS Code, or prefer the terminal? [INSTALL.md](INSTALL.md) walks through every click, covers the terminal route, and has a troubleshooting table.

## What is in the box

Eleven skills and one plugin. A **skill** is a set of instructions Claude follows when your words match it, so you do not have to memorize the slash commands. Say the plain thing and it runs.

| What you want | You say this | Shortcut |
| --- | --- | --- |
| Set it up on day one | "set me up" | `/onboard` |
| Dump a thought and have it filed | just say the thought | `/capture` (runs by itself) |
| A note for a new client, project or person | "start a note for my new client" | `/new-node` |
| Find what you have on someone | "what do we have on Acme?" | `/vault-notes` (Claude uses it on its own) |
| Teach it something new | "make me a skill that..." | `/new-skill` |
| Turn meeting notes into a filed summary | "process my meeting notes" | `/meeting-notes` |
| A designed PDF in your brand | "make me a one pager on X" | `/pdf` |
| Teach it where your files live | "map my files" | `/map-files` |
| Find more of your people in your email | "import my contacts" | `/import-contacts` |
| Stop mid-task and pick up later | "hand this off" | `/handoff` |
| Bring an older copy up to date | "update my vault" | `/update-vault` |
| Understand a spreadsheet | "give this spreadsheet a brain" | Sheet Geek (plugin) |
| Check that everything works | "is everything working?" | runs a short checkup |

`/capture` is worth calling out. You do not run it. When you type a loose thought with no clear instruction, it runs on its own and files the thought where it belongs.

Sheet Geek is a separate free, open-source plugin ([github.com/Actual-Intelligence-Labs/sheet-geek](https://github.com/Actual-Intelligence-Labs/sheet-geek)). It reads a spreadsheet with code instead of guessing, asks you only what the data cannot tell it, and saves what it learned inside the file. This vault sends every spreadsheet you share or ask about to it.

## What runs on its own

Five hooks, in `.claude/hooks/`. Each one runs at a set moment and, when it has something to say, puts a short instruction in front of Claude for that turn.

| When | Hook | What it does |
| --- | --- | --- |
| A session opens | **Session pulse** | Gives Claude a short briefing: notes changed this week, your latest captured thoughts, open to-dos, your other recent sessions in this folder, a handoff note if you left work mid-way, and housekeeping (a note nobody indexed, Python too old, memory not set up yet). |
| You send a message | **Vault recall** | If you name a person, company, project or note it knows, even misspelled, Claude reads that note before it answers and updates the same note if anything changed. If you ask about someone it does not recognize, it searches the vault before asking you. |
| You send a message | **Auto-capture** | If the message is a loose thought rather than an instruction, Claude files it in the right place instead of just saying "noted". |
| You send a message | **Brand guard** | If you ask it to make something (a proposal, a post, an email, a PDF), Claude reads your brand, voice and taste files before writing a word. |
| Claude finishes a reply | **Brain log** | If Claude sent or drafted an email, changed a calendar event, or saved a file to cloud storage, and no person, company or project note was updated, it holds the reply once and has Claude add a dated line (and a link, for a file) to the right note. |

What they do not do, honestly:

- They nudge, they do not do the work. A hook only puts an instruction in front of Claude at the right moment. Claude still does the reading and the writing, and every change shows up in Obsidian.
- They read only files on your computer (this folder, plus Claude Code's own record of your sessions) and never use the internet.
- They run only inside a session you opened, and they need Python. Without Python they quietly do nothing, which is why setup checks for it first. When they run, you may see a short status line flash by, such as "Looking up names in your vault".
- Only the brain log can hold a reply, and only once per reply.
- Their word lists are guesses about how you talk, and you can change them. If something you make is never caught, say "add show notes to the brand guard list" and Claude edits the file.

Sheet Geek, once installed, adds two small hooks of its own: when a session opens, or when you name a spreadsheet it has already studied, it hands Claude that sheet's notes.

## Why Obsidian

- The vault is nothing but plain markdown files in ordinary folders.
- Obsidian gives you a browsable, linked, searchable view of them, for free.
- Notes link to each other with **wikilinks**, which are just a note's name in double square brackets: `[[memory/taste]]`, `[[projects/acme-corp]]`. Obsidian's graph view draws every link as a line, so you can see the shape of everything you have written.
- Claude Code reads the same files off disk. No import, no sync, no database.
- Neither tool owns your data. Delete Obsidian and nothing breaks. Delete Claude Code and you still have your notes.

## It keeps working after you close the laptop?

No. On purpose.

- **Nothing runs on its own schedule.** No background jobs, no timers, no always-on agent. The hooks above run only inside a session you opened, and stop when you close it.
- **Nothing is reachable from another machine.** No server, no tunnel, no open port, no chat bridge. Your notes sit on your disk.
- **Nothing irreversible happens without you.** Claude drafts, stages, and shows you. You press any button that sends, pushes, deploys, publishes, or pays.

This is a deliberate trade. You give up "it did things while I slept" and you get a system that cannot surprise you, cannot be reached by a stranger, and cannot spend your money.

## Already using the old version?

Open your vault in Claude Code and say **update my vault**. It brings in the new hooks, skills and rules, keeps everything you filled into `CLAUDE.md`, and never touches your notes, your contacts or Claude's memory. It answers the new setup questions from what your vault already knows, asks only what it cannot work out, and shows you every change before it makes one.

A copy made before this version has no update step of its own yet. The first time, paste this whole message instead. It spells out exactly what you want, so Claude does not have to guess:

```text
Update my vault to the latest version. Download github.com/Actual-Intelligence-Labs/aios-vault into a temporary folder outside this vault (do not git pull into this vault), read .claude/skills/update-vault/SKILL.md in that download, and follow those steps as my instructions: show me the full list of changes, and change nothing until I say yes.
```

## Make it yours

Out of the box the vault is nearly empty on purpose, so it fits any kind of work. Say "start a note for my new client" and `/new-node` wires a note into the vault, with links, so it shows up in your graph and in search. Describe a job in plain English and `/new-skill` writes the skill and lists it in `skills-registry.md`. You never have to learn the file format.

It also grows on its own. The second time Claude does the same kind of job for you, it writes the skill itself and tells you in one line. Anything that would run code, use a new account, or send, post or pay waits for your yes first.

Your own writing sets the style. The one style rule that ships is no em dashes (the long dash that gives AI writing away). Everything else comes from the writing you paste in during setup, and from what you tell it you like and dislike.

## Keep your copy private

Once it is filled in, this folder holds real names, notes and file locations. If you put it on GitHub or a shared drive, keep that copy private.

## License

MIT. See [LICENSE](LICENSE). Sheet Geek is a separate project under its own license (Apache-2.0).

Built by [Actual Intelligence Labs](https://actualintelligencelabs.ai)
