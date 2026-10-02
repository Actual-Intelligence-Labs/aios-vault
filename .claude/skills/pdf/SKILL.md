---
name: pdf
description: Turn content into a designed PDF that comes out in the owner's brand automatically. Use for a PDF, one-pager, proposal, sell sheet, leave-behind, report, or any time someone says "make this look good" or "turn this into a PDF". Reads brand/brand.md, memory/taste.md and references/voice.md first, builds an HTML page from the shipped design system, renders it with a Chrome-family browser, then files the final where the owner keeps files and links it on the right note. Never asks the owner to describe their brand. Use this to make a new document; a general PDF skill is for reading, merging or filling PDFs that already exist.
---

# pdf

## What this is

You hand over content. You get back a document that looks designed.

Your colors. Your logo. Your fonts. Your voice. Not markdown printed to a page. And when it is done, it lands where you keep your files, with a link on the note it belongs to, so you can find it next month.

The whole point of `brand/brand.md` is this skill. The brand was captured once during setup, so no document ever starts with "what color do you want?"

## When it runs

Any of these:

- "make me a PDF of this"
- "turn this into a one-pager"
- "draft a proposal for {{CLIENT_NAME}}"
- "I need a leave-behind for tomorrow's meeting"
- "sell sheet for the new service"
- "make this look good"

A hook (a small script that runs before the AI answers) already nudges toward reading the brand files whenever a message asks for something to be made. This skill is the full procedure.

## Step 0. Read the brand FIRST, always

Before writing a single line of HTML, read these three files:

| File | What you take from it |
|---|---|
| `brand/brand.md` | Colors, heading and body fonts, logo files and which surface each belongs on, document defaults (cover style, logo placement, footer line, date format) |
| `memory/taste.md` | What the owner likes and dislikes: `[global]` rules, `[doc: TYPE]` rules for this kind of document, and `[client: NAME]` rules for whoever it is for. Honor all of them. |
| `references/voice.md` | How the words should sound, including sentence length and whether the owner writes in bullets or in paragraphs |

These three files decide how the document looks and reads. This skill only supplies the machinery.

Hard rules for this step:

- **Never ask the owner to describe their brand.** It is already on disk. Asking is a bug.
- If a field you actually need is still a placeholder (something in `{{DOUBLE_BRACES}}` or an empty line), ask **one** question, then **write the answer into `brand/brand.md`** before you continue.
- That write-back is what makes the system learn. A question asked once is answered forever. A question asked twice is a defect.

## Step 1. A short intake, only for what you cannot infer

Three things decide the layout:

1. **Who is it for?** (a named client, a prospect, internal, a general audience)
2. **What kind of document?** (one-pager, proposal, leave-behind, report)
3. **What is the title?**

If the message already makes those obvious, **skip the questions entirely.** Build it, and say in one line which defaults you took. For example: "Built as a one-pager for {{CLIENT_NAME}}, titled from your first line, in your brand colors."

Ask only about the ones that are genuinely ambiguous, in a single message, not one at a time.

If it is for a named client or person, look the name up in `context/who-and-what.md` and read their note: it holds facts the document may need, and it is where the finished file gets logged.

## Step 2. Shape the content before you lay it out

This is the difference between a designed document and a printed wall of text. Do not transcribe.

- **Group it into real sections**, each with a heading that says something. "What changes for you" beats "Section 2".
- **Pick the components that fit the content**: a figure worth remembering can stand alone as a stat, a list of deliverables reads well as key-value rows or a table, and the one point a reader must not miss can go in a callout. Use a component only when the content calls for it.
- **Write in the owner's voice.** How long paragraphs run, whether points are bullets or prose, and whether the document opens with the conclusion or builds to it all come from `references/voice.md` and `memory/taste.md`, not from this skill.
- **Never add a fact that was not in the source.** No invented metrics, no invented client names, no invented dates. If a number is needed and missing, leave a clearly marked gap and say so when you deliver.

## Step 3. Build the HTML

Start from `.claude/skills/pdf/assets/template.html`. It demonstrates every available component. Copy it, delete what you do not need, fill in the rest.

Write the file to `outputs/<short-name>.html`. The `outputs/` folder is the workbench: drafts and renders live there while you work.

Theme it with one inline style block in the `<head>`, right after the `<link>` to `base.css`. Four values come out of `brand/brand.md` and nothing else does:

```html
<!-- Only if the brand fonts are Google Fonts. Skip this line otherwise. -->
<link rel="stylesheet"
      href="https://fonts.googleapis.com/css2?family=Heading+Font:wght@400;600;700;800&family=Body+Font:wght@400;600&display=swap">
<style>
  :root{
    --accent:       #1f5fdb;   /* Accent hex from brand/brand.md */
    --ink:          #16202e;   /* Ink hex from brand/brand.md, if it has one */
    --font-heading: "Heading Font", Georgia, serif;      /* Heading font from brand/brand.md */
    --font-body:    "Body Font", -apple-system, Arial, sans-serif;  /* Body font */
  }
</style>
```

