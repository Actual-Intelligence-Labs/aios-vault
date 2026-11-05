"""Connector check: runs once, when a Claude Code session opens in this vault.

WHAT IT DOES
  Connectors (email, calendar, cloud files and the like), plugins and local
  tool servers decide what every chat in this folder can reach. They can
  change without anyone noticing: a new connector on the account, a sign-in
  to a different account, a plugin switched on. A chat keeps the list it
  opened with, so a change shows up only in the next chat.
  This check compares today's setup with the last session's and, when
  something changed, hands Claude one line saying what. A newly connected
  connector is named (names are not secrets). Claude tells the owner in one
  plain line and asks before changing anything.
  The first session only takes a first reading and says nothing.

WHAT IT READS
  Claude Code's own settings: the account file (.claude.json), the global
  settings.json, and this folder's .claude/settings.json,
  .claude/settings.local.json and .mcp.json. Only names and on/off lists.

SAFETY
  It stores only fingerprints (hashes) of those lists, never a name, a value
  or a key, in .claude/state/ inside this vault. That folder ignores itself
  in git. It never changes a setting, never touches the network, logs
  nothing, and stays quiet inside helper agents and after a compaction.
  On any error it prints nothing and gets out of the way.
  Runs on Python 3.9 or newer, standard library only, through run.sh.
"""

import hashlib
import json
import os
import sys
import tempfile


def vault_root():
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(os.path.dirname(here))
    if os.path.isdir(os.path.join(root, ".claude")):
        return root
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    return env if env and os.path.isdir(env) else os.getcwd()


def config_dir():
    return os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")


def account_file():
    env = os.environ.get("CLAUDE_CONFIG_DIR")
    return os.path.join(env, ".claude.json") if env else os.path.join(os.path.expanduser("~"), ".claude.json")


def state_file(root):
    folder = os.environ.get("VAULT_HOOKS_STATE_DIR") or os.path.join(root, ".claude", "state")
    return os.path.join(folder, "connector-check.json")


def fingerprint(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode("utf-8")).hexdigest()[:20]


def load(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def as_dict(x):
    return x if isinstance(x, dict) else {}


def as_list(x):
    return [str(v) for v in x] if isinstance(x, list) else []


def snapshot(root):
    account = load(account_file())
    projects = as_dict(account.get("projects"))
    entry = as_dict(projects.get(root) or projects.get(os.path.realpath(root)))
    plugins = {"global": as_dict(load(os.path.join(config_dir(), "settings.json")).get("enabledPlugins"))}
    for name in ("settings.json", "settings.local.json"):
        plugins[name] = as_dict(load(os.path.join(root, ".claude", name)).get("enabledPlugins"))
    servers = [sorted(as_dict(account.get("mcpServers")).keys()), sorted(as_dict(entry.get("mcpServers")).keys()),
               sorted(as_dict(load(os.path.join(root, ".mcp.json")).get("mcpServers")).keys())]
    off = [sorted(as_list(entry.get(k))) for k in ("disabledMcpServers", "disabledMcpjsonServers",
                                                    "enabledMcpjsonServers")]
    connected = sorted(set(as_list(account.get("claudeAiMcpEverConnected"))))
    return {
        "off": fingerprint(off),
        "plugins": fingerprint(plugins),
        "servers": fingerprint(servers),
        "connected": [fingerprint(n) for n in connected],
    }, connected


def save(path, obj):
    folder = os.path.dirname(path)
    if not os.path.isdir(folder):
        os.makedirs(folder, mode=0o700, exist_ok=True)
        ignore = os.path.join(folder, ".gitignore")
        if not os.path.exists(ignore):
            with open(ignore, "w", encoding="utf-8") as fh:
                fh.write("# Machine state for the vault's automatic helpers. Never worth keeping in git.\n*\n")
    fd, tmp = tempfile.mkstemp(dir=folder, prefix=".connector-check-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(obj, fh)
        os.replace(tmp, path)
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return   # input it cannot read: do nothing
    if not isinstance(data, dict):
        return
    tp = str(data.get("transcript_path") or "").replace("\\", "/")
    if data.get("agent_id") or "/subagents/" in tp or data.get("source") == "compact":
        return
    root = vault_root()
    path = state_file(root)
    before = load(path)
    now, names = snapshot(root)
    if now != {k: before.get(k) for k in now}:
        save(path, now)
    if not before:
        return   # first reading: nothing to compare with yet
    changes = []
    known = set(as_list(before.get("connected")))
    new = [n for n in names if fingerprint(n) not in known]
    if new:
        changes.append("newly connected on the account: " + ", ".join(new[:5]) + (" and more" if len(new) > 5 else "")
                       + " (a connector loads in every chat in this folder unless it is switched off here)")
    if now["off"] != before.get("off"):
        changes.append("the list of connectors switched on or off for this folder changed")
    if now["plugins"] != before.get("plugins"):
        changes.append("which plugins are switched on changed")
    if now["servers"] != before.get("servers"):
        changes.append("the list of local tool servers (MCP servers) changed")
    if changes:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": "CONNECTOR CHECK (automatic): since the last session in this folder, "
                                 + "; ".join(changes) + ". If the owner did not mean this (signing in to another "
                                 "account can do it), tell them in one plain line and ask before changing anything. "
                                 "Never print connector settings or keys.",
        }}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
