---
aliases: []
type: client            # client / company / project / person
status: active          # active / paused / done
started: "{{YYYY-MM-DD}}"
tags: []
---

# {{NODE_NAME}}

**Status ({{YYYY-MM-DD}}):** {{ONE_LINE: where this stands today and what happens next. Rewritten with a new date whenever it changes.}}

## What this is

{{ONE_PARAGRAPH. What this engagement actually is, in plain language. What they do, what you are building or delivering, and why they came to you. Write it so a stranger could read it cold and understand the situation.}}

## Who

| Name | Role | How to reach them |
| --- | --- | --- |
| {{FULL_NAME}} | {{ROLE, e.g. decision maker}} | {{EMAIL_OR_CHANNEL}} |
| {{FULL_NAME}} | {{ROLE, e.g. day-to-day contact}} | {{EMAIL_OR_CHANNEL}} |

Each person here also gets a row in [[context/who-and-what]], with this note as their home, so their name pulls up this note in any session.

**Where we talk:** {{THE_SHARED_CHANNEL_OR_THREAD, e.g. email, a shared chat channel}}

## What we agreed

**Rule: quote the source document. Never guess a number.**
If a figure is not written down somewhere you can open, do not put it here. Write `unconfirmed` instead. A wrong number in this section will get repeated in a proposal, an invoice, and an email before anyone notices.

- **Scope:** {{WHAT_IS_INCLUDED}} (source: {{CONTRACT_OR_PROPOSAL_NAME}})
- **Explicitly not included:** {{WHAT_IS_OUT_OF_SCOPE}}
- **Price:** {{AMOUNT_AND_TERMS}} (source: {{CONTRACT_OR_PROPOSAL_NAME}})
- **Payment schedule:** {{DEPOSIT_AND_MILESTONES}}
- **Key dates:** {{KICKOFF}}, {{DELIVERY}}, {{RENEWAL_OR_END}}

Decisions behind these, with the reasoning, are logged in [[decisions/log]]:

- {{YYYY-MM-DD}} {{ONE_LINE_DECISION}}
- {{YYYY-MM-DD}} {{ONE_LINE_DECISION}}

## Files

**Folder:** {{LINK_OR_PATH to the folder that holds this client's files, following [[context/where-files-live]]}}

One dated line per file, oldest at the top. The files themselves stay where you keep files; this note only points at them. When a newer version replaces a draft, update that line. Keep the lines for anything sent or signed.

<!--
- {{YYYY-MM-DD}} [{{TITLE}}]({{LINK}})            for a file in cloud storage
- {{YYYY-MM-DD}} {{TITLE}}: `{{PATH}}`            for a file on this computer
-->

## Open threads

What is unresolved right now. Delete a line when it closes.

- {{THING_WAITING_ON_THEM}}
- {{THING_WAITING_ON_YOU}}
- {{QUESTION_NOBODY_HAS_ANSWERED_YET}}

## Meetings

Newest at the top. `/meeting-notes` adds entries here in exactly this format, so leave the shape alone.

<!--
### {{YYYY-MM-DD}} {{MEETING_TITLE}}

**Attendees:** {{NAME}}, {{NAME}}
**Source:** [{{DOC_NAME}}]({{LINK_OR_PATH}})

**Decisions**
- {{WHAT_WAS_DECIDED}}

**Action items**
- [ ] {{TASK}} ({{OWNER}}, due {{YYYY-MM-DD}})
- [ ] {{TASK}} ({{OWNER}}, due {{YYYY-MM-DD}})

**Follow-ups**
- {{THING_TO_CHASE_NEXT_TIME}}
-->

## Notes

Loose thoughts about this project land here automatically. When you say something in passing that belongs to this client, it gets added as a dated bullet instead of disappearing.

<!--
- {{YYYY-MM-DD}} {{THE_THOUGHT, one line, written the way you said it}}
-->

## Taste for this client

Preferences that apply **to this client only** live in [[memory/taste]], each on a line tagged `[client: {{NODE_NAME}}]`. Keeping them there means every document the AI makes reads them, whatever note it starts from. Preferences that apply to all your work go in the same file, tagged `[global]`.
