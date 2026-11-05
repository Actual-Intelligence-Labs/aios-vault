---
name: optimize-vault
description: Make a vault lighter so every chat loads less, without losing a line. Use when the owner says "optimize my vault", "clean up my vault", "clean up my brain", "de-bloat my vault", "tidy my vault" or "my vault is slow or uses too many tokens". Update my vault runs these steps too, so do not offer it right after an update that ran them. Makes a save point, measures, shows one plan, changes only what the owner says yes to, proves nothing was lost, then writes a plain report.
---

# Optimize my vault

Every chat loads `CLAUDE.md`, the memory index (`memory/claude/MEMORY.md`), every skill description and the session briefing. Some files also grow forever: `decisions/log.md`, `tasks.md` and `inbox.md`. This skill shrinks what every chat loads and moves old entries into dated files in `history/`, word for word, with a link left behind. Nothing is deleted and no rule is reworded.

**Read from GitHub by a vault without this skill.** If the owner pasted a link and asked you to follow these steps, the vault is older than this skill. Follow the update-vault skill in that same download instead (`.claude/skills/update-vault/SKILL.md`). It brings the vault up to date and runs these steps in the same run, with one list and one yes.

**Sent here by update-vault?** Then skip Step a and Step b. Update-vault makes the one save point for the whole run, and it is what brings the vault up to date, so the version check would only send you back to it. Do Steps c and d before its list, and Steps e to g after its changes, as it says. Fold your plan and your questions into its list, under its one yes.

## What it does, and what it never does

- **It never deletes a line.** Lines move word for word into `history/` or into a hub note, and a link points at them. A check proves it before and after writing.
- **It never rewords a rule.** In the memory index, a line under a rules heading, or a line that states a default, a never or an always, stays exactly as it is. Only plain pointer lines move.
- **It changes nothing until the owner says yes** to one plan. Ask only real questions: the ones the scripts list. One yes covers the rest.
- **It keeps a copy** of every file it changes in `archives/optimize-YYYY-MM-DD-HHMM/`, with a list of what changed (`manifest.json`). There, `CLAUDE.md` is saved as `CLAUDE.old.md` and `.claude/` as `dot-claude/`, so Claude never reads a second set of rules.
- **It writes only inside the vault,** plus this computer's temp folder for its numbers. The save point is a local git commit, or one packed file in `archives/save-points/`. The only thing that ever goes beside the vault folder is a file the owner agrees to move out, such as a key.
- **It never pushes, sends or posts.** A save point in git is a local commit.
- **It never opens, reads or shows** what a secret file says. It names the path and the kind only.
- **Never run an apply command in a turn that also sends or drafts an email or changes a calendar.** Keep this work in its own turns.

| Part | Budget | What the skill does over it |
| --- | --- | --- |
| Memory index | 75 lines and 10,000 characters | groups plain pointer lines into hub notes |
| `CLAUDE.md` | 18,000 characters (a warning) | over the limit only: lists lines a memory note repeats word for word; one goes only when the owner names it |
| `decisions/log.md` | 40,000 characters, or entries older than 90 days | moves old entries to `history/decisions/` |
| `tasks.md` | 20 done items | moves done items to `history/tasks/` |
| `inbox.md` | 100 lines | moves old entries that say where they went to `history/inbox/` |
| Each skill description | 300 to 500 characters (over 600 is too long) | a shorter text that keeps every quoted trigger phrase |

## How to run the scripts

Run everything from the vault folder (the one that holds `CLAUDE.md`). The scripts need Python 3.9 or newer and nothing else. Each command starts by asking `run.sh` which Python to use:

```sh
PY=$(sh .claude/hooks/run.sh --which) && [ -n "$PY" ] && "$PY" .claude/skills/optimize-vault/scripts/measure.py --vault .
```

