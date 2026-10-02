---
name: "{{PLAYBOOK_NAME}}"
trigger: "{{WHAT_STARTS_THIS, e.g. a new client signs the contract}}"
owner: "{{WHO_IS_RESPONSIBLE}}"
gated-steps:
  - "{{STEP_THAT_ONLY_YOU_FIRE}}"
  - "{{STEP_THAT_ONLY_YOU_FIRE}}"
---

# {{PLAYBOOK_NAME}}

## When to run this

{{THE_TRIGGER, in one or two sentences. Be specific about the moment it starts, not the general topic. "A new client signs" is a trigger. "Client management" is not.}}

Do **not** run this when: {{THE_LOOKALIKE_SITUATION_THAT_NEEDS_SOMETHING_ELSE}}

## What done looks like

A checklist, not a feeling. If you cannot tick every box, it is not done.

- [ ] {{OBSERVABLE_RESULT, e.g. the client's note exists in projects/ with scope and price filled in}}
- [ ] {{OBSERVABLE_RESULT, e.g. the welcome email is sent}}
- [ ] {{OBSERVABLE_RESULT, e.g. the kickoff call is on the calendar}}
- [ ] {{OBSERVABLE_RESULT}}

## Steps

Each step is tagged with who does it.

- `[AI]` the AI does it on its own.
- `[GATED: you press it]` the AI prepares it, shows you, and waits. You fire it.

Anything that leaves your control (sending, pushing, deploying, publishing, paying) is always gated.

Two filled-in examples so the convention is unmistakable:

1. **[AI]** Read the signed contract at {{CONTRACT_LOCATION}} and pull out scope, price, payment schedule, and key dates. Quote the document. Never guess a number.
2. **[GATED: you press it]** Draft the welcome email to {{CONTACT_NAME}} in your voice (from `references/voice.md`) and leave it as a draft. **You send it.**

Now your steps:

3. **[AI]** {{WHAT_THE_AI_DOES, and the actual file or tool it uses, e.g. create the client's note with /new-node}}
4. **[AI]** {{WHAT_THE_AI_DOES, naming the actual file or tool}}
5. **[GATED: you press it]** {{WHAT_GETS_PREPARED, and what you do to fire it}}
6. **[AI]** {{WHAT_THE_AI_DOES, naming the actual file or tool}}

## What to record when it is finished

Where the outcome gets written down, so the next run starts from something real.

- **The note:** rewrite the dated status line at the top of the client or project note (`**Status (YYYY-MM-DD):** ...`), and append a dated line under its `## Notes`
- **Files:** anything this playbook produced goes where `context/where-files-live.md` says, with one dated line in the note's `## Files` section
- **Decisions:** anything you chose and could be asked about later goes in [[decisions/log]] with the reason
- **Tasks:** anything still open goes in [[tasks]] as a `- [ ]` line, linked back to the note
- **Numbers:** {{WHERE_AMOUNTS_OR_DATES_GET_LOGGED}}

## What went wrong last time

A running list. Add a line every time this playbook bites you. This section is the whole reason a playbook beats memory: the process gets better instead of repeating the same mistake.

<!--
- {{YYYY-MM-DD}} {{WHAT_WENT_WRONG}} -> fixed by {{WHAT_CHANGED_IN_THIS_PLAYBOOK}}
-->
