---
name: new-skill
description: Make or fix a skill so a job comes out the same way every time. Use when the owner says "make a skill that...", "save how we did this", "remember how to do this", "turn this playbook into a skill", "I keep doing this, can you automate it", or "that skill did the wrong thing". Also runs on its own the second time the AI does the same kind of task, when the owner walks the AI through a process worth keeping, and when a skill fired at the wrong moment or gave a wrong result.
---

# New skill

Turns a job into a skill the AI picks up on its own from then on, and repairs a skill that misbehaved.

## What a skill is (read this first if you are new)

A skill is a folder inside `.claude/skills/` holding one file, `SKILL.md`. The top of the file is a short description. The rest is the steps.

At the start of every session the AI reads the description of every skill it has. When a request matches one, it opens that skill and follows the steps. That is why nobody has to remember a command: saying the job in your own words is enough. The slash command (`/pdf`, `/capture`) is only a shortcut.

A skill is a habit you explain once.

## When this runs

**On its own, without being asked:**

- **The second time the AI does the same kind of task.** Same shape, different inputs: a second proposal, a second monthly summary, a second time cleaning up the same export. Build the skill from how the job was actually done, register it, and tell the owner in one line.
- **The owner walks the AI through a process** step by step, and it will clearly come up again.
- **A skill misfired.** It started when it should not have, stayed silent when it should have started, or produced the wrong result. Go to "Fixing a skill that misfired" at the bottom.

**When asked:** "make a skill that...", "save how we did this", "remember how to do this", "turn the onboarding playbook into a skill", or `/new-skill`.

**Not this skill:**

- **The owner doing a task by hand for the third time.** That calls for a playbook, a written process a person can follow: say so and offer to write one (see `playbooks/README.md`). A playbook whose steps have stopped changing can become a skill later.
- **A one-off job.** Just do it.
- **A fact or a preference.** A fact goes in its note, a like or dislike goes in `memory/taste.md`, a lesson about how to work with the owner goes in `memory/claude/`. None of those are skills.

## Step 1: Check what already exists

Look at every skill this session can see, not just this folder:

