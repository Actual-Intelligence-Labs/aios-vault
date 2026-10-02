#!/bin/sh
# ---------------------------------------------------------------------------
# run.sh
#
# WHAT THIS IS
#   Every automatic helper (a "hook") in this folder is a small Python script.
#   Claude Code never runs those scripts directly. It runs this file and names
#   the script, like this:
#
#       sh .claude/hooks/run.sh session_pulse.py
#
#   This file finds a Python on your computer and runs the script with it,
#   passing along everything Claude Code sent.
#
# WHY A WRAPPER
#   Python goes by different names on different computers (python3, python,
#   python3.12). This file tries them in order and uses the first one that is
#   version 3.9 or newer. Sheet Geek, the spreadsheet plugin, needs 3.10 or
#   newer, so 3.10+ is what the guides tell you to install.
#
#   On a Mac it never runs /usr/bin/python3. That one is Apple's stand-in: on
#   a Mac without Apple's developer tools it pops up an install window in the
#   middle of your session. When the developer tools ARE installed, this file
#   runs their Python directly, which never shows that window.
#
# SAFETY
#   If no suitable Python is found, or anything goes wrong, it prints nothing
#   and exits quietly, so a missing Python can never break or block a turn.
#   The one exception is the vault check (doctor.py): you ran that to find
#   out what is wrong, so it says plainly that Python is missing.
#
# You can run the vault check yourself any time from this folder:
#       sh .claude/hooks/run.sh doctor.py </dev/null
#
# Skills that run a Python script ask this file which Python to use, so every
# part of the vault uses the same one:
#       sh .claude/hooks/run.sh --which
# prints that Python's full path, or nothing when there is none.
# ---------------------------------------------------------------------------

script=$1

# Only a plain file name from this folder, never a path. The one other word
# understood is --which (see above).
case "$script" in
  --which) ;;
  '' | */* | *..*) exit 0 ;;
esac

# This folder, found without calling any other program (so it works even
# when PATH is empty or odd).
case "$0" in
  */*) here_rel=${0%/*} ;;
  *) here_rel=. ;;
esac
here=$(CDPATH= cd -- "$here_rel" 2>/dev/null && pwd) || exit 0
target=$here/$script
if [ "$script" != --which ]; then
  [ -f "$target" ] || exit 0
fi

# Common install spots, added at the END so your own PATH order still wins.
# (The vault check looks at your PATH as it was, to see what Sheet Geek sees.)
VAULT_ORIGINAL_PATH=${PATH:-}
export VAULT_ORIGINAL_PATH
PATH="${PATH:-/usr/bin:/bin}:/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$HOME/.pyenv/shims:/Library/Frameworks/Python.framework/Versions/Current/bin:/usr/bin:/bin"
export PATH

on_mac=0
[ "$(uname -s 2>/dev/null)" = Darwin ] && on_mac=1

# Does this Python work, and is it 3.9 or newer? (Reads nothing from stdin,
# so the message from Claude Code is still there for the real run.)
usable() {
  "$@" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' </dev/null >/dev/null 2>&1
}

# Run the script with this Python, stay quiet about errors, always exit 0.
# With --which, print this Python's full path instead.
run_with() {
  if [ "$script" = --which ]; then
    "$@" -c 'import sys; print(sys.executable)' </dev/null 2>/dev/null
    exit 0
  fi
  "$@" "$target" 2>/dev/null
  exit 0
}

# Apple's stand-in python3 lives in /usr/bin. Skip it on a Mac.
skip() {
  [ "$on_mac" = 1 ] || return 1
  case "$1" in
    /usr/bin/*) return 0 ;;
  esac
  return 1
}

# 1. python3, then python, in every folder on PATH, in PATH order.
old_ifs=$IFS
IFS=:
set -f
for dir in $PATH; do
  IFS=$old_ifs
  case "$dir" in
    /*) ;;
    *) continue ;;   # skip empty and relative entries
  esac
  for name in python3 python; do
    p=$dir/$name
    [ -x "$p" ] && [ ! -d "$p" ] || continue
    skip "$p" && continue
    usable "$p" && run_with "$p"
  done
done
IFS=$old_ifs
set +f

# 2. A version-numbered Python (some installers only add python3.12 and so on).
for name in python3.15 python3.14 python3.13 python3.12 python3.11 python3.10 python3.9; do
  p=$(command -v "$name" 2>/dev/null) || continue
  case "$p" in
    /*) ;;
    *) continue ;;
  esac
  skip "$p" && continue
  usable "$p" && run_with "$p"
done

# 3. On a Mac, the Python inside Apple's developer tools, called directly.
if [ "$on_mac" = 1 ]; then
  for p in /Library/Developer/CommandLineTools/usr/bin/python3 \
           /Applications/Xcode.app/Contents/Developer/usr/bin/python3; do
    [ -x "$p" ] && usable "$p" && run_with "$p"
  done
fi

# 4. The Windows Python launcher, for Git Bash.
if command -v py >/dev/null 2>&1; then
  usable py -3 && run_with py -3
fi

# No usable Python. Hooks stay silent. The vault check says so.
if [ "$script" = doctor.py ]; then
  echo "[fix] No Python 3.9 or newer was found on this computer, so the vault's automatic helpers are switched off."
  echo "      Install Python 3.10 or newer (python.org has a free installer), reload the window, then run this check again."
fi
exit 0
