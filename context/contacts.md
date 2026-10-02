# Contacts

*How to reach the people you deal with, and how they like to be talked to. Setup starts this file from the people you name, and Claude adds to it whenever a channel or a working style comes up.*

This is the channel and tone sheet. The full list of every person, company, project and tool, with nicknames and the note to read first, is [[context/who-and-what]]. When you say "send this to the ops lead" or "draft a note to Jordan", Claude works out who that is from [[context/who-and-what]], then reads the row here for the channel to use and the tone to take.

**Note to Claude:** never invent a contact, a role or a channel to fill a gap. If the table has no rows yet, say so instead of guessing who someone is. When a new person comes up, give them a row in [[context/who-and-what]] in the same turn, and a row here once you know how to reach them or how they like to work.

## Who is who

| Name | Who they are | How we talk to them | Notes |
| --- | --- | --- | --- |

Example of a finished row, for the shape only: `| Jordan Lee | Ops lead at Acme Corp, signs off on invoices | Email, plus a monthly video call | Likes a short summary first. Copy her manager on anything over budget. |`

Fill "How we talk to them" with the real channel: email (with the address), a shared chat, text, phone, in person. Claude uses it to pick the right register and length, and the right place to draft a message.

## Privacy

Keep this to working facts: role, channel, how they like to work, what they own.

Do not store anything sensitive about a person here: no home addresses, no health or family details, no financial details, no passwords, nothing you would not be comfortable showing them. This file is plain text in a folder you may one day sync or share.

## Related

- [[context/who-and-what]] every name, with nicknames and the note to read first
- [[context/about-business]] the business these people work with
- [[projects/README]] the client and project notes these people show up in
- [[memory/taste]] per-client preferences live there, tagged `[client: NAME]`
