"""Is this vault's system (hooks, skills, guides) older than this copy of the
template? Read only.

  python3 version_check.py --vault .  [--template <a downloaded copy of the template>]

It works out the vault's version the way the update-vault skill does: from the
"What's new in vX.Y.Z" heading in the vault's README.md, or, for a version
older than those headings, from the fingerprints in
.claude/skills/update-vault/known-versions.json. It also looks for files this
version ships that the vault lacks, old hook files a later version retired,
and system files that are still exactly an older version.

It prints "older" (run the update-vault skill first) or "current".
"""

import sys
sys.dont_write_bytecode = True  # never leave a __pycache__ folder in the vault
import argparse
import json
import os
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vaultkit as vk  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OWN_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
BASE_FILES = ["CLAUDE.md", ".claude/hooks/run.sh", ".claude/settings.json", "memory/claude/MEMORY.md",
        "context/who-and-what.md", "context/where-files-live.md"]


def vtuple(v):
    if not v:
        return None
    m = re.match(r"v?(\d+)(?:\.(\d+))?(?:\.(\d+))?", str(v))
    if not m:
        return None
    return tuple(int(x or 0) for x in m.groups())


def readme_version(root):
    t = vk.read_text(os.path.join(root, "README.md")) or ""
    vs = [vtuple(m.group(1)) for m in re.finditer(r"^#{1,4}\s+What's new in (v?\d+(?:\.\d+){0,2})", t, re.M)]
    vs = [v for v in vs if v]
    return max(vs) if vs else None


def known_versions(*roots):
    for r in roots:
        p = os.path.join(r, ".claude", "skills", "update-vault", "known-versions.json")
        d = vk.load_json(p, None)
        if isinstance(d, dict):
            return [v for v in d.get("versions", []) if isinstance(v, dict)]
    return []


def show(t):
    return "v" + ".".join(str(x) for x in t) if t else "unknown"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Is the vault older than this template? (read only)")
    ap.add_argument("--vault", default=None)
    ap.add_argument("--template", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    root = vk.find_vault(args.vault)
    tmpl = os.path.abspath(args.template) if args.template else OWN_ROOT
    same = os.path.realpath(tmpl) == os.path.realpath(root)
    facts = vk.template_facts()
    known = known_versions(tmpl, root)

    t_ver = readme_version(tmpl) if args.template else None
    t_ver = t_ver or vtuple(facts.get("version"))
    v_ver = readme_version(root)
    label = None
    if v_ver is None:
        h = None
        p = os.path.join(root, "README.md")
        if os.path.isfile(p):
            h = vk.norm_hash(vk.read_bytes(p) or b"")
        for v in known:
            if h and v.get("files", {}).get("README.md") == h:
                label = v.get("label")
        v_ver = vtuple(label) if label and vtuple(label) and label.startswith("v") else None

    reasons = []
    if t_ver and (v_ver is None or v_ver < t_ver):
        reasons.append("the vault's guides say %s, this template is %s" % (
            show(v_ver) if v_ver else ("version " + label if label else "an older version"), show(t_ver)))
    if t_ver and v_ver and v_ver > t_ver:
        res = {"older": False, "newer_vault": True, "vault_version": show(v_ver), "template_version": show(t_ver)}
        vk.emit(args, res, ["The vault (%s) is newer than this copy of the skill (%s). Use the vault's own copy of "
                            "the optimize-vault skill instead." % (show(v_ver), show(t_ver))])
        return 0

    # What this version ships that the vault lacks.
    want_hooks = set(facts.get("hooks") or [])
    want_skills = set(facts.get("skills") or [])
    if not same:
        hd = os.path.join(tmpl, ".claude", "hooks")
        sd = os.path.join(tmpl, ".claude", "skills")
        want_hooks = set(n for n in os.listdir(hd) if not n.startswith(".") and n != "__pycache__") \
            if os.path.isdir(hd) else want_hooks
        want_skills = set(n for n in os.listdir(sd) if os.path.isfile(os.path.join(sd, n, "SKILL.md"))) \
            if os.path.isdir(sd) else want_skills
    missing = [r for r in BASE_FILES if not os.path.exists(os.path.join(root, r))]
    missing += [".claude/hooks/" + h for h in sorted(want_hooks)
                if not os.path.exists(os.path.join(root, ".claude", "hooks", h))]
    missing += [".claude/skills/" + s + "/" for s in sorted(want_skills)
                if not os.path.isfile(os.path.join(root, ".claude", "skills", s, "SKILL.md"))]
    if missing:
        reasons.append("missing: " + ", ".join(missing[:8]) + (" and more" if len(missing) > 8 else ""))

    # Retired hook files from an earlier version.
    old_hooks = set()
    for v in known:
        for rel in v.get("files", {}):
            if rel.startswith(".claude/hooks/"):
                old_hooks.add(rel.split("/")[-1])
    retired = [h for h in sorted(old_hooks - want_hooks) if os.path.exists(os.path.join(root, ".claude", "hooks", h))]
    if want_hooks and retired:
        reasons.append("old hook files a later version retired: " + ", ".join(retired))

    # System files still exactly as an earlier version shipped them, where this template differs.
    stale = []
    if not same:
        for v in known:
            for rel, h in v.get("files", {}).items():
                if not rel.startswith((".claude/hooks/", ".claude/skills/")):
                    continue
                vp, tp = os.path.join(root, rel), os.path.join(tmpl, rel)
                if os.path.isfile(vp) and os.path.isfile(tp):
                    vh = vk.norm_hash(vk.read_bytes(vp) or b"")
                    if vh == h and vh != vk.norm_hash(vk.read_bytes(tp) or b""):
                        stale.append(rel)
        stale = sorted(set(stale))
        if stale:
            reasons.append("%d system files are still an older version (for example %s)" % (len(stale), stale[0]))

    older = bool(reasons)
    res = {"older": older, "vault_version": show(v_ver) if v_ver else (label or "unknown"),
           "template_version": show(t_ver), "reasons": reasons, "missing": missing, "retired": retired,
           "stale": stale}
    if older:
        lines = ["Version check: older. Run the update-vault skill first, then come back to this one.",
                 "  Why: " + "; ".join(reasons) + "."]
    else:
        lines = ["Version check: current (%s). No update needed first." % show(t_ver)]
    vk.emit(args, res, lines)
    return 0


if __name__ == "__main__":
    sys.exit(main())
