"""Can Claude still find every memory note and every history file? Read only.

  python3 reach.py --vault .            plain report
  python3 reach.py --vault . --strict   exits 1 when something is not reachable

Memory notes: each note in memory/claude/ should be reachable from the index
(MEMORY.md) within two links: index -> note, or index -> hub note -> note.
History files: each file in history/ should be linked from the file its lines
came from (decisions/log.md, tasks.md or inbox.md), one link away.
"""

import sys
sys.dont_write_bytecode = True  # never leave a __pycache__ folder in the vault
import argparse
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vaultkit as vk  # noqa: E402
import memory_index as mi  # noqa: E402

SOURCES = {"decisions": "decisions/log.md", "tasks": "tasks.md", "inbox": "inbox.md"}


def check(root):
    reach = mi.reachable(root)
    notes = mi.memory_notes(root)
    far = [n for n in notes if n not in reach]
    hops = {}
    for n, h in reach.items():
        hops[h] = hops.get(h, 0) + 1
    hist = []
    hd = os.path.join(root, vk.HISTORY)
    for rel in vk.walk_files(root):
        if not rel.startswith(vk.HISTORY + "/") or not rel.endswith(".md"):
            continue
        parts = rel.split("/")
        src = SOURCES.get(parts[1]) if len(parts) > 2 else None
        if not src:
            continue
        if ("[[" + rel[:-3]) not in (vk.read_text(os.path.join(root, src)) or ""):
            hist.append(rel)
    return {"memory_notes": len(notes), "reachable": len(reach), "by_links": hops, "not_reachable": far,
            "history_unlinked": hist, "ok": not far and not hist, "history_folder": os.path.isdir(hd)}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Reachability of memory notes and history files (read only).")
    ap.add_argument("--vault", default=None)
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    root = vk.find_vault(args.vault)
    r = check(root)
    L = ["Memory notes: %d, reachable from the index within two links: %d (one link: %d, two links: %d)." % (
        r["memory_notes"], r["reachable"], r["by_links"].get(1, 0), r["by_links"].get(2, 0))]
    if r["not_reachable"]:
        L.append("  Not reachable: " + ", ".join(r["not_reachable"][:10]) + (" and more" if len(r["not_reachable"]) > 10 else ""))
    if r["history_unlinked"]:
        L.append("History files with no link from where they came from: " + ", ".join(r["history_unlinked"]))
    elif r["history_folder"]:
        L.append("History files: each one is linked from the file it came from.")
    vk.emit(args, r, L)
    return 1 if (args.strict and not r["ok"]) else 0


if __name__ == "__main__":
    sys.exit(main())
