"""Tool implementations (roadmap §16, SKILL §15).

Tools are separate from the model: the model requests a capability, Supli
decides whether it may actually run. Each tool declares the permission it
requires; the registry enforces that before calling it.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from ..core.models import Permission
from .diff import make_diff, summarize_diff
from .workspace import Workspace, WorkspaceViolation

MAX_READ_BYTES = 400_000
COMMAND_TIMEOUT = 60


@dataclass
class ToolResult:
    ok: bool
    output: Any = None
    error: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "output": self.output, "error": self.error, "meta": self.meta}


@dataclass
class ToolSpec:
    name: str
    description: str
    permission: str
    parameters: dict[str, str]
    func: Callable[..., ToolResult]


def _read_file(ws: Workspace, path: str) -> ToolResult:
    try:
        target = ws.resolve(path, must_exist=True)
    except WorkspaceViolation as exc:
        return ToolResult(False, error=str(exc))
    if target.is_dir():
        return ToolResult(False, error=f"is a directory: {path}")
    size = target.stat().st_size
    try:
        data = target.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return ToolResult(False, error=str(exc))
    truncated = size > MAX_READ_BYTES
    return ToolResult(
        True,
        output=data[:MAX_READ_BYTES],
        meta={"path": path, "size": size, "truncated": truncated},
    )


def _write_file(ws: Workspace, path: str, content: str) -> ToolResult:
    try:
        target = ws.resolve(path)
    except WorkspaceViolation as exc:
        return ToolResult(False, error=str(exc))
    existed = target.exists()
    previous = target.read_text(encoding="utf-8", errors="replace") if existed else ""
    if target.is_dir():
        return ToolResult(False, error=f"is a directory: {path}")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    except OSError as exc:
        return ToolResult(False, error=str(exc))
    diff = make_diff(previous, content, path)
    return ToolResult(
        True,
        output={"path": path, "created": not existed, "bytes": len(content.encode())},
        meta={"diff": diff},
    )


def _delete_file(ws: Workspace, path: str) -> ToolResult:
    try:
        target = ws.resolve(path, must_exist=True)
    except WorkspaceViolation as exc:
        return ToolResult(False, error=str(exc))
    if target.is_dir():
        return ToolResult(False, error=f"refusing to delete directory: {path}")
    previous = target.read_text(encoding="utf-8", errors="replace")
    try:
        target.unlink()
    except OSError as exc:
        return ToolResult(False, error=str(exc))
    return ToolResult(
        True,
        output={"path": path, "deleted": True},
        meta={"diff": make_diff(previous, "", path)},
    )


def _list_dir(ws: Workspace, path: str = ".") -> ToolResult:
    try:
        target = ws.resolve(path, must_exist=True)
    except WorkspaceViolation as exc:
        return ToolResult(False, error=str(exc))
    if not target.is_dir():
        return ToolResult(False, error=f"not a directory: {path}")
    entries = []
    for child in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        if child.name.startswith(".") or child.name in {"node_modules", "__pycache__"}:
            continue
        entries.append({"name": child.name, "is_dir": child.is_dir()})
    return ToolResult(True, output=entries, meta={"path": path})


# Commands that would let the model reconfigure or escape its sandbox are
# blocked outright rather than trusted to the permission gate.
BLOCKED_COMMAND_PATTERNS = (
    "rm -rf /",
    "mkfs",
    "shutdown",
    "reboot",
    ":(){",
    "chmod -R 777 /",
    "dd if=/dev/zero",
)


def _run_command(ws: Workspace, command: str, timeout: int = COMMAND_TIMEOUT) -> ToolResult:
    lowered = command.lower()
    for pattern in BLOCKED_COMMAND_PATTERNS:
        if pattern in lowered:
            return ToolResult(False, error=f"command blocked by safety policy: {pattern!r}")
    timeout = max(1, min(int(timeout), 300))
    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=str(ws.root),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return ToolResult(False, error=f"command timed out after {timeout}s", meta={"timeout": timeout})
    except OSError as exc:
        return ToolResult(False, error=str(exc))
    out = (proc.stdout or "")[-100_000:]
    err = (proc.stderr or "")[-100_000:]
    return ToolResult(
        proc.returncode == 0,
        output={"stdout": out, "stderr": err, "returncode": proc.returncode, "command": command},
        error="" if proc.returncode == 0 else f"exit code {proc.returncode}",
        meta={"command": command, "returncode": proc.returncode, "timeout": timeout},
    )


def _git(ws: Workspace, args: str) -> ToolResult:
    """Git access is limited to read-only inspection.

    SKILL §8 and roadmap §26 forbid automatic push/pull, so those verbs are
    rejected here regardless of permissions.
    """
    parts = args.strip().split()
    if not parts:
        return ToolResult(False, error="no git subcommand given")
    verb = parts[0]
    forbidden = {"push", "pull", "fetch", "remote", "clone"}
    if verb in forbidden:
        return ToolResult(
            False,
            error=f"git {verb} is not permitted automatically (SKILL §8); run it manually",
        )
    if verb not in {"status", "log", "diff", "show", "branch", "rev-parse", "ls-files"}:
        return ToolResult(False, error=f"git {verb} is not in the allowed read-only set")
    return _run_command(ws, f"git {verb} " + " ".join(parts[1:]))


def _propose_edit(ws: Workspace, path: str, content: str) -> ToolResult:
    """Build a diff for review without touching the file (roadmap §17)."""
    try:
        target = ws.resolve(path)
    except WorkspaceViolation as exc:
        return ToolResult(False, error=str(exc))
    previous = target.read_text(encoding="utf-8", errors="replace") if target.exists() else ""
    diff = make_diff(previous, content, path)
    if not diff:
        return ToolResult(True, output={"path": path, "changed": False, "diff": ""})
    return ToolResult(
        True,
        output={"path": path, "changed": True, "diff": diff, "preview": summarize_diff(diff)},
        meta={"diff": diff, "previous": previous, "proposed": content},
    )


def _detect_tools(ws: Workspace) -> ToolResult:
    """Detect actually-available platform tools (roadmap §29).

    Reports only what is found on PATH; absence is reported as absence rather
    than assumed.
    """
    import shutil

    candidates = {
        "python": ["python3", "python"],
        "node": ["node"],
        "npm": ["npm"],
        "git": ["git"],
        "docker": ["docker"],
        "ollama": ["ollama"],
        "gcc": ["gcc", "clang"],
        "make": ["make"],
        "java": ["java"],
        "rustc": ["rustc"],
        "go": ["go"],
        "adb": ["adb"],
        "flutter": ["flutter"],
    }
    detected: dict[str, str | None] = {}
    for name, binaries in candidates.items():
        found = None
        for binary in binaries:
            location = shutil.which(binary)
            if location:
                found = location
                break
        detected[name] = found
    return ToolResult(
        True,
        output=detected,
        meta={"platform": sys.platform, "available_count": sum(1 for v in detected.values() if v)},
    )


def build_tool_specs() -> list[ToolSpec]:
    return [
        ToolSpec(
            "read_file", "Read a UTF-8 text file inside the workspace",
            Permission.READ_FILE.value, {"path": "str"}, _read_file,
        ),
        ToolSpec(
            "write_file", "Write a UTF-8 text file inside the workspace",
            Permission.WRITE_FILE.value, {"path": "str", "content": "str"}, _write_file,
        ),
        ToolSpec(
            "delete_file", "Delete a file inside the workspace",
            Permission.DELETE_FILE.value, {"path": "str"}, _delete_file,
        ),
        ToolSpec(
            "list_dir", "List directory entries inside the workspace",
            Permission.READ_FILE.value, {"path": "str"}, _list_dir,
        ),
        ToolSpec(
            "run_command", "Run a shell command in the workspace root",
            Permission.RUN_COMMAND.value, {"command": "str", "timeout": "int"}, _run_command,
        ),
        ToolSpec(
            "git", "Run a read-only git command",
            Permission.GIT.value, {"args": "str"}, _git,
        ),
        ToolSpec(
            "propose_edit", "Produce a reviewable diff without writing",
            Permission.READ_FILE.value, {"path": "str", "content": "str"}, _propose_edit,
        ),
        ToolSpec(
            "detect_tools", "Detect available platform development tools",
            Permission.PLATFORM_TOOL.value, {}, _detect_tools,
        ),
    ]