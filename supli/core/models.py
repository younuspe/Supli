"""Core domain models shared across Supli layers."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any


def new_id() -> str:
    return uuid.uuid4().hex


def now() -> float:
    return time.time()


class Permission(str, Enum):
    """Explicit permission categories (roadmap §32)."""

    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    DELETE_FILE = "delete_file"
    RUN_COMMAND = "run_command"
    NETWORK_ACCESS = "network_access"
    GIT = "git"
    GITHUB = "github"
    EXTERNAL_SERVICE = "external_service"
    SYSTEM_ACCESS = "system_access"
    PLATFORM_TOOL = "platform_tool"
    SECURITY_TOOL = "security_tool"


class PermissionState(str, Enum):
    # DENIED and ASK are distinct: ASK routes to the approval gate,
    # DENIED fails immediately without creating an approval.
    ALLOWED = "allowed"
    ASK = "ask"
    DENIED = "denied"


class ApprovalState(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ActionState(str, Enum):
    # PENDING means "started, not yet known to have completed" — crash
    # recovery treats these as interrupted, never as successful.
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class StageState(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETE = "complete"


class MessageKind(str, Enum):
    """Chat must distinguish these roles (roadmap §15)."""

    USER = "user"
    PLAN = "plan"
    TOOL_ACTIVITY = "tool_activity"
    TOOL_RESULT = "tool_result"
    APPROVAL_REQUEST = "approval_request"
    RESULT = "result"
    ERROR = "error"
    CLARIFICATION = "clarification"


@dataclass
class Project:
    id: str
    name: str
    workspace: str
    created_at: float = field(default_factory=now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Approval:
    id: str
    project_id: str
    kind: str
    summary: str
    payload: dict[str, Any]
    state: str = ApprovalState.PENDING.value
    created_at: float = field(default_factory=now)
    decided_at: float | None = None
    decision_note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ActionRecord:
    """Audit record for one agent/tool action (roadmap §36)."""

    id: str
    project_id: str
    kind: str
    name: str
    state: str = ActionState.PENDING.value
    detail: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    retries: int = 0
    created_at: float = field(default_factory=now)
    finished_at: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Document:
    id: str
    project_id: str
    name: str
    content: str
    version: int = 1
    created_at: float = field(default_factory=now)
    updated_at: float = field(default_factory=now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Message:
    id: str
    project_id: str
    session_id: str
    kind: str
    content: str
    meta: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)