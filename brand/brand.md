*Your brand profile. `/onboard` fills this from your website and logo folder during setup. Hand edits always win. Read automatically before anything is produced.*

**Note to the AI:** if a field below still contains a `{{PLACEHOLDER}}`, do not guess and do not invent a value. Ask the owner once, in plain language, then write the answer into this file so it never has to be asked again.

## Name and tagline

- Name: {{YOUR_BUSINESS}}
- Tagline: {{YOUR_TAGLINE}}
- Website: {{YOUR_WEBSITE}}

## What we do, in one sentence

{{WHAT_YOU_DO_ONE_SENTENCE}}

In the owner's own words, not marketing language. This line shows up on covers, headers, and the first paragraph of anything introducing the business.

## Colors

| Role | Hex code | Where it is used |
| --- | --- | --- |
| Primary | {{PRIMARY_HEX}} | The main brand color |
| Accent | {{ACCENT_HEX}} | The highlight color |
| Ink / text | {{INK_HEX}} | Body text |
| Background | {{BACKGROUND_HEX}} | The page itself |

A **hex code** is how a computer writes a color: a `#` followed by six characters, like `#1f5fdb`. Your website or your logo file already has yours. If only one color is known, use it as the **accent**. How and where your colors appear in a document is your call: tell Claude, and it goes in the Document defaults below or in [[memory/taste]].

## Typography

- Heading font: {{HEADING_FONT}}
- Body font: {{BODY_FONT}}
- Fallback fonts: {{FONT_FALLBACK_STACK}}

The **fallback** is the list of ordinary fonts to use if the real one is not on the machine building the document, for example `Georgia, "Times New Roman", serif`. Something always has to be there. Prefer fonts the owner actually owns and has installed, or fonts that load free from Google Fonts. A font that is not present on the machine building the document will silently swap for something else, and the result will not look like the brand at all. If you do not know your fonts yet, leave these blank: documents then use a plain, neutral typeface rather than a guess.

## Logo files

| File | When to use it | What surface it belongs on |
| --- | --- | --- |
| {{LOGO_PRIMARY_FILE}} | {{WHEN_TO_USE_PRIMARY}} | {{PRIMARY_SURFACE}} |
| {{LOGO_ALT_FILE}} | {{WHEN_TO_USE_ALT}} | {{ALT_SURFACE}} |

Files live in `brand/logos/`.

**Warning:** a logo drawn for a dark background will look washed out, grey, or invisible on a white page, and a dark logo disappears on a black cover. That is why there are usually two versions of the same mark. Check which surface the document uses before choosing the file.

## Tone in three adjectives

{{TONE_ADJECTIVE_1}}, {{TONE_ADJECTIVE_2}}, {{TONE_ADJECTIVE_3}}

## Logo rules

These protect the brand itself, so they hold for every document:

- Never stretch, squash, rotate, or recolor the logo. Scale it proportionally or leave it alone.
- Never place a light-on-dark logo on a white page, or a dark logo on a dark background.
- Never invent, trace, redraw, or AI-generate a logo. Always use the real file from `brand/logos/`. If the right file is missing, ask for it.

Any other rule about how your documents look comes from you. When you state one, it goes in the Document defaults below or in [[memory/taste]].

## Document defaults

| Document type | Default look |
| --- | --- |
| Proposal | {{PROPOSAL_DEFAULTS}} |
| One-pager | {{ONE_PAGER_DEFAULTS}} |
| Internal note | {{INTERNAL_NOTE_DEFAULTS}} |
| Social post | {{SOCIAL_POST_DEFAULTS}} |

Describe each in a phrase or two: cover page or no cover page, logo placement, how dense the type is, whether the accent color appears.

These start empty on purpose. The interview does not ask about them, because nobody can describe their own document defaults before they have seen one. Instead, the first time the `pdf` skill builds each type it writes what it did into the matching row here. From the second one onward, "make me a one-pager" is a complete instruction. You can overwrite any row by hand at any time, and a hand-written row always wins.

## Related

- [[brand/README]] how this file gets filled in and used
- [[memory/taste]] preferences that override or refine these defaults
- [[references/voice]] how the words themselves should sound