- this vault's skills, in `.claude/skills/` and listed in `skills-registry.md`
- personal skills the owner installed for all their projects, in `~/.claude/skills/`
- skills that came with plugins (shown with the plugin's name, for example `sheet-geek`)
- the skills built into Claude Code

If one of them already does most of the job, improve that one instead of adding a second. Two skills with near-identical descriptions make the AI guess between them, and it guesses wrong.

A plugin's skill or a built-in skill cannot be edited from here. If one competes with this job, make this vault's description say plainly when to use which ("use this, not X, when ...").

Done when you can name the closest existing skill and say in one line why this one is new, or that it is an edit.

## Step 2: Choose the lightest thing that works

A repeat does not always call for a skill. Pick the lightest form that makes the job come out right next time:

| What the job needs | Make this |
| --- | --- |
| One rule that should hold in every session | one line in `CLAUDE.md` |
| A lesson about how the owner likes to work | a note in `memory/claude/` |
| Steps a person also follows, or steps that still change often | a playbook in `playbooks/` |
| Steps with judgment and file edits, that should start on their own | a skill made of instructions |
| Exact calculation, a file format plain text cannot produce, or a precise transformation | a skill plus a small script in its folder |

Each row down the table is one more thing that can break or go stale. Say which form you chose and why, in one line, before writing anything.

## Step 3: Sort it: ships now, or waits for a yes

This decides whether the skill is usable today.

- **Instructions only:** steps, rules, templates and checklists that use only what this session already uses (reading and writing vault files, searching, drafting an email, reading a connected calendar). Build it, register it `active`, tell the owner in one line. No approval needed.
- **Needs review:** it ships a script or anything else that runs; it needs a new account, key, API or connection; it can send, post, publish, pay or push by itself; or it came from outside this vault (the internet, a marketplace, someone else's folder). Build it, register it `needs-review`, tell the owner in two sentences what it does and what it touches, and do not run it until they say yes.
- **Never:** a skill that runs on a schedule, keeps running in the background, or listens for connections from other machines. If a job seems to want one of those, say so and let the owner decide.

## Step 4: Name it

- Lowercase words joined by hyphens, named after the job in the owner's own words: `weekly-invoice`, `show-notes`, `client-welcome`.
- **Unique across every skill from Step 1.** When two skills share a name, one of them gets hidden and never runs.
- The folder name and the `name:` line in the file match exactly.
- A real folder at `.claude/skills/<name>/`, never a shortcut or link to a folder somewhere else.

## Step 5: Write the description

This is where most skills fail.

**When the AI is deciding whether to use a skill, the description is the only thing it sees.** Not the steps, not the title. Just that one line.

So it has to hold the words a real person says when they want the job done, not an abstract summary.

Bad:

```yaml
description: Handles invoicing workflows.
```

Nobody says "handle my invoicing workflow." It names a category, not a moment, and it will almost never fire.

Good:

```yaml
description: Builds the monthly invoice from a client note and saves it as a PDF. Use when the owner says "send the invoice", "bill the client", "what do we invoice this month", or names a client and asks to invoice them.
```

That fires, because it quotes the trigger phrases.

Rules for the description:

- Say what it does, then "Use when the owner says..." with three to five real phrases in quotes. Include the messy, dictated versions, not just the tidy ones.
- If another skill competes, say when to use this one and when the other.
- One line, under about 1,000 characters.
- **Keep it valid.** The top block is YAML, a strict format, and one stray character makes the skill silently fail to load:
  - no colon followed by a space anywhere in the description
  - no space followed by `#` (everything after it is thrown away)
  - do not start it with a quote mark, a bracket, or a star
  - if you need any of those, wrap the whole description in double quotes and put a backslash before any double quote inside it
- Leave out `allowed-tools` (it lets a skill use tools without asking first) and `disable-model-invocation` (it stops the skill from starting on its own).

## Step 6: Write the steps

Write them from what actually happened in this session, not from theory.

- Numbered steps, in order. Each one ends on something you can check.
- Exact paths: where inputs come from and where outputs land. A file the skill makes goes where `context/where-files-live.md` says, with a dated line in the right note's `## Files` section.
- The snags hit this time, and the fix for each.
- How to check the result before calling it done.
- A "When NOT to run this" section. A skill that fires at the wrong moment is worse than no skill.
- A one-line sign-off, so every run ends the same way.
- Keep it as short as the job allows. Long reference material goes in a second file in the same folder, with a pointer to it.

The anatomy, annotated:

```markdown
---
name: weekly-invoice                 <- matches the folder name exactly
description: Builds the monthly ...  <- the trigger phrases, in quotes
---

# Weekly invoice                     <- plain title

One or two lines: what this does.    <- a human skimming knows in seconds

## When to run this
- The owner says "send the invoice"

## When NOT to run this
- The client is on a flat retainer

## Steps
1. Read projects/<client>.md for the rate.
2. ...

## Sign-off
One line: what was produced, where it went.
```

**Anything that leaves the vault gets this section, word for word:**

```markdown
## Hard stop
This skill prepares the work in full and then stops. Sending, publishing, pushing,
deploying and paying are done by the owner, never by this skill.
```

If the job's whole point is to send something, the skill still ends at "the draft is ready, here it is."

## Step 7: Register it

Add a row to the table in `skills-registry.md`, using that table's exact columns in that exact order, or the table stops rendering:

| Skill | What it does | Source | Reviewed | Runs code? | Status | You say this |
|---|---|---|---|---|---|---|
| `/weekly-invoice` | Builds the monthly invoice PDF | written here 2026-03-14, from how the March invoice was made | instructions only, owner told 2026-03-14 | no, instructions only | active | "send the invoice for Acme" |

- **Runs code?** Be honest. If it ships a script, name the language and what it touches.
- **Status** is `active` or `needs-review`, from Step 3.
- **You say this** is in the owner's words, so months later they can skim the table and remember what they have.

Skills live in a hidden folder, so Obsidian cannot link to them. If the skill serves one project, mention it by name (`/weekly-invoice`) in that project's note so the connection is findable.

## Step 8: Check that it loads and fires

- A new skill is usually picked up within seconds. If it does not appear when you type `/`, reload: in VS Code, open the Command Palette and run "Developer: Reload Window", or start a new session.
- **The owner asked for it:** have them say the thing they would naturally say. If the skill does not start, the description is what to fix: add their exact words to it and try again. Typing the slash command only proves the file exists.
- **You built it on your own:** run its first step as a dry run, or let the next real use be the test.

## Step 9: Tell the owner in one line

> Made a skill: `/weekly-invoice`. It starts when you say "send the invoice". Instructions only.

or

> Made a skill: `/weekly-invoice`. It needs your yes before its first run, because it runs a script that reads your invoice folder.

## Fixing a skill that misfired

Fix the skill, not just this one result.

- **Started at the wrong time, or never started:** fix the description. Add the phrases that should have triggered it, or a line saying when not to use it.
- **Started at the right time, wrong result:** fix the step that went wrong, or add the snag and its fix.

Then add one dated line at the very bottom of its `SKILL.md`:

```markdown
- 2026-03-14 fixed: it filed the invoice under the wrong client -> step 1 now checks the index for the canonical client name
```

Update the registry row if the trigger phrase or the sort from Step 3 changed. A fix that adds a script or new reach turns the skill back to `needs-review`.

After editing a skill mid-session, read its `SKILL.md` again before using it. A copy loaded earlier in the session does not update on its own.

## Keep the set small

Every extra skill is one more description the AI has to choose between, and similar descriptions blur together. Merge rather than multiply. Removing a skill nobody uses is a real improvement: move its folder to `archives/`, delete its registry row, and log why in `decisions/log.md`.

## Sign-off

> Built `<skill-name>` at `.claude/skills/<skill-name>/SKILL.md`, registered in [[skills-registry]] as active (or needs-review), tested with "<the phrase we tried>".
