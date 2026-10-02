#!/usr/bin/env python3
"""
Reduce a long meeting-notes export down to just the notes. Drops the
verbatim transcript so the result fits in the model's reading window.

Why: a recorded-meeting document is mostly the full word-for-word transcript
(often 100KB or more). The parts a note-taking tool already pulled out for you
(Summary, Decisions, Next steps with owners, Details) sit ABOVE the point where
the transcript starts. This prints only that portion.

The transcript boundary is found by the markers common tools write at that
point. Add your own tool's marker to the checks in main() if yours differs.

Usage:
  python3 extract_notes.py <file>      # file = saved tool-result JSON {"result": "..."} OR raw exported text
  cat export.txt | python3 extract_notes.py
"""
import json, re, sys, pathlib


def decode(raw):
    """Unwrap a saved MCP tool-result ({"result": "..."}) or return raw text."""
    if raw.lstrip().startswith("{"):
        try:
            return json.loads(raw).get("result", raw)
        except Exception:
            return raw
    return raw


def load(src):
    if src is None:                              # stdin: decode JSON too, not just file paths
        return decode(sys.stdin.read())
    return decode(pathlib.Path(src).expanduser().read_text(encoding="utf-8", errors="replace"))


def main():
    text = load(sys.argv[1] if len(sys.argv) > 1 else None)
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\ufeff", "")
    lines = text.split("\n")

    cut = len(lines)
    seen_body = False
    for i, l in enumerate(lines):
        s = l.strip()
        if s in ("Summary", "Decisions", "Next steps", "Details"):
            seen_body = True
        # A heading that is just the word "transcript" marks where the verbatim
        # transcript starts. Strip any decoration around it (symbols, punctuation,
        # markdown) before comparing, so every tool's style of heading matches.
        if len(s) <= 40 and re.sub(r"[^a-z ]", "", s.lower()).strip() in (
                "transcript", "full transcript", "verbatim transcript"):
            cut = i; break
        if seen_body and re.match(r".+ - Transcript$", s):  # fallback marker
            cut = i; break

    # Guardrail: no transcript boundary AND no notes sections means this is a
    # structureless / transcript-only doc. Do NOT dump it (it would overflow the
    # reading window). Signal the caller to summarize it in a subagent (SKILL Step 2.4).
    if cut == len(lines) and not seen_body:
        print("[extract_notes] NO notes sections found (no Summary/Decisions/Next steps). "
              "Treat as transcript-only: summarize inside a subagent per SKILL Step 2.4. Do not read inline.")
        print(f"[extract_notes: {len(lines)} lines, no notes boundary; dump suppressed]", file=sys.stderr)
        sys.exit(2)

    print("\n".join(lines[:cut]).strip())
    status = "transcript dropped" if cut < len(lines) else "no transcript marker; kept notes only"
    print(f"\n[extract_notes: kept {cut} of {len(lines)} lines; {status}]", file=sys.stderr)


if __name__ == "__main__":
    main()
