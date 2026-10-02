*The running record of what you like and dislike about the work Claude produces. You do not have to write in this file. It grows every time you react to something.*

This is the file that stops the output from being generic. Your own writing (in [[references/voice]]) sets your style. This file holds the corrections on top of it.

## How it works

1. Claude makes something. A draft email, a one-pager, a caption.
2. You react. "Too long." "Stop opening with a summary." "That closing line is right, keep it."
3. That reaction becomes one line in this file, with the general principle behind it.
4. Before Claude makes anything else, it reads this file. A hook reminds it every time you ask for something to be made, so there is no command to remember.

The second half of step 3 is the important part. If you say "that proposal was too long", the useless version of the rule is "the proposal was too long". The useful version names the reason, so it applies next time too, for example `- [doc: proposal] Keep it to two pages -> the people who approve proposals read them on a phone between meetings`. (That line is an example of the format, not a rule that ships.)

## Scope

Not every preference is universal. Some are true for everything you make. Some belong to one client, or to one kind of document. So every entry carries a scope tag in square brackets, which stops a rule you set for one client from quietly leaking into another client's work.

- `[global]` applies to everything
- `[client: NAME]` applies only to work for that client
- `[doc: TYPE]` applies only to that kind of document, for example `[doc: proposal]` or `[doc: social post]`

## Format

Every entry is one line:

`- [scope] the thing -> the principle behind it`

## Global (applies to everything)

- [global] Never use an em dash (the long dash) as punctuation -> it is the most recognizable tell of machine-written text, and a period, a comma, a colon or parentheses does the same job

That is the only rule that ships with the vault. Everything else here comes from you.

## Per client or project

Nothing here yet.

Rules for one client or one kind of document go here, under a heading with that client's name or that document type, and each line still carries its tag. The heading is how you read the file. The tag is how a search or a skill finds the rule from anywhere else.

## Note to Claude

Read this file before producing anything. When the owner states a preference, in any words, append it here in the format above, with the right scope and the principle behind it, tell them in one line, then carry on with the task. A preference that contradicts an existing line replaces that line; never keep both.

## Related

- [[references/voice]] how the owner writes, which sets the style
- [[brand/brand]] how the owner's work looks
- [[decisions/log]] decisions, which are different from preferences
