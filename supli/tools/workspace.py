"""Workspace confinement (SKILL §8, §16).

The workspace restriction is the foundational security rule: every path a tool
touches must resolve inside the project workspace, symlinks included.
"""

from __future__ import annotations

import os
from pathlib import Path


class WorkspaceViolation(Exception):
    """Raised when a path escapes the project workspace."""


class Workspace:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def resolve(self, relative: str, must_exist: bool = False) -> Path:
        """Resolve a workspace-relative path, rejecting any escape.

        Uses realpath so a symlink pointing outside the workspace is rejected
        rather than followed.
        """
        if os.path.isabs(relative):
            candidate = Path(relative)
        else:
            candidate = self.root / relative
        real = Path(os.path.realpath(candidate))
        root_real = Path(os.path.realpath(self.root))
        if real != root_real and root_real not in real.parents:
            raise WorkspaceViolation(f"path escapes workspace: {relative}")
        if must_exist and not real.exists():
            raise WorkspaceViolation(f"path does not exist: {relative}")
        return real

    def relative(self, path: str | Path) -> str:
        return str(Path(path).resolve().relative_to(self.root))

    def tree(self, max_entries: int = 2000) -> list[dict[str, object]]:
        """Flat listing of the workspace, skipping noise directories."""
        skip = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".mypy_cache"}
        entries: list[dict[str, object]] = []
        count = 0
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = sorted(d for d in dirnames if d not in skip and not d.startswith("."))
            for name in sorted(filenames):
                if name.startswith("."):
                    continue
                full = Path(dirpath) / name
                try:
                    rel = full.relative_to(self.root)
                except ValueError:
                    continue
                entries.append(
                    {
                        "path": str(rel),
                        "name": name,
                        "dir": str(rel.parent) if str(rel.parent) != "." else "",
                        "size": full.stat().st_size,
                        "is_dir": False,
                    }
                )
                count += 1
                if count >= max_entries:
                    return entries
            for name in dirnames:
                full = Path(dirpath) / name
                try:
                    rel = full.relative_to(self.root)
                except ValueError:
                    continue
                entries.append(
                    {"path": str(rel), "name": name, "dir": str(rel.parent) if str(rel.parent) != "." else "", "size": 0, "is_dir": True}
                )
        return entries