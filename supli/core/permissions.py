"""Permission gate (roadmap §32, SKILL §16).

Every tool call passes through here before execution. Dangerous capabilities
default to ASK so they cannot silently become available.
"""

from __future__ import annotations

from typing import Any

from .models import Permission, PermissionState
from .state import StateStore

# Defaults are deliberately conservative: anything that writes, executes, or
# reaches outside the process requires explicit approval.
DEFAULT_PERMISSIONS: dict[str, str] = {
    Permission.READ_FILE.value: PermissionState.ALLOWED.value,
    Permission.WRITE_FILE.value: PermissionState.ALLOWED.value,
    Permission.DELETE_FILE.value: PermissionState.ASK.value,
    Permission.RUN_COMMAND.value: PermissionState.ALLOWED.value,
    Permission.NETWORK_ACCESS.value: PermissionState.ASK.value,
    Permission.GIT.value: PermissionState.ASK.value,
    Permission.GITHUB.value: PermissionState.DENIED.value,
    Permission.EXTERNAL_SERVICE.value: PermissionState.DENIED.value,
    Permission.SYSTEM_ACCESS.value: PermissionState.DENIED.value,
    Permission.PLATFORM_TOOL.value: PermissionState.DENIED.value,
    Permission.SECURITY_TOOL.value: PermissionState.ASK.value,
}


class PermissionDecision:
    __slots__ = ("permission", "state", "reason")

    def __init__(self, permission: str, state: str, reason: str = "") -> None:
        self.permission = permission
        self.state = state
        self.reason = reason

    @property
    def allowed(self) -> bool:
        return self.state == PermissionState.ALLOWED.value

    @property
    def needs_approval(self) -> bool:
        return self.state == PermissionState.ASK.value

    def to_dict(self) -> dict[str, Any]:
        return {
            "permission": self.permission,
            "state": self.state,
            "reason": self.reason,
            "allowed": self.allowed,
            "needs_approval": self.needs_approval,
        }


class PermissionManager:
    def __init__(self, store: StateStore) -> None:
        self.store = store

    def ensure_defaults(self, project_id: str) -> None:
        existing = self.store.get_permissions(project_id)
        for permission, state in DEFAULT_PERMISSIONS.items():
            if permission not in existing:
                self.store.set_permission(project_id, permission, state)

    def all(self, project_id: str) -> dict[str, str]:
        self.ensure_defaults(project_id)
        return self.store.get_permissions(project_id)

    def check(self, project_id: str, permission: str) -> PermissionDecision:
        state = self.all(project_id).get(permission)
        if state is None:
            return PermissionDecision(
                permission, PermissionState.DENIED.value, "unrecognised permission"
            )
        return PermissionDecision(permission, state)

    def set(self, project_id: str, permission: str, state: str) -> None:
        if permission not in {p.value for p in Permission}:
            raise ValueError(f"unknown permission: {permission}")
        if state not in {s.value for s in PermissionState}:
            raise ValueError(f"unknown permission state: {state}")
        self.store.set_permission(project_id, permission, state)