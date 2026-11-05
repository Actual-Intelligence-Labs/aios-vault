"""For whoever releases a new version of the template, not for vault owners.

  python3 record_template.py <clean copy of the new release> [--also <older release copy>]... [--version X.Y.Z]

Rewrites ../template-facts.json from that copy: its version (from the
"What's new in vX.Y.Z" heading in README.md), the hooks and skills it ships,
the lines its .gitignore keeps, and a fingerprint of every line of its
CLAUDE.md. The optimize-vault skill uses those fingerprints to tell the
template's own house rules (never trimmed) from lines the owner added.
Fingerprints of earlier versions already in the file are kept. A fingerprint
holds no text.
"""

import sys
sys.dont_write_bytecode = True  # never leave a __pycache__ folder in the vault
import json
import os
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vaultkit as vk  # noqa: E402
import fixes  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "template-facts.json")


def line_hashes(folder):
    t = vk.read_text(os.path.join(folder, "CLAUDE.md")) or ""
    out = set()
    for l in t.split("\n"):
        n = fixes.norm_line(l)
        if n:
            out.add(vk.norm_hash(n))
    return out


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    folder = argv[1]
    also = [argv[i + 1] for i, a in enumerate(argv) if a == "--also" and i + 1 < len(argv)]
    given = [argv[i + 1] for i, a in enumerate(argv) if a == "--version" and i + 1 < len(argv)]
    readme = vk.read_text(os.path.join(folder, "README.md")) or ""
    vs = re.findall(r"^#{1,4}\s+What's new in v?(\d+\.\d+\.\d+)", readme, re.M)
    version = max(vs, key=lambda v: tuple(int(x) for x in v.split("."))) if vs else ""
    if given:
        version = given[0].lstrip("v")
        if version not in vs:
            print("Note: README.md has no \"What's new in v%s\" heading yet. Add it before release, or every "
                  "vault on this version will be told it is older." % version)
    hooks = sorted(n for n in os.listdir(os.path.join(folder, ".claude", "hooks"))
                   if not n.startswith(".") and n != "__pycache__")
    skills = vk.skill_dirs(folder)
    gi = [vk.bare(l).strip() for l in vk.split_keep(vk.read_text(os.path.join(folder, ".gitignore")) or "")]
    gi = [l for l in gi if l and not l.startswith("#")]
    old = vk.load_json(OUT, {})
    hashes = set(old.get("claude_line_hashes", [])) if isinstance(old, dict) else set()
    hashes |= line_hashes(folder)
    for a in also:
        hashes |= line_hashes(a)
    data = {
        "_what_this_is": "Facts about the template version this skill ships with. claude_line_hashes are SHA-256 "
                         "fingerprints of each CLAUDE.md line the template has shipped, so the skill never offers to "
                         "trim a house rule. A fingerprint holds no text.",
        "_when_releasing": "Run scripts/record_template.py on a clean copy of the new release before tagging it. "
                           "It keeps every older fingerprint.",
        "version": version,
        "hooks": hooks,
        "skills": skills,
        "gitignore_required": gi,
        "claude_line_hashes": sorted(hashes),
    }
    vk.atomic_write(OUT, json.dumps(data, indent=2, sort_keys=True) + "\n")
    print("Wrote %s: version %s, %d hooks, %d skills, %d .gitignore lines, %d CLAUDE.md line fingerprints."
          % (OUT, version or "(none found)", len(hooks), len(skills), len(gi), len(hashes)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
