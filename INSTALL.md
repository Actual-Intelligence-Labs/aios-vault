# Install

Written for someone who has never installed a developer tool. Every step is a literal thing to click or type.

**Time:** about 15 minutes to install, then a 15 to 30 minute setup conversation.

**What you need:**

- A Mac, a Windows PC, or a Linux machine.
- A paid Claude plan (Pro, Max, Team or Enterprise) or a Claude Console account. You sign in with it the first time you open Claude Code. You do not need an API key.

There are two ways to run this vault. Most people use **VS Code** ([Part 1](#part-1-the-vs-code-route-recommended)). If you already live in a terminal, [Part 2](#part-2-the-terminal-route) is for you. Both use the same folder and end up in the same place.

---

## A few words you will see

- **VS Code:** a free app from Microsoft for editing files. Claude Code runs inside it as an **extension** (an add-on), in a panel at the side of the window.
- **Obsidian:** a free app for reading and linking notes. It is how you *see* your vault.
- **Vault:** this folder. Plain text files that both apps read. Nothing is copied or converted.
- **Trust:** the first time you open a folder, VS Code asks whether you trust the files in it, and Claude Code may ask too. Saying yes is what lets the vault's automatic parts run.
- **Command Palette:** VS Code's search box for commands. Open it with `Cmd+Shift+P` on a Mac or `Ctrl+Shift+P` on Windows and Linux, then type the name of a command.
- **Python:** a free programming language. The vault's automatic parts and the spreadsheet plugin run on it. You never have to write any.
- **Plugin:** a packaged add-on for Claude Code. This vault uses one, Sheet Geek, for spreadsheets.
- **Path:** a file or folder's full address on your computer, like `/Users/sam/Documents/aios-vault`. Setup asks for one or two. To copy one without typing it: on a Mac, right-click the folder in Finder, hold down `Option`, and choose **Copy "name" as Pathname**. On Windows, right-click it and choose **Copy as path**. On Linux, choose **Copy location**.

---

## Part 1: the VS Code route (recommended)

### Step 1: install the apps

| # | App | What it is for | How to get it |
| --- | --- | --- | --- |
| 1 | VS Code | Where you talk to Claude. Version 1.94 or newer. | Free at [code.visualstudio.com](https://code.visualstudio.com). Open it once after installing. |
| 2 | Claude Code extension | Claude itself, inside VS Code. | In VS Code, open the Extensions view (`Cmd+Shift+X` on a Mac, `Ctrl+Shift+X` on Windows or Linux), search **Claude Code**, and click **Install** on the one published by Anthropic. |
| 3 | Obsidian | Where you read and browse your notes. | Free at [obsidian.md](https://obsidian.md). |
| 4 | Git for Windows (Windows only) | The vault's automatic parts run through the small command shell it brings. Macs and Linux already have one. | Free at [git-scm.com/downloads/win](https://git-scm.com/downloads/win). Click through the installer with its default choices. |

You do not need to sort out Python or the Sheet Geek plugin first. Setup checks for both in Step 6, installs what it can on your yes, and walks you through the rest. If you would rather do it by hand, see [Installing Python yourself](#installing-python-yourself) and [Installing Sheet Geek yourself](#installing-sheet-geek-yourself).

### Step 2: get the folder

**The clicking route.** On the vault's GitHub page ([github.com/Actual-Intelligence-Labs/aios-vault](https://github.com/Actual-Intelligence-Labs/aios-vault)):

1. Click the green **Code** button near the top.
2. Click **Download ZIP**.
3. Open your Downloads folder and unzip the file (double-click it on a Mac, right-click then **Extract All** on Windows).
4. Move the unzipped folder into your Documents folder, or anywhere permanent. Rename it if you like, for example to `aios-vault` or `sam-vault`.

**The git route.** If you already use git: click the same green **Code** button, copy the `https://...` address, and run `git clone` with it from your Documents folder.

**Somebody handed you the folder** on a drive or in a shared folder? Copy it into your Documents folder. You are done with this step.

Whichever route you took, keep the folder somewhere permanent. It is going to hold your real work. (If you move it later, setup's memory step needs redoing. The vault notices and tells you.)

### Step 3: open it in Obsidian

A vault in Obsidian is just a folder of markdown files.

1. Open Obsidian.
2. Click **Open folder as vault**. (If another vault is already open, click its name in the bottom-left corner first, then **Open another vault**.)
3. Pick the folder from Step 2.
4. If Obsidian asks whether you trust the author of this vault, click **Trust author and enable plugins**.

You should see folders in the left sidebar: `brand`, `context`, `memory`, `references`, `projects`, `playbooks`, `decisions`. Click any note to read it.

### Step 4: open the same folder in VS Code

1. In VS Code: **File**, then **Open Folder...** (on a Mac, **File**, then **Open...** works too).
2. Pick the vault folder itself: the one with `CLAUDE.md` directly inside it. Not the folder around it, and not a folder inside it.
3. VS Code asks: **Do you trust the authors of the files in this folder?** Click **Yes, I trust the authors**. If you click No, VS Code opens the folder in Restricted Mode, and Claude Code does not work there.

### Step 5: open Claude Code and sign in

1. Click **Claude Code** in the status bar at the bottom right of the window. (Or click the Spark icon, a small starburst, in the bar on the far left, then start a new session from the list it opens.)
2. The first time, a sign-in screen appears. Click **Sign in** and finish in your browser.
3. If Claude Code asks whether you trust this folder, say yes.

**What to expect:** depending on its permission mode (shown at the bottom of the Claude Code box), Claude Code may ask before it writes a file or runs a command. Setup writes a dozen or so files and runs a few checks, so the first run is the busiest it ever gets. Read each request and approve it. That is the design, not a fault.

### Step 6: say "set me up"

Type **set me up** in the Claude Code box and press Enter. (Typing `/onboard` does the same.)

**First, a quick check of your computer.** Before any questions, setup checks three things:

1. **Python 3.10 or newer**, which the automatic parts and Sheet Geek run on.
2. **The Sheet Geek plugin**, for spreadsheets. This vault's settings name it and switch it on, but Claude Code never downloads a plugin by itself, so it has to be installed once.
3. **Folder trust**, without which the automatic parts stay off.

For anything missing, it says what it is in one line and asks once whether to fix it. On a yes, it installs what it can itself (Sheet Geek, and Python through Homebrew on a Mac that has Homebrew) and walks you through the rest (for example the python.org installer). Your computer may ask for your password while something installs. That is your computer asking, not Claude, and Claude never sees what you type there.

**Then the conversation.** Setup asks as many questions as it needs and never more than 15. Each one is shaped by your earlier answers, and it skips anything it already knows. Between them, the questions cover:

- **Who you are, what your business offers, and who buys it.** Plain words. A few sentences is plenty.
- **Real writing of yours.** An email you sent, a post you published. **Paste it exactly as it went out.** Do not write a fresh sample in the chat: anything written inside the conversation sounds like the conversation, not like you, and every document made from it later would be slightly off.
- **Your website and your logos.** It reads your site for colors, fonts, tagline and how you describe yourself, and copies your logo files into `brand/logos/`. Have the path to your logo folder ready.
- **Money.** Where payments land and where you track them: the invoicing tool, the payment processor, the spreadsheet. Names only, never account numbers or logins.
- **Where you talk, and who with.** The apps you use with customers, with your team and in public, and the people and companies you deal with most: a name and one line each. Those seed the index Claude uses to recognize names.
- **Where your files live.** It looks first (look only, it never moves anything), drafts a map of how you organize things, and asks only about what it could not see.

**At the end** it writes everything into the vault and tells you, in a few lines, what is still missing, such as a tool you have not connected yet or a logo it could not find.

Never paste a password, an API key, or a bank number. Nothing in this vault ever needs one.

You can run setup again any time. It keeps what it already knows and asks only about what changed.

### Step 7: reload the window once

Setup tells Claude Code to keep Claude's own memory inside your vault (in `memory/claude/`), so you can read it in Obsidian. That setting takes effect when the window reloads:

1. Open the Command Palette (`Cmd+Shift+P` on a Mac, `Ctrl+Shift+P` on Windows or Linux).
2. Type **Developer: Reload Window** and press Enter.

The conversation usually comes back after the reload. If it does not, open a new one and say "where were we?": the session pulse tells Claude what just happened. You only do this once.

---

## Part 2: the terminal route

A **terminal** is a window where you type commands instead of clicking. Mac: press `Cmd + Space`, type `terminal`, press Enter. Linux: `Ctrl + Alt + T`. Windows: open the Start menu and type `powershell`.

1. **Install Claude Code** by following Anthropic's instructions at [code.claude.com/docs/en/setup](https://code.claude.com/docs/en/setup). It is one command to paste. On Windows, install [Git for Windows](https://git-scm.com/downloads/win) too.
2. **Install Obsidian and get the folder**, as in Steps 2 and 3 above.
3. **Go into the folder.** Type `cd `, a space, then paste the folder's path, and press Enter. If the path has spaces, wrap it in double quotes: `cd "/Users/sam/Documents/my vault"`.
4. **Check you are in the right place.** Type `ls` (on Windows, `dir`) and press Enter. You should see `CLAUDE.md` in the list.
5. **Start Claude Code.** Type `claude` and press Enter. If it asks whether you trust this folder, say yes.
6. **Say "set me up"**, and follow Step 6 above.
7. **Restart once at the end.** When setup says to reload, type `/exit`, then run `claude` again in the same folder.

You have changed programs once Claude Code starts: from then on you type plain English, not commands. To get back to the terminal, type `/exit`.

---

## Installing Python yourself

Setup offers to do this for you. If you would rather do it by hand, or setup could not:

| Computer | How |
| --- | --- |
| Mac | Download the macOS installer from [python.org/downloads](https://www.python.org/downloads/) and double-click it. (If you use Homebrew, `brew install python` works too.) |
| Windows | Download the installer from [python.org/downloads](https://www.python.org/downloads/). On its first screen, tick **Add python.exe to PATH**, then click **Install Now**. |
| Linux | Most already have it. Check with `python3 --version` in a terminal. If it is missing or older than 3.10, install a newer one with your package manager, for example `sudo apt install python3 python3-pip`. |

Then **quit VS Code completely and open it again** (not just Reload Window), so it can find the new Python.

After that, add the one library Sheet Geek needs for Excel files. In VS Code, open a terminal (**Terminal**, then **New Terminal**) and type:

```bash
python3 -m pip install --user openpyxl
```

On Windows, type `python` instead of `python3`.

## Installing Sheet Geek yourself

Sheet Geek is a free, open-source plugin ([github.com/Actual-Intelligence-Labs/sheet-geek](https://github.com/Actual-Intelligence-Labs/sheet-geek)) that reads spreadsheets with code. This vault's settings name it and switch it on, but Claude Code never downloads a plugin by itself, so it is installed once.

**The easy way:** say "install Sheet Geek". Claude installs it on your yes. It starts working after the next reload (**Developer: Reload Window**).

**By hand in VS Code:** type `/plugins` in the Claude Code box to open **Manage plugins**. If **sheet-geek** is not listed on the **Plugins** tab, go to the **Marketplaces** tab and add `Actual-Intelligence-Labs/sheet-geek#release`. Then click **Install** next to **sheet-geek** on the **Plugins** tab and choose **Install for this project**.

**By hand in a terminal session:** type these two lines, one at a time:

```text
/plugin marketplace add Actual-Intelligence-Labs/sheet-geek#release
```

```text
/plugin install sheet-geek@sheet-geek
```

Sheet Geek needs Python 3.10 or newer, plus `openpyxl` for Excel files (see above). CSV files need nothing extra.

---

## Later: connect your email, calendar and files

Skip this on day one. Do it once the vault feels useful.

A **connection** lets Claude read or act in a real service, like your email or your calendar, instead of you pasting things in. Two ways to add one:

1. **Connectors on claude.ai (easiest).** If you sign in with a claude.ai account, the connectors you switch on at [claude.ai/customize/connectors](https://claude.ai/customize/connectors), such as Gmail, Google Calendar or Google Drive, also work inside Claude Code.
2. **An MCP server.** MCP (Model Context Protocol) is the standard way an AI tool gets permission to talk to a service. An MCP server is a small program that speaks it for one service. In VS Code, type `/mcp` in the Claude Code box to add one. In a terminal, use `claude mcp add` with the command from that server's own instructions. Prefer a server published by the company that owns the service, and never paste a server command you found in a random comment thread: you are handing it access to a real account.

After connecting something, tell Claude in plain words, for example "I connected my email". It updates `connections.md`, and then:

- **Email:** say "import my contacts" once. Claude reads your recent mail and suggests people and companies to add to its index of names. Nothing is added without your yes.
- **A drive (Google Drive, OneDrive, Dropbox):** say "map my files", so the new drive joins the map of where your files live.
- **Anything unusual:** the brain log (the end-of-reply check that logs emails and saved files on the right note) already recognizes Gmail, Outlook and Microsoft 365, Apple Mail, Google Calendar, Outlook calendar, Google Drive, OneDrive and SharePoint, Dropbox, Box and iCloud Drive. If a mail, calendar or storage tool of yours is still missed, say "add it to the brain log lists".

---

## Did it work?

Type these in Claude Code, in order.

| Type this | You should see |
| --- | --- |
| `who am I and what do I sell?` | A correct answer drawn from your own files, with no follow-up questions and no guessing. |
| `inbox: buy stamps` | It files the thought somewhere real and tells you where, in one line. It does not just say "got it". |
| `what's the latest with` plus the name of someone you mentioned in setup | It reads that person's note before answering. If there is nothing on them yet, it says so instead of guessing. |
| `make me a one pager about what I do` | Before writing, it reads your brand, taste and voice files. The result uses your colors and sounds like you. |
| `is everything working?` | A short plain-language checklist: Python, Sheet Geek, where Claude's memory lives, the settings file, each automatic check, and folder trust. |

If all five behave, you are done.

---

## Troubleshooting

| What you see | Why | Fix |
| --- | --- | --- |
| The Claude Code panel will not open, or VS Code says **Restricted Mode** | The folder is not trusted, and Claude Code does not run in Restricted Mode. | Click **Restricted Mode** in the bottom-left corner (or run **Workspaces: Manage Workspace Trust** from the Command Palette) and trust the folder. |
| No Spark icon anywhere | The icon at the top right of the editor only shows when a file is open, and VS Code may need a reload after installing the extension. | Click **Claude Code** in the status bar at the bottom right instead, or run **Developer: Reload Window**. Check that VS Code is version 1.94 or newer (**Help**, then **About**; on a Mac, **Code**, then **About Visual Studio Code**). |
| "Not logged in" | The sign-in did not finish. | Click **Sign in** again. If no sign-in screen appears, run **Developer: Reload Window**. |
| "set me up" does not start setup, or `/onboard` is an unknown command | VS Code opened the wrong folder, so Claude Code cannot see `.claude/skills/`. | **File**, then **Open Folder**, and pick the folder with `CLAUDE.md` directly inside it. |
| I typed a loose thought and it just said "noted". Nothing automatic seems to happen. | Usually one of three things: Python is missing, the folder is not trusted, or a different folder is open. | Ask "is everything working?". If Claude finds no Python, install it (see [Installing Python yourself](#installing-python-yourself)), then quit VS Code completely and reopen it. |
| Setup said to reload and I skipped it. Claude's memory notes are not showing up in `memory/claude/`. | The memory setting only takes effect after a reload. | Run **Developer: Reload Window** once. In a terminal, `/exit` and run `claude` again. |
| I moved or renamed the vault folder | The memory setting still points at the old place. | Open the folder at its new place. The session pulse notices the mismatch and Claude fixes it in one step. Then reload once. |
| Claude Code says **Plugins changed. Run /reload-plugins to activate.** | A plugin such as Sheet Geek was just installed, and this session has not loaded it yet. | Type `/reload-plugins`, or run **Developer: Reload Window**. |
| Claude Code says a plugin is **enabled in project settings but isn't installed here** | This vault's settings name Sheet Geek, but it has not been installed on this computer yet. | Say "install Sheet Geek" (Claude installs it on your yes), or follow [Installing Sheet Geek yourself](#installing-sheet-geek-yourself). |
| Sheet Geek says Python is too old, or that `openpyxl` is missing | Sheet Geek needs Python 3.10 or newer, plus `openpyxl` for Excel files. | See [Installing Python yourself](#installing-python-yourself). |
| Sheet Geek still says Python is too old after you installed a newer one | An older Python (often Apple's) comes first on your PATH, the list of folders your computer searches for programs, so Sheet Geek finds that one first. | Ask "is everything working?". The check names the newer Python it found and the folder to put first, and Claude can make that change on your yes. Then quit VS Code completely and reopen it. |
| `pip` says **externally-managed-environment** | Your Python is managed by Homebrew or by Linux, which blocks installs into it. | Run `python3 -m pip install --user --break-system-packages openpyxl`. It installs the library for your user account only. On Ubuntu or Debian, `sudo apt install python3-openpyxl` also works. |
| On a Mac, a box pops up offering to install **command line developer tools** | Something asked for Apple's developer tools, which include an older Python. | Either answer is safe. Installing them is harmless; Sheet Geek still needs Python 3.10 or newer, so setup may offer a newer Python as well. |
| On a Mac, a box asks whether **Visual Studio Code** (or your terminal app) can access files in your Documents, Desktop or Downloads folder | Setup is looking at your folders to map where your files live. It reads folder and file names only, and never opens or moves anything. | Click **OK**. **Don't Allow** is fine too: that folder is just marked as not reachable in the map. You can change your answer later in System Settings, under Privacy & Security, then Files and Folders. |
| On Windows, the automatic parts never fire | They run through the command shell that comes with Git for Windows. | Install [Git for Windows](https://git-scm.com/downloads/win), then quit VS Code completely and reopen it. When installing Python, make sure **Add python.exe to PATH** was ticked. |
| `command not found: claude` in a terminal | The VS Code extension does not add the `claude` command to your terminal. | Use the Claude Code panel in VS Code, or install the terminal version (Part 2). |
| It asks permission for everything | Working as designed in Manual mode. It asks before writing files or running commands. | Read each one and approve it. You can change the permission mode at the bottom of the Claude Code box. Setup is the noisiest it ever gets. |
| Setup says it cannot read my website | The site blocks automated reading, or sits behind a login. | Open the site yourself, copy the About page text and any style notes, and paste them into the chat. |
| `/pdf` fails or produces nothing | No Chrome-family browser, or no Python. The PDF skill lays the page out in a real browser. | Install Google Chrome, Microsoft Edge, Brave or Chromium, and check Python with "is everything working?". |
| Obsidian's sidebar is cluttered with folders I do not care about | Obsidian shows everything by default. | Tell Claude: "hide the folder called X in Obsidian". It already hides `outputs/`, `archives/` and `.claude/`. |
| Documents still do not look like mine | `brand/brand.md` still has `{{PLACEHOLDER}}` values, so there is nothing real to apply. | Say "refresh my brand", or fill in the colors and fonts by hand. Drop logo files into `brand/logos/`. |
| It keeps asking me things I already told it | The answer landed in a note but never became a standing rule. | If it must be true in *every* session, ask Claude to add one line about it to `CLAUDE.md`. That file is read every time. Everything else is read only when relevant. |
| Nothing happened overnight | Working as designed. Nothing in this vault runs on a schedule. | Open a session when you want work done. See the safety section in [HOW-IT-WORKS.md](HOW-IT-WORKS.md) for why. |

---

Want the mental model rather than the steps? Read [HOW-IT-WORKS.md](HOW-IT-WORKS.md).
