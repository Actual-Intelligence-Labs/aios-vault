*What the `brand/` folder is and why it earns its place. Read it once, then mostly forget about it.*

This is the folder that makes a document come out looking like **yours** the first time you ask for one.

Without it, you get generic AI output: default fonts, a blue heading, a layout that could belong to anybody. With it, the first draft already has your colors, your fonts, your logo on the right background, and the tone you actually use.

## What is in here

- `brand.md`: your brand profile. Name, tagline, colors, fonts, logo rules, tone, and what each kind of document should look like.
- `logos/`: your actual logo files, copied in from wherever they live on your computer.

This is one of only two places in the vault that hold real files rather than links. (The other is `outputs/`, scratch space for things being built.) Everywhere else, the vault keeps a link to where a file lives, on the note it belongs to.

## How it gets filled in

During setup, Claude asks for your website and for the folder on your computer that holds your logos. From those it:

1. Reads your site for your colors, fonts, tagline, and how you describe what you do.
2. Copies your logo files into `brand/logos/`, and works out which version suits a light page and which suits a dark one.
3. Writes `brand.md` with what it found.
4. Asks you about anything it could not work out, once, and writes your answers down so it never has to ask again.

No website yet? That is fine. Setup asks you a few direct questions instead.

New logos or a redesign later? Say **"refresh my brand"**. It saves a copy of the old `brand.md` in `archives/`, redoes just this part, and leaves the rest of the vault alone.

## How it gets used

A **hook** is a small script that runs automatically while you work. One of them, the brand guard (`.claude/hooks/brand_guard.py`), watches your messages for a request to make something: a PDF, a proposal, a one-pager, a post, an email, a deck, a report, a script.

When it sees one, it tells Claude to read `brand.md`, [[memory/taste]] and [[references/voice]] before writing a single word.

That is the whole trick. You do not run a command. You do not remind it. You ask for a one-pager and a one-pager in your brand comes back.

The words it watches for are listed at the top of that file. If you make something it has never heard of, say "add show notes to the brand guard list" and Claude adds it.

## You can edit it by hand

`brand.md` is plain markdown. Open it in Obsidian or any text editor and change whatever you like.

**Hand edits win.** Anything you type in yourself beats anything that was pulled from your website. If your site is out of date and your real accent color is different now, change the line. Nothing will overwrite it, including a later "refresh my brand", which asks before touching a field you wrote.

## Related

- [[brand/brand]] the profile itself
- [[memory/taste]] what you like and dislike about produced work
- [[references/voice]] how the words should sound