Rules for that block:

- Replace `Heading Font` and `Body Font` with the real names from `brand/brand.md`. Put them in the `<link>` too, with spaces written as `+`.
- **Always keep a fallback after the brand font**, the way the example does. If the font is not on the machine and not on Google Fonts, the fallback is what actually renders, and a bare font name with no fallback renders as Times.
- If `brand/brand.md` lists `Fallback fonts`, use those as the fallback instead of the example ones.
- If a font field is still a `{{PLACEHOLDER}}`, leave `--font-heading` and `--font-body` out entirely. The stylesheet's own defaults are good, and a guessed typeface is worse than a neutral one.
- `--accent` re-colors headings, rules, stats, callouts, table headers and the footer in one go. If the brand uses more than one color, `brand/brand.md` and `memory/taste.md` say how; follow them.

**Available components.** Use these by name. Do not invent markup.

| Component | Markup | Use it for |
|---|---|---|
| Cover | `<header class="cover">` | Standard title page: title, subtitle, meta row |
| Masthead | `<header class="masthead">` | Bolder cover: solid accent band, white text |
| Eyebrow | `<div class="eyebrow">` | Small uppercase label above a title or callout |
| Lead | `<p class="lead">` | An opening paragraph set slightly larger |
| Callout | `<div class="callout">` | A point that must not be missed |
| Two-column grid | `<div class="grid-2">` | Paired cards |
| Three-column grid | `<div class="grid-3">` | Three stats or three features |
| Card | `<div class="card">` | A bordered block with a heading and copy |
| Stat | `<div class="card stat"><div class="num">…</div><div class="label">…</div></div>` | A big number with a caption |
| Key-value rows | `<div class="kv"><div class="row"><span class="k">…</span><span class="v">…</span></div></div>` | Deliverables, line items, specs |
| Table | `<table>` with `<thead>`, `<tbody>`, and `<tr class="total">` for a total row | Scope and pricing |
| Tag | `<span class="tag">` | Small badges: status, category, phase |
| Footer | `<footer class="footer">` | Business name plus a website or confidentiality line |
| Page break | `<div class="page-break"></div>` | Force the next content onto a new page |

Let the stylesheet handle spacing. Hand-tuned margins and padding fight the system and usually look worse.

## Logos

- **Use the real file** from `brand/logos/`. Reference it with a full absolute path, written as `src="file://{{ABSOLUTE_PATH_TO_VAULT}}/brand/logos/logo-dark.png"`, where `{{ABSOLUTE_PATH_TO_VAULT}}` is the real folder path of this vault on this machine (run `pwd` in the vault to get it). Or copy the logo file next to the HTML and reference it by file name alone.
- **Never draw, trace, regenerate or crop a logo out of a screenshot.** Anything that is not the real file is a wrong logo.
- **Pick the file `brand/brand.md` lists for that surface.** A logo made for a dark background can look washed out on a white page, and the reverse can disappear. That is why brands usually have two versions. The masthead is a solid band of the accent color, so it takes the file meant for dark backgrounds; the stylesheet never recolors a logo to make one fit.
- **Placement** (which corner, how big, whether it appears at all) follows the document defaults in `brand/brand.md` and any rule in `memory/taste.md`. If neither says, choose a placement that suits the layout and record what you did in Step 6.
- **If `brand/logos/` is empty**, set the business name in the heading typeface where the logo would go, ship the document, and say plainly that is what you did and where to drop a logo file for next time.

## Starting shapes by document type

When `brand/brand.md` has no default for a type yet, start from these. A filled-in Document defaults row always wins.

| Type | Common shape |
|---|---|
| One-pager | Cover block, a short opening, two or three sections, closing line. It has to fit on **one page**. |
| Proposal | Cover, overview, scope, a table of what is included and what it costs, next steps. Multi-page. |
| Leave-behind | Masthead, the key numbers, short sections, a closing line. Meant to be read quickly. |
| Report | Cover, opening, sections with headings, tables or key-value rows, footer. Headings do the navigating. |

## Step 4. Render

Use the same Python the vault's automatic helpers use (never a bare `python3`: on a Mac without Apple's developer tools it pops up an install window, and on Windows the command is often `python`):

```sh
PY=$(sh .claude/hooks/run.sh --which) && [ -n "$PY" ] && "$PY" .claude/skills/pdf/render.py outputs/<name>.html
```

