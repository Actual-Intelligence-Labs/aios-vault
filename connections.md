# Connections

The outside tools you use (email, calendar, file storage, the place money lands, chat, social media) and whether Claude can reach each one. A tool Claude can reach is a live link, not a copy you paste in: once your email is reachable, you can ask "what did the client say last week?" and Claude goes and looks.

Nothing is reachable out of the box. That is on purpose. You connect each tool yourself, and this page is the record of what you use and what Claude can see.

## Your tools

| Tool | Used for | Can Claude reach it? | Signed in as | Last checked |
| --- | --- | --- | --- | --- |

Setup adds a row for each tool you name, and Claude adds one whenever a new tool comes up. Example of a finished row, for the shape only: `| Gmail, work account | customer email; meeting invites | yes, the Gmail connector on claude.ai | sam@example.com | 2026-03-14 |`

## What goes in each column (Claude relies on this)

- **Tool:** the product, plus the account or folder when it matters, such as `Google Drive, the shared Clients drive`.
- **Used for:** what you use it for, in plain words, as many as apply: payments coming in, bookkeeping, customer email, team chat, calendar, to-dos, meeting notes (and where they land), files, social media, newsletter. If you use nothing for something yet (say, nothing tracks money), write that on a row of its own, like `| (nothing yet) | bookkeeping | not yet | | 2026-03-14 |`.
- **Can Claude reach it?:** `yes`, plus how, or `not yet`. The ways a tool becomes reachable:
  - a connector you switched on at claude.ai, or a connection you added in Claude Code (an "MCP server": MCP is the standard way an AI tool gets permission to use an app like Gmail; you approve it once, in the app's own sign-in screen);
  - a small script, written by you or Claude, that talks to the tool directly;
  - a file you export from the tool (a spreadsheet or a data file) and drop into the vault. The easiest to start with, and the quickest to go stale.
- **Signed in as:** the account name or email address. Never a password, never a key.
- **Last checked:** the date someone last confirmed it works, written `YYYY-MM-DD`.

Claude counts a tool as reachable only when its row says `yes` and the tool really shows up in the session. (Tables from an older version of this vault say `mcp`, `script` or `export` instead of `yes`; those count too.) Anything else means Claude cannot reach it and says so instead of pretending. For example, with no calendar reachable, a time-bound thought goes to `tasks.md`, and Claude tells you, rather than claiming it booked an event.

## How to connect something

Two ways, easiest first:

1. **A connector on claude.ai.** If you sign in to Claude Code with a claude.ai account, the connectors you switch on at [claude.ai/customize/connectors](https://claude.ai/customize/connectors) (Gmail, Google Calendar, Google Drive and many more) also work inside Claude Code.
2. **An MCP server.** In VS Code, type `/mcp` in the Claude Code box to add one. In a terminal, run `claude mcp add` with the command from that server's own instructions. Prefer a server published by the company that owns the service. Never paste a server command from a random comment thread: you are handing it access to a real account.

A new connection shows up in sessions you start after adding it, so open a new session (or reload the window) before trying it. [INSTALL.md](INSTALL.md) has the same steps with more detail.

## When you connect email, a calendar, or file storage

Tell Claude in plain words, for example "I connected my email". Then:

1. **The row.** Claude marks the tool `yes`, with how it connects, the account, and today's date.
2. **Email:** say "import my contacts" once. Claude reads your recent mail and suggests people and companies for [[context/who-and-what]], the index it uses to recognize names. Nothing is added without your yes. After that, new names are added as they come up.
3. **Storage** (Google Drive, OneDrive, Dropbox, and the like): say "map my files", so the new location joins [[context/where-files-live]].
4. **The brain log.** At the end of every reply, an automatic check called the brain log looks for an email sent or drafted, a calendar event changed, or a file saved to or shared from cloud storage, and makes sure it was logged on the right person or project note. It spots those by the names of the tools that did them, using short word lists at the top of `.claude/hooks/brain_log.py`. Gmail, Outlook and Microsoft 365, Apple Mail, Google Calendar, Outlook calendar, Google Drive, OneDrive and SharePoint, Dropbox and Box are already on the lists, and a file saved into a cloud-synced folder on this computer (iCloud Drive included) counts too. If a tool of yours is still missed, say "add it to the brain log lists".

If getting a tool to work took real effort, ask Claude to keep a short page about it in `references/` (what finally worked, what tripped you up, how signing in goes, never the key itself), so nobody has to figure it out twice.

## Safety

Never paste an API key, token, password, or account number into this file or any other file in this vault.

A **key** or **token** is a long string of characters that proves to a service that a request is yours, so anyone holding it can act as you. This vault is plain text, so anything written in it is readable by anything that reads the folder, and it may be copied to a backup or shared with someone later.

Keys belong in one of two places instead:

- **The tool's own sign-in screen.** Most connections are set up by signing in once, and the tool remembers it. Nothing lands in a file. This is the normal case.
- **A `.env` file**, if a script truly needs one. That is a plain text file named exactly `.env`, at the top of this folder, holding one `NAME=value` line per secret. This kit's `.gitignore` already excludes it, so git never copies it anywhere.

If you ever find a secret sitting in a vault file, delete it and then **rotate** it, which means going into that service and generating a fresh key so the exposed one stops working. Deleting alone is not enough: the old one still opens the door.

## Related

- [[CLAUDE]] the house rules, including what counts as reachable
- [[context/who-and-what]] the index of names that email import adds to
- [[context/where-files-live]] the file map that storage connections feed
