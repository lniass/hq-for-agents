#!/usr/bin/env python3
"""HQ context check: report this thread's context size and whether a handoff is due.

Usage: python3 -I ~/hq/context_check.py <nonce>

Pass a fresh, unique nonce typed literally in the command (for example
`ctx-notifications-2026-11-13-4`, never `$(...)`). The transcript records the
command as typed, which is how the script finds the right session file among
parallel threads.

Prints one JSON line:
  {"session": ..., "user_messages": N, "context_tokens": T,
   "threshold": 300000, "every": 10, "check_due": bool, "handoff_due": bool}

check_due is true once `every` or more user messages arrived since the last
check; handoff_due = check_due and context_tokens > threshold. Each run that is
check_due records the count, so the next check comes `every` messages later.
Thresholds live in state.json (`contextHandoffTokens`,
`contextCheckEveryMessages`) so they can be retuned without editing this file.

Paths can be overridden with environment variables:
  HQ_HOME          folder holding state.json (default ~/hq)
  CLAUDE_PROJECTS  Claude Code transcript folder (default ~/.claude/projects)
Note: `python3 -I` ignores PYTHON* variables but still passes these through.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

HQ_HOME = Path(os.environ.get("HQ_HOME", Path.home() / "hq")).expanduser()
PROJECTS = Path(os.environ.get("CLAUDE_PROJECTS", Path.home() / ".claude" / "projects")).expanduser()
STATE = HQ_HOME / "state.json"
CHECKS = HQ_HOME / "context-checks"
RECENT_FILES = 200


def find_transcript(nonce: str) -> Path | None:
    # The current session is being written right now; look at recent files first.
    files = sorted(PROJECTS.glob("*/*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    for path in files[:RECENT_FILES]:
        try:
            if nonce in path.read_text(errors="ignore"):
                return path
        except OSError:
            continue
    return None


def measure(path: Path) -> tuple[int, int]:
    """Return (user_messages, latest context tokens) for one transcript."""
    user_messages = 0
    context_tokens = 0
    for line in path.read_text(errors="ignore").splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if not isinstance(entry, dict):
            continue
        message = entry.get("message") or {}
        if not isinstance(message, dict):
            continue
        if entry.get("type") == "user" and not entry.get("isMeta"):
            content = message.get("content")
            is_tool_result = isinstance(content, list) and any(
                isinstance(c, dict) and c.get("type") == "tool_result" for c in content
            )
            if not is_tool_result:
                user_messages += 1
        usage = message.get("usage")
        if isinstance(usage, dict):
            context_tokens = (
                usage.get("input_tokens", 0)
                + usage.get("cache_read_input_tokens", 0)
                + usage.get("cache_creation_input_tokens", 0)
            )
    return user_messages, context_tokens


def main() -> int:
    if len(sys.argv) != 2 or len(sys.argv[1]) < 12:
        print(json.dumps({"error": "pass one unique nonce of 12+ characters"}))
        return 2
    nonce = sys.argv[1]
    path = None
    for _ in range(10):  # the transcript line holding the nonce may land a moment later
        path = find_transcript(nonce)
        if path:
            break
        time.sleep(0.5)
    if path is None:
        print(json.dumps({"error": "transcript not found for nonce"}))
        return 1

    user_messages, context_tokens = measure(path)

    try:
        state = json.loads(STATE.read_text())
    except (OSError, ValueError):
        state = {}
    threshold = int(state.get("contextHandoffTokens", 300000))
    every = int(state.get("contextCheckEveryMessages", 10))

    CHECKS.mkdir(parents=True, exist_ok=True)
    marker = CHECKS / f"{path.stem}.json"
    try:
        last = json.loads(marker.read_text()).get("checked_at_messages", 0)
    except (OSError, ValueError):
        last = 0
    check_due = user_messages - last >= every
    if check_due:
        marker.write_text(json.dumps({"checked_at_messages": user_messages, "context_tokens": context_tokens}))

    print(json.dumps({
        "session": path.stem,
        "user_messages": user_messages,
        "context_tokens": context_tokens,
        "threshold": threshold,
        "every": every,
        "check_due": check_due,
        "handoff_due": check_due and context_tokens > threshold,
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
