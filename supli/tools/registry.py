"""Tool registry and permission enforcement (SKILL §15).

Call flow:
    request -> permission check -> (approval gate if ASK) -> execute -> audit

The registry never executes a tool whose permission is DENIED, and returns an
approval request rather than running when the permission is ASK.
"""

from __future__ import annotations

from typing import Any

from ..core.permissions import PermissionManager
from ..core.state import StateStore
from .impl import ToolResult, ToolSpec, build_tool_specs
from .workspace import Workspace


class ToolRegistry:
    def __init__(self, store: StateStore, permissions: PermissionManager) -> None:
        self.store = store
        self.permissions = permissions
        self._specs: dict[str, ToolSpec] = {spec.name: spec for spec in build_tool_specs()}

    def names(self) -> list[str]:
        return sorted(self._specs)

    def describe(self) -> list[dict[str, Any]]:
        return [
            {
                "name": s.name,
                "description": s.description,
                "permission": s.permission,
                "parameters": s.parameters,
            }
            for s in self._specs.values()
        ]

    def spec(self, name: str) -> ToolSpec | None:
        return self._specs.get(name)

    def execute(
        self,
        project_id: str,
        workspace: Workspace,
        name: str,
        stage_key: str | None = None,
        **kwargs: Any,
    ) -> ToolResult:
        spec = self._specs.get(name)
        if spec is None:
            return ToolResult(False, error=f"unknown tool: {name}")

        decision = self.permissions.check(project_id, spec.permission)
        if decision.needs_approval:
            approval = self.store.create_approval(
                project_id,
                kind="permission",
                summary=f"Tool {name} requires permission {spec.permission}",
                payload={"tool": name, "permission": spec.permission, "arguments": kwargs},
            )
            return ToolResult(
                False,
                error="permission requires approval",
                meta={"approval_id": approval.id, "permission": spec.permission},
            )
        if not decision.allowed:
            self.store.log_event(
                project_id, "permission_denied", {"tool": name, "permission": spec.permission}
            )
            return ToolResult(
                False,
                error=f"permission denied: {spec.permission}",
                meta={"permission": spec.permission},
            )

        action_id = self.store.start_action(
            project_id, kind="tool", name=name, stage_key=stage_key,
            detail={"arguments": {k: _truncate(v) for k, v in kwargs.items()}},
        )
        self.store.log_event(project_id, "tool_call", {"tool": name})
        try:
            result = spec.func(workspace, **kwargs)
        except WorkspaceViolation as exc:  # pragma: no cover - defensive
            result = ToolResult(False, error=str(exc))
        except Exception as exc:  # pragma: no cover - defensive
            result = ToolResult(False, error=f"{type(exc).__name__}: {exc}")

        self.store.finish_action(
            action_id, result.ok,
            result={"output": _truncate(result.output)}, error=result.error,
        )
        result.meta.setdefault("action_id", action_id)
        return result


def _truncate(value: Any, limit: int = 2000) -> Any:
    if isinstance(value, str) and len(value) > limit:
        return value[:limit] + f"... ({len(value)} chars)"
    if isinstance(value, dict):
        return {k: _truncate(v, limit) for k, v in value.items()}
    if isinstance(value, list):
        return [_truncate(v, limit) for v in value[:50]]
    return value