That finds a browser, copies the stylesheet next to your file, writes the PDF beside the HTML, and prints the path. If `run.sh --which` prints nothing, there is no Python 3.9 or newer: say so in one line and offer to set it up (the `onboard` skill's install check has the steps).

That command is a shell command, run with the Bash tool from the vault folder. It is not something the owner types.

If it reports that no browser was found, the machine has none of Google Chrome, Chromium, Microsoft Edge, or Brave, any of which works. Tell the owner to install one (Chrome is at google.com/chrome) and re-run the same command. Nothing else is required. There is no package to install.

## Step 5. Check it before handing it over

Open the rendered PDF and actually look at it. Do not skip this.

Watch for:

- A one-pager that spilled onto a second page.
- An awkward page break splitting a heading from its section, or a table from its header.
- A missing image showing as a broken box.
- Text running off the right edge (usually a long URL or an unbroken code string).
- A logo that looks grey, washed out or invisible (wrong file for the background).
- Anything that breaks a rule in `memory/taste.md`.

When you find one, **fix the HTML and re-render.** Do not hand over a flawed document with an apology attached.

## Step 6. Write the document default back into the brand file

The first time you build a given document type (one-pager, proposal, leave-behind, report), open `brand/brand.md` and fill in that row of the **Document defaults** table with what you actually just did. A phrase or two: cover or masthead, where the logo sat, how dense the type was, how the accent color was used.

This is what stops the second one-pager from being a fresh set of decisions. If the row already has a real value, follow it rather than rewriting it, and only change it when the owner asks for something different.

When the owner reacts to the document ("too busy", "I like that cover"), that reaction becomes a rule in `memory/taste.md`, scoped `[doc: TYPE]` or `[client: NAME]` if it is not universal.

## Step 7. File the final and link it

A finished document lives where the owner keeps their files, not in the vault. The vault only points at it.

1. **Find its home.** Read `context/where-files-live.md`: its rules, where each kind of file goes, and the owner's naming pattern. A proposal for Acme goes wherever the map says client proposals go.
   - **Clear home:** use it. If the map's pattern calls for a subfolder that does not exist yet (say, a folder for a brand new client in a folder-per-client system), create just that one. Never a new top-level folder, and never a new way of organizing.
   - **No clear home,** or no map yet: ask one question with your best guess. "I'd put this in Documents/Clients/Acme/Proposals. Right?" Then add the answer to the map so it is never asked again. With no map at all, also offer `/map-files`, which learns the whole system in one pass.
2. **Name it the owner's way,** following the Naming section of the map (their date format, version style, word order). If the map has no naming rule yet, use a plain descriptive name (what it is, who it is for, the date) and add a line to the map's questions list for the owner.
3. **Save it there.**
   - A folder on this computer, including a cloud drive that syncs to this computer as a folder: copy the PDF in.
   - A cloud drive reached through a connected tool: upload it there.
   - Not reachable from here: leave it in `outputs/`, give the owner the path, and say where the map says it should go.
   - Never overwrite a file that was already sent or signed. A new version gets a new version number, in the owner's style.
4. **Log it on the note.** Add one dated line to the `## Files` section of the note for the client, person or project it is for (`context/who-and-what.md` says which note):

   ```markdown
   - 2026-03-14 [Acme proposal v2](https://link-to-the-file)
   - 2026-03-14 Acme proposal v2: `~/Documents/Clients/Acme/Proposals/Acme proposal v2.pdf`
   ```

   The first shape is for a cloud link, the second for a file on this computer. If a newer version replaces a draft, update the draft's line instead of adding another; keep the lines for versions that were sent or signed. If the document belongs to no note, say so and offer to start one with `/new-node`; do not invent a home.
5. **Leave `outputs/` tidy, with permission.** The HTML and draft renders stay in `outputs/` (it is ignored by git and safe to empty). Once the final is filed and checked, offer to clear older drafts. Never delete them on your own.

## Step 8. Deliver

- Say where the final lives (the link or the path) and which note it is logged on.
- Offer a fast tweak loop: different color treatment, tighter copy, other logo file, add or drop a section. Each of those is an edit to the HTML and one re-render, not a rebuild. A changed final replaces the filed copy as a new version.
- Anything that goes outside (attaching it to an email, sharing a link with a client) is drafted and shown. The owner sends it.

## Notes

- **Engine.** A Chrome-family browser with no window open prints the HTML to PDF: Chrome, Chromium, Edge, or Brave, whichever it finds first. US Letter, 16mm margins. No LaTeX, no wkhtmltopdf, no Python packages.
- **Fonts.** The stylesheet ships with Inter and Source Serif 4 as its defaults, and the document overrides them with the brand fonts through `--font-heading` and `--font-body`. Webfonts load when the machine is online and fall back to the stack you wrote when it is not. An offline render still looks correct, just slightly different.
- **Images.** Any image path must be absolute (`file:///...`) or sit in the same folder as the HTML. A relative path is resolved against the folder the HTML is in, so a relative path pointing anywhere else finds nothing. Before rendering, `render.py` checks every local image the page references and refuses to render if any of those files does not exist, because a missing image does not error at render time. It just becomes a grey box in the finished PDF.
- **Output path.** `render.py` writes the PDF next to the HTML by default. `-o <path>` writes it somewhere else, but render in `outputs/` first and file the checked copy, so a half-finished render never lands in the owner's folders.
- **Theming.** Per-document theming comes down to these custom properties in the style block: `--accent`, `--ink`, `--font-heading`, `--font-body`. Everything derived from the accent updates on its own.

Related: [[brand/brand]], [[memory/taste]], [[references/voice]], [[context/where-files-live]], [[connections]]
