"""Prove that an optimize run lost nothing. Read only.

  python3 proof.py --vault . --run-dir archives/optimize-YYYY-MM-DD-HHMM

It reads the copies the run kept of every file before it changed, and checks:
  1. Every line that was in a changed file is still in that file, or in a file
     the run wrote to (a history file, a hub note), or, for a CLAUDE.md line
     the owner chose to drop, word for word in its memory note. (Blank lines
     are not counted; the tidy step checks those byte for byte itself.)
  2. Every rule and default line of the memory index is still in the index,
     word for word.
  3. Every memory note that the index reached within two links still is.
  4. Every history file the run made is linked from the file it came from.
  5. Every file moved out of the vault is at its new place, byte for byte.
It prints a short plain report, or JSON with --json, and exits 1 if anything
is missing.
"""

import sys
sys.dont_write_bytecode = True  # never leave a __pycache__ folder in the vault
import argparse
import os
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vaultkit as vk  # noqa: E402
import memory_index as mi  # noqa: E402
import fixes  # noqa: E402


def nonblank(text):
    return [vk.bare(l) for l in vk.split_keep(text or "") if vk.bare(l).strip()]


def prove(root, run_dir):
    run = vk.Run(root, run_dir)
    if not os.path.isfile(run.manifest_path()):
        return {"error": "no manifest.json in " + run.rel + ", so this is not an optimize run folder"}
    man = run.manifest()
    files = man["files"]
    steps = man["steps"]
    trimmed = [t for s in steps if s.get("step") == "repeats" for t in s.get("trimmed", [])]
    replaced = [r for s in steps if s.get("step") == "skill-description" for r in s.get("replaced", [])]
    moved_out = [m for s in steps if s.get("step") == "move-out" for m in s.get("moved", [])]
    out = {"run_dir": run.rel, "files_checked": 0, "lines_checked": 0, "lost": [], "on_purpose": 0}

    backups = {}
    current = {}
    for rel, e in files.items():
        current[rel] = vk.read_text(os.path.join(root, rel))
        backups[rel] = vk.read_text(os.path.join(root, e["backup"])) if e.get("existed") and e.get("backup") else None
    pool = Counter()
    for rel in files:
        now = Counter(nonblank(current[rel]))
        was = Counter(nonblank(backups[rel]))
        pool.update(now - was)
    trimmed_ok = Counter()
    for t in trimmed:
        note = vk.read_text(os.path.join(root, t["note"])) or ""
        if fixes.norm_line(t["line"]) in [fixes.norm_line(x) for x in note.split("\n")]:
            trimmed_ok[t["line"]] += 1
    replaced_text = [r.get("old") or "" for r in replaced]
    for rel, e in sorted(files.items()):
        if not e.get("existed"):
            continue
        out["files_checked"] += 1
        need = Counter(nonblank(backups[rel]))
        out["lines_checked"] += sum(need.values())
        gone = need - Counter(nonblank(current[rel]))
        for line, n in gone.items():
            take = min(n, pool[line])
            pool[line] -= take
            n -= take
            if n and trimmed_ok[line]:
                k = min(n, trimmed_ok[line])
                trimmed_ok[line] -= k
                n -= k
                out["on_purpose"] += k
            if n and rel.endswith("SKILL.md") and line.startswith("description:") and any(
                    old and old in line or line.endswith(old) for old in replaced_text):
                out["on_purpose"] += n
                n = 0
            if n and rel.endswith("SKILL.md") and any(line.strip() and line.strip() in old for old in replaced_text):
                out["on_purpose"] += n
                n = 0
            if n:
                out["lost"].append({"file": rel, "line": line[:160], "count": n})
    # Memory index: rule and default lines word for word, and reachability.
    if mi.INDEX_REL in files and backups.get(mi.INDEX_REL) is not None:
        _, rows = mi.parse_index(backups[mi.INDEX_REL])
        stays = [vk.bare(r["line"]) for r in rows if r["kind"] in ("rule", "default")]
        have = set(vk.bare(l) for l in vk.split_keep(current.get(mi.INDEX_REL) or ""))
        out["rule_lines"] = len(stays)
        out["rule_lines_kept"] = sum(1 for s in stays if s in have)
        before = mi.reachable(root, backups[mi.INDEX_REL])
    else:
        before = mi.reachable(root)
    after = mi.reachable(root)
    out["reachable_before"] = len(before)
    out["reachable_after"] = len(after)
    out["unreachable_now"] = sorted(set(before) - set(after))
    # History files are linked from where their lines came from.
    unlinked = []
    for rel, e in files.items():
        if e.get("existed") or not rel.startswith(vk.HISTORY + "/"):
            continue
        src = {"decisions": "decisions/log.md", "tasks": "tasks.md", "inbox": "inbox.md"}.get(rel.split("/")[1])
        if src and ("[[" + rel[:-3]) not in (vk.read_text(os.path.join(root, src)) or ""):
            unlinked.append(rel)
    out["history_unlinked"] = unlinked
    # Files moved out of the vault.
    bad = []
    for m in moved_out:
        if not os.path.isfile(m["to"]) or vk.sha_file(m["to"]) != m["sha256"]:
            bad.append(m["from"])
    out["moved_out"] = len(moved_out)
    out["moved_out_missing"] = bad
    out["ok"] = (not out["lost"] and not out["unreachable_now"] and not unlinked and not bad
                 and out.get("rule_lines_kept", 0) == out.get("rule_lines", 0))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Prove an optimize run lost nothing (read only).")
    ap.add_argument("--vault", default=None)
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    root = vk.find_vault(args.vault)
    r = prove(root, args.run_dir)
    if r.get("error"):
        vk.emit(args, r, [r["error"]])
        return 1
    L = []
    lost = sum(x["count"] for x in r["lost"])
    L.append("Line check for %s: %s lines checked in %d files, %d lost%s." % (
        r["run_dir"], vk.fmt(r["lines_checked"]), r["files_checked"], lost,
        (" (%d removed on purpose, each still in the vault or the backup)" % r["on_purpose"]) if r["on_purpose"] else ""))
    for x in r["lost"][:10]:
        L.append("  LOST from %s: %s" % (x["file"], x["line"]))
    if "rule_lines" in r:
        L.append("Memory index rule and default lines kept word for word: %d of %d." % (r["rule_lines_kept"], r["rule_lines"]))
    L.append("Memory notes reachable from the index within two links: %d before, %d now%s." % (
        r["reachable_before"], r["reachable_after"],
        "" if not r["unreachable_now"] else "; no longer reachable: " + ", ".join(r["unreachable_now"][:5])))
    if r["history_unlinked"]:
        L.append("History files with no link from where they came from: " + ", ".join(r["history_unlinked"]))
    if r["moved_out"]:
        L.append("Files moved out of the vault: %d, %s." % (
            r["moved_out"], "each one checked at its new place" if not r["moved_out_missing"]
            else "MISSING at the new place: " + ", ".join(r["moved_out_missing"])))
    L.append("Result: " + ("nothing lost." if r["ok"] else "PROBLEM, see above. Restore from the save point."))
    vk.emit(args, r, L)
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
