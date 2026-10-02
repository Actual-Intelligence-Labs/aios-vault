# Playbooks

This folder holds your **playbooks**: written processes for the jobs you do over and over.

## What a playbook is

A playbook is **the steps for a recurring job, written down in your own words**.

Onboarding a new client. Sending the monthly invoice. Publishing a post. Closing out a project. Anything you have done before and will do again.

It is a document, not a program. A person can follow it. The AI can also follow it, because the AI reads the same files you do.

## Playbook or skill? The new-hire test

There are two ways to write down a process in this vault, and they are easy to mix up. Here is the difference.

- A **playbook** is a written process. It lives in `playbooks/`. Someone reads it and follows it.
- A **skill** is a procedure the AI runs itself when the moment comes. It lives in `.claude/skills/`. You say a few words and it happens.

The test:

> If you would hand it to a new hire and say "follow this," it is a **playbook**.
> If you want the AI to just do it without you watching, it is a **skill**.

Many processes start as a playbook. You write the steps because you keep forgetting one. Then the steps stop changing, and at that point it is ready to become a skill.

Turning one into a skill takes one sentence. Say "turn the client onboarding playbook into a skill" and `/new-skill` reads the playbook, builds the skill from it, and registers it in [[skills-registry]] so you can find it later. The playbook stays where it is as the human-readable version.

## When a playbook gets written

Two different repeats, two different results:

- **You do the same job by hand for the third time:** that is a process you are rebuilding from memory each time. The AI points it out and offers to write the playbook with you. You do not have to catch it yourself, but if you notice first, say "write this up as a playbook" while it is fresh. A rough playbook beats a perfect one you never wrote.
- **The AI does the same kind of job for the second time:** it turns that into a skill on its own, so the next run comes out the same way, and tells you in one line. See `/new-skill`.

## Safety convention: who presses the button

Every step in a playbook is tagged with **who does it**. This is the most important convention in this folder, and it exists so that nothing leaves your control by accident.

- `[AI]` means the AI does this step on its own. Reading, drafting, organizing, calculating, filing, formatting. Nothing here can embarrass you or cost you money.
- `[GATED: you press it]` means the AI prepares it and then **stops**. It shows you the result and waits. You are the one who fires it.

These kinds of step are **always gated**, no exceptions, in every playbook:

| Step type | Why it is gated |
| --- | --- |
| Sending anything outside (email, message, DM, text) | It cannot be unsent |
| Pushing code to a shared repository | Other people build on it immediately |
| Deploying | It is live for real users |
| Publishing (a post, a page, a listing) | It is public and indexed |
| Paying, sending an invoice, or moving money | Money that has moved is hard to get back |

Rule of thumb: if undoing it means an apology, it is gated.

When you write a new playbook, tag the steps as you go. If you are unsure, gate it. An extra confirmation costs three seconds. A sent email costs a lot more.

## Index

| Playbook | When it runs | Gated steps |
| --- | --- | --- |
<!-- Example row (write the link without the backticks): | `[[playbooks/client-onboarding]]` | A new client signs | welcome email, shared folder invite | -->

## Starting one

Copy `_TEMPLATE.md`, rename it in kebab-case (all lowercase, hyphens instead of spaces, for example `client-onboarding.md`), and fill it in. Or just describe the process out loud and ask for it to be written up. Either way, add a row to the index table above so you can find it again.

Any file a playbook produces goes where [[context/where-files-live]] says, with a dated line in the right note's `## Files` section. The playbook itself only holds the steps.
