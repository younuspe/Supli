"""Unified diff generation and application (roadmap §17, §35).

Edits are proposed as diffs so the user can approve or reject before anything
is written. Rejection must leave the file byte-identical.
"""

from __future__ import annotations

import difflib


def make_diff(old: str, new: str, path: str = "file", context: int = 3) -> str:
    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    # A trailing newline change would otherwise be invisible to difflib.
    if old and not old.endswith("\n"):
        old_lines[-1] = old_lines[-1] + "\n"
    if new and not new.endswith("\n"):
        new_lines[-1] = new_lines[-1] + "\n"
    diff = difflib.unified_diff(
        old_lines, new_lines, fromfile=f"a/{path}", tofile=f"b/{path}", n=context
    )
    return "".join(diff)


def diff_stats(diff: str) -> dict[str, int]:
    added = sum(1 for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in diff.splitlines() if line.startswith("-") and not line.startswith("---"))
    return {"added": added, "removed": removed}


def summarize_diff(diff: str, limit: int = 40) -> str:
    lines = diff.splitlines()
    if len(lines) <= limit:
        return diff
    return "\n".join(lines[:limit]) + f"\n... ({len(lines) - limit} more lines)"