If `run.sh --which` prints nothing, there is no Python 3.9 or newer: say so in one line and offer to set it up (the `onboard` skill's install check has the steps). Every script is a dry run unless it gets `--apply`, and each one takes `--json`. Below, `"$PY" scripts/NAME.py` is short for that full command.

A helper script you write yourself runs as a heredoc on stdin (`"$PY" - <<'EOF'`, then the script, then `EOF`), never as a script file in `/tmp` or anywhere else outside the vault. Read this file, and every file it tells you to read, with the Read tool, never with `cat`: a long `cat` output gets cut short.

While it runs, the owner reads every line you write, so keep them short, one per stage at most, and in the report's plain words: say what you are doing for them, such as "Measuring how much Claude reads first." or "Saving a copy of everything first." Never a step letter, a script or file name, or inside words such as fingerprint, sha, hub, pointer line or index. The words in this skill and in the scripts' output are for you, not the owner: never pass them on. Write at most one line per stage, and use these lines word for word, in this order, skipping any stage that does not happen:

- "Measuring how much Claude reads first."
- "Saving a copy of everything first."
- "Moving old decisions, finished to-dos and old inbox notes to the history folder."
- "Grouping the memory lines that only say where a note is onto topic pages."
- "Checking that every rule is still word for word."
- "Measuring again to see what changed."

Where each line goes (this is for you; never copy it into a line): measuring is Step c. Saving, moving and grouping are Step e: the save point, the tidy-up, then the memory lines. Checking and measuring again are Step f: the proof, then the numbers after. The checking line is for that proof only, never for checking your own work along the way.

These progress lines are for when this skill runs alone. When update-vault sent you here, use only its progress lines, which have these same words for these stages. A long stage still gets one line only, even when it takes many steps. Never write a line about reading or checking a script, checking your own work, planning, or to say you are still working: work with no ready line carries on under the last line you wrote. Between those lines, write nothing to the owner except a question that needs their answer, or a one-line message these steps ask for when they stop (no Python 3.9 or newer, a vault already tidy, not enough disk space, an older vault). After "Measuring again to see what changed." write nothing at all until the report: the report, the log entry and the last check get no line. Then start the report message with the report's own first line, its heading, with nothing before it.

**Check before you show it.** Before you show the owner any other text before the report (anything that is not a progress line or the Step d plan; a question you write yourself is checked too), check it against the report's words to watch (in "The report" below) and against the rule for progress lines above: no step letter, no script or file name, no inside words. If it has any of them, say it again without them, in the report's plain words. Leave text out only when nothing in it needs saying: a stop, a failure or an offer to fix is always said, in one plain line.

In the Bash tool (it runs zsh), print a divider with `echo '---'`, with the quotes: a bare `echo ====` fails and stops the commands after it.

## Step a. Save point check

```sh
"$PY" scripts/save_point.py --vault .
```

This changes nothing. It says what the save point will be, and how big: a local git commit if the vault folder is its own git repository, or else one packed file inside the vault, in `archives/save-points/`. It leaves out `archives/`, `outputs/`, files that look like a key or a password, and files over 5 MB. The save point itself is made in Step e, right after the owner's yes, so nothing is written before they have seen the plan.

If it says a save point is **not needed** (the vault is as the last run left it and nothing needs changing), tell the owner their vault is already tidy, run Step c's measure to get the numbers, show them, and stop. Write no log entry. If it says the save point is big and to ask first, put that question in the Step d list. If it says there is not enough free disk space, tell the owner and stop.

**Done:** the script printed what the save point will be, or that none is needed.

## Step b. Version check

```sh
"$PY" scripts/version_check.py --vault .
```

If it says **older**, tell the owner in one line why, then run the update-vault skill instead and stop here. Update-vault does the update and these steps in the same run, with one list and one yes, so do not start this skill again afterwards. If it says the vault is **newer** than this copy of the skill, use the vault's own copy.

**Done:** it says **current**, or you handed the run to update-vault.

## Step c. Measure

```sh
"$PY" scripts/measure.py --vault . --save-before --doctor
```

Put in the Step d plan message (or, when update-vault sent you here, in its Step 4 list), in plain words, how many pages Claude reads before every answer (the "For the owner" line: one page is about 3,000 characters) and what is on the "To do" line. Do not send them as a line of their own. Never say tokens to the owner. `--save-before` keeps these numbers in the temp folder for Step f.

**Nothing to do?** If the "To do" line is empty, nothing needs changing. Still write the report (see "The report" below), with "What changed" saying in one line that nothing needed to move. Save it, show it, and stop: no save point, no log entry. The saved report also tells the session briefing that the first cleanup has run, so it stops offering one.

**Done:** the numbers are saved and you know which parts are over budget.

## Step d. Plan

Run each dry run that the "To do" line calls for:

```sh
"$PY" scripts/tidy.py --vault .
"$PY" scripts/memory_index.py plan --vault .
"$PY" scripts/fixes.py repeats --vault .
"$PY" scripts/fixes.py skills --vault .
"$PY" scripts/fixes.py gitignore --vault .
"$PY" scripts/fixes.py scan --vault .
"$PY" scripts/fixes.py save-points --vault .
```

Then show the owner **one** message: a numbered list of every change, each with its before and after numbers, then the questions. Ask only these, and only when they come up:

1. **Old decisions that hold a rule** (tidy lists them as QUESTION). Search `CLAUDE.md` and `memory/claude/` for each rule first. If the rule lives there too, the entry moves with no question. If it does not, ask: keep this entry in the log, or move it? Suggest keeping it.
2. **Inbox entries that do not say where they went.** Ask whether they move too. Suggest leaving them.
3. **Memory index lines.** Show the numbered lines that would move into each hub. The owner can name any number to keep in the index.
4. **`CLAUDE.md` lines a memory note repeats.** Only listed when `CLAUDE.md` is over its limit. The owner wrote every one of them, so each stays unless the owner names its number.
5. **Secret files and big media files.** Ask whether to move each out of the vault, and say where to (the folder beside the vault). If one was ever saved in git history, say plainly that moving it does not remove it from history: the owner should change that key or password at the service that issued it.
6. **Save points at the end of every session.** Offer to turn them on, but only when `fixes.py save-points` says the vault is a git repository. If it is not one, say in one line that save points need git, and that the owner can ask you to set git up in this folder later.

For a skill description over 600 characters, the owner wrote every word of it, so cut, never reword. When `fixes.py skills` prints a text with the repeats cut, use that text exactly as it prints it: it keeps the first time each sentence is said, word for word. Otherwise write the new text yourself by cutting whole sentences or parts of them: 300 to 500 characters, one line, every quoted trigger phrase kept, no colon followed by a space, and every word you keep exactly as the owner wrote it. Never drop what the skill does or where it saves its work. Show the before and after. Only shorten the owner's own skills; the template's skills come from update-vault.

If `CLAUDE.md` is over 18,000 characters, say so and name its three biggest sections. Do not move anything else in it. Mention any note over 40 KB, any memory note the index does not reach, and any second `CLAUDE.md` or skills folder inside the vault, as things the owner may want to look at later.

**Done:** the owner said yes, or yes with the numbers or items to skip. No file has changed yet.

## Step e. Apply

Pick one run folder for every command in this run, for example `archives/optimize-2026-11-04-1530` (today's date and time), and write it in place of `"$R"` in each command (a shell variable does not carry over from one command to the next). Make the save point first. Then run, in this order, only what the owner agreed to:

```sh
"$PY" scripts/save_point.py --vault . --apply [--big-ok]
"$PY" scripts/tidy.py --vault . --apply --expect-sha <sha from the tidy dry run> --run-dir "$R" [--rules-checked] [--keep "title"]... [--include-unrouted]
"$PY" scripts/memory_index.py apply --vault . --expect-sha <sha from the plan> [--skip 3,7] --apply --run-dir "$R"
"$PY" scripts/fixes.py repeats --vault . --remove 2,5 --apply --run-dir "$R"
"$PY" scripts/fixes.py skills --vault . --skill NAME --text "new description" --apply --run-dir "$R"
"$PY" scripts/fixes.py gitignore --vault . --apply --run-dir "$R"
"$PY" scripts/fixes.py move-out --vault . --path REL [--path REL] --apply --run-dir "$R"
"$PY" scripts/fixes.py save-points --vault . --apply --run-dir "$R"
```

Add `--big-ok` to the save point only when the owner said yes to a big one. If the save point is not made, stop: change nothing without one. `--expect-sha` makes tidy stop, changing nothing, if the plan is no longer the one the owner saw (an entry was added in between); then show the new list and ask again. `--rules-checked` tells tidy you did the search in question 1. Each `--keep` names the start of an entry the owner wants to keep; it is saved in `.claude/optimize-keep.json`, so later runs keep it too. Run `fixes.py repeats` only when the owner named a line. If any command says a check FAILED, STOPPED, or that a file changed while it ran, stop, tell the owner, and offer the undo below. A file a script says it left as is (not saved as UTF-8, a link, read-only) is not a failure: say so in the report.

**Done:** every command finished without a failed check.

## Step f. Verify

```sh
"$PY" scripts/proof.py --vault . --run-dir "$R"
"$PY" scripts/reach.py --vault .
"$PY" scripts/measure.py --vault . --compare --doctor
```

`proof.py` reads the copies in the run folder and checks that every line is still in the vault (or, for a line the owner chose to drop, still in its memory note or the backup), that every rule line in the memory index is unchanged, that every memory note is still within two links of the index, that every history file is linked from where its lines came from, and that each moved-out file arrived intact. `--compare` shows the before and after numbers.

**Done:** proof says "nothing lost", the numbers went down, and the vault check (doctor) lists nothing new compared with Step c.

## Step g. Report, log and summary

First write the report (see "The report" below) and save it in the vault as `history/reports/YYYY-MM-DD-vault-report.md` (add the time, `-HHMM`, if that name is taken). Then:

```sh
"$PY" scripts/fixes.py log --vault . --text "one line: what changed, pages read at the start of every chat before and after, the run folder. Report: [[history/reports/YYYY-MM-DD-vault-report]]" --apply --run-dir "$R"
"$PY" scripts/save_point.py --vault . --done --apply
```

The first adds one dated entry to `decisions/log.md` that links the report. The owner reads that log, so write its text in the report's plain words (topic pages, not hubs or pointer lines). It adds nothing when this skill's own steps changed nothing; if update-vault changed files in this run, add that same entry yourself at the bottom of the log, in the same format. The second records the vault's state, so a second run right away changes nothing; in git it also commits the result locally.

Then end the run in chat, as "Showing it in chat" below says: the report read back from the saved note, word for word, then a **Fine print:** line only when something truly needs the owner, then the last line: the smaller files load when a new session starts. When update-vault sent you here, do not show it yet: its Step 8 shows it once, at the very end of the run. How the work went (a step tried again, a check that spoke up) is never shown: the run folder's `manifest.json` records it.

**Done:** the report is saved and shown, one dated entry in the log links it, and the state is recorded.

## The report

The owner does not work in AI, so write it the way you would explain it to a friend. It is the last thing they see, in chat and as the dated note, and it has exactly three short parts: how your brain was working before, what changed, and what it means for you. Use 8th-grade words and short sentences. Nothing scary and nothing blaming. Keep only the lines that are true for this run, and use the real numbers from `measure.py --compare`. Count one page as about 3,000 characters. When update-vault ran this, fold what the update changed into "What changed", in the same plain words. When the session briefing offered this run because an earlier update skipped its cleanup, fold in what that update brought too: the newest `archives/update-*/what-changed.md` lists it.

Words to watch:

- Never use the words tokens, index, hooks, context or MCP. Never name a skill, a script, a file or a folder (only "the history folder" and "your decision log"), and never write Python, git, settings or needs-review.
- Never write "description" or "trigger words". For a skill's description, say "the short summary Claude reads to know when to use it".
- Say "the notes Claude reads at the start of every chat", "Claude's list of memories" and "automatic checks".
- The first time helpers come up, say what they are: "the small helpers Claude sends off to do side jobs". Call a skill by what it does ("your weekly report steps"), never a helper.
- Never write skill or skills, hub, fingerprint, header or a version number. A skill is "your weekly report steps", never a line on "your list of skills".
- Name a part of the house rules by what it holds ("who you are", "your business", "the notes you added yourself"), never by its heading.
- Count only what the vault holds. Say "the four clients you have notes on", never "your four clients" when the notes may name more.

Keep it short enough for a tired reader: at most 7 lines under "What changed", the biggest change first, one plain idea each. Each line says what the owner gets, and where a thing now is when that matters ("Claude's list of memories now points to it"). Never a line that only says the vault is on a newer version: say what that brings them instead.

How the work went (a backup taken twice, a step tried again, a check that spoke up along the way) never goes in the report. Bookkeeping (a row added to a list, one memory linked, a version number) is left out. So is something kept on purpose that needs nothing from the owner (a photo a note shows, old inbox lines left where they are, old decisions kept in the log): the paragraph under "What changed" already says the rules did not change and nothing was deleted. Optional extras (installing a plugin, mapping files, looking through mail for more people) never appear in the report or under it: offer them later in a normal chat, when they come up. If something truly needs the owner, it goes in one short **Fine print:** line in chat, under the report, and nowhere else.

Use this shape. The numbers are only an example:

```markdown
# How your brain changed, YYYY-MM-DD

Related: [[decisions/log]]

## How your brain was working before

- Claude read about 13 pages of your notes before every answer.
- Claude's list of memories had 155 lines, and it read all of them at the start of every chat.
- Your decision log had grown to about 14 pages, and 40 finished to-dos were still on your list.

## What changed

- Claude now reads about 9 pages before every answer, down from 13.
- 91 memory lines that only said where to find a note now sit on 6 topic pages. Claude can still find every one of them.
- Old decisions, finished to-dos and old inbox notes moved word for word into dated pages in the history folder, with a link left where they were.
- New automatic checks keep Claude from showing a saved password or key, and make it ask you before anything that pays.
- The small helpers Claude sends off to do side jobs now carry less, so they use less of your plan.
- The four clients you have notes on are now on Claude's list of names, so it pulls up the right note when you mention one.
- The short summary Claude reads to know when to use your weekly report steps said the same thing three times. It now says it once, in your own words.

Your rules did not change. Claude's list of memories is only touched when it is over its size limit. Even then, only lines that just say where to find a note get grouped onto one page. Every rule line, and every line that says always, never or what Claude does by default, stays word for word. Nothing was deleted, and a save point was made first, so all of this can be undone.

## What it means for you

- Chats start faster, because Claude has less to read first.
- Each chat uses less of your plan's limit, so you can do more before you reach it.
- It is safer with passwords: Claude will not show a saved password or key, even to test it.
- To undo anything, ask Claude. It copies the old version back from the save point.
```

### Showing it in chat

1. Read the saved note back from the vault and paste its text into the chat word for word. Start the message with the report's first line, its heading, with nothing before it. Never retype it from memory, shorten it or reword it. Leave out only lines that hold nothing but Obsidian links, such as "Related: [[decisions/log]]": they help the note, and in chat they show up as brackets.
2. Under it, at most one line that starts **Fine print:**, and only when something truly needs the owner. Only these count: a file of passwords or keys still sitting in the vault, a key to change where it was issued, a part of the run that did not finish, or the one line from update-vault's Step 5 that the owner pastes themselves. At most two short sentences in all, with no file names and no backticks (the paste line itself is the one exception), and at most one offer. So copy the matching line below word for word, and add nothing to it. When more than one applies, use only the first one that does:
   - "**Fine print:** One part of the update needs one more step from you. In VS Code, click View, then Terminal, paste this line, press Enter and reload the window: <the line from Step 5>"
   - "**Fine print:** One part did not finish. Ask me to try it again."
   - "**Fine print:** An old copy of a password or key is still in your vault's history. Change it on the site that gave it to you."
   - "**Fine print:** A file with passwords or keys is still in your vault. Ask me if you want it moved out."

   Never call anything a slip, an error, a failure or a warning.
3. Then the last line. Nothing else goes between the report and that line: no list of what was kept, no optional extras, no second offer.

## Undo

- **One file:** copy it back from the run folder's `backup/` (rename `CLAUDE.old.md` back to `CLAUDE.md`, and `dot-claude/` to `.claude/`). Files the run created are listed in `manifest.json` with `"existed": false`.
- **The whole run:** with a packed save point, copy the files back out of `archives/save-points/save-point-YYYY-MM-DD-HHMM.tar.gz` (Python's `tarfile` module reads it; on a Mac or Windows a double click opens it). In git, restore the files from the commit named "Save point before optimize-vault".
- Ask before undoing anything, and make a new save point first.

## Running it again

A second run on a vault that has not changed since changes nothing: Step a says no save point is needed, and you stop. What the owner chose to keep or leave last time does not count as new work. Run it again whenever the session briefing says a file has grown. The briefing stays quiet about a size the last run could not go under (rule lines never move) until the file grows clearly past it. After update my vault there is no need: it already ran these steps.
