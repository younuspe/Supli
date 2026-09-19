"""Supli agent engine (SKILL §5, §9, §10; roadmap §19).

Workflow:
    Understand -> Inspect -> Plan -> Edit -> Run -> Review -> Retry -> Complete/Ask

The engine is deliberately UI-independent so it can be driven from the API,
the terminal, or a test. It never invents files or results: plans are built
from the real workspace, and every claim comes from a real tool result.

Retries are bounded. When the limit is reached the engine stops and reports
what it tried rather than guessing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from ..core.models import MessageKind
from ..core.state import StateStore
from ..providers.base import ChatMessage, ProviderError
from ..tools.registry import ToolRegistry
from ..tools.workspace import Workspace, WorkspaceViolation
from .context import ContextGatherer

MAX_RETRIES = 3
MAX_STEPS = 12

SYSTEM_PROMPT = """You are Supli, a local development agent working inside a controlled workspace.

Rules you must follow:
- Operate only from reality. Never invent files, paths, results, or tests.
- Inspect before planning. Use real filenames from the provided context.
- Make the smallest safe change.
- Never claim a test passed unless it actually passed.
- Never run git push or git pull.
- If you cannot safely continue, stop and ask the user.

To use a tool, emit a fenced JSON block:
```json
{"tool": "read_file", "path": "relative/path"}
```
Available tools and their arguments:
__TOOLS__

When you have completed the task or are answering directly, reply in plain prose.
When you are blocked and need the user to decide, begin your reply with "ASK:".
"""


@dataclass
class PlanStep:
    description: str
    files: list[str] = field(default_factory=list)
    tool: str | None = None
    arguments: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "files": self.files,
            "tool": self.tool,
            "arguments": self.arguments,
        }


@dataclass
class EngineResult:
    status: str
    content: str
    steps: list[dict[str, Any]] = field(default_factory=list)
    retries: int = 0
    needs_approval: str | None = None
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "content": self.content,
            "steps": self.steps,
            "retries": self.retries,
            "needs_approval": self.needs_approval,
            "error": self.error,
        }


class SupliEngine:
    def __init__(
        self,
        store: StateStore,
        workspace: Workspace,
        tools: ToolRegistry,
        provider,
        session_id: str | None = None,
        stage_key: str | None = None,
        max_retries: int = MAX_RETRIES,
    ) -> None:
        self.store = store
        self.workspace = workspace
        self.tools = tools
        self.provider = provider
        self.project_id = ""
        self.session_id = session_id
        self.stage_key = stage_key
        self.max_retries = max_retries
        self.context = ContextGatherer(workspace)

    # ---------------- inspection ----------------

    def inspect(self, request: str, explicit_paths: list[str] | None = None) -> dict[str, Any]:
        bundle = self.context.gather(request, explicit_paths)
        return {
            "workspace": str(self.workspace.root),
            "tree": self.workspace.tree(),
            "context_files": [f["path"] for f in bundle.files],
            "documents": bundle.documents,
            "_bundle": bundle,
        }

    # ---------------- planning ----------------

    def plan(self, request: str, explicit_paths: list[str] | None = None) -> dict[str, Any]:
        """Build a plan grounded in real files discovered from the workspace."""
        inspection = self.inspect(request, explicit_paths)
        relevant = inspection["context_files"]
        steps = [
            PlanStep(
                description="Inspect the current workspace and identify the real files involved",
                files=relevant[:5],
            ).to_dict()
        ]
        for rel in relevant[:5]:
            verb = "Inspect" if rel.endswith(".md") else "Inspect and, if needed, modify"
            steps.append(PlanStep(description=f"{verb} {rel}", files=[rel]).to_dict())
        if not relevant:
            steps.append(
                PlanStep(
                    description="No existing project files matched; create the minimum new file the task requires",
                    files=[],
                ).to_dict()
            )
        steps.append(
            PlanStep(description="Run the relevant test or command and review the real output").to_dict()
        )
        plan = {
            "request": request,
            "workspace": inspection["workspace"],
            "files": relevant,
            "documents": inspection["documents"],
            "steps": steps,
        }
        if self.session_id:
            self.store.add_message(
                self.project_id, self.session_id, MessageKind.PLAN.value,
                json.dumps(plan, indent=2),
            )
        return plan

    # ---------------- execution ----------------

    def run(self, request: str, explicit_paths: list[str] | None = None) -> EngineResult:
        """Answer or act on a request, driving tool calls with bounded retries."""
        if self.session_id:
            self.store.add_message(
                self.project_id, self.session_id, MessageKind.USER.value, request
            )

        inspection = self.inspect(request, explicit_paths)
        bundle = inspection["_bundle"]
        system = SYSTEM_PROMPT.replace(
            "__TOOLS__", json.dumps(self.tools.describe(), indent=2)
        )
        prompt = (
            f"Workspace: {inspection['workspace']}\n"
            f"Project documents present: {', '.join(inspection['documents']) or 'none'}\n\n"
            f"Relevant project files:\n{bundle.to_prompt()}\n\n"
            f"User request:\n{request}"
        )

        transcript: list[ChatMessage] = [ChatMessage("system", system), ChatMessage("user", prompt)]
        steps: list[dict[str, Any]] = []
        retries = 0
        attempts = 0

        while attempts < MAX_STEPS:
            attempts += 1
            try:
                response = self.provider.chat(transcript)
            except ProviderError as exc:
                return self._fail(f"provider error: {exc}", steps, retries)

            call = _parse_call(response.content)
            if call is None:
                content = response.content.strip()
                if content.startswith("ASK:"):
                    return self._ask(content[4:].strip(), steps, retries)
                return self._complete(content, steps, retries)

            step = self._execute_tool_call(call)
            steps.append(step)

            if step.get("approval_id"):
                return EngineResult(
                    status="needs_approval",
                    content=(
                        f"Tool {call['tool']} requires approval before it can run "
                        f"(approval {step['approval_id']})."
                    ),
                    steps=steps,
                    retries=retries,
                    needs_approval=step["approval_id"],
                )

            if not step["ok"] and step.get("retryable"):
                if retries >= self.max_retries:
                    return self._ask(
                        self._retry_exhausted_message(call, step, retries), steps, retries
                    )
                retries += 1
                transcript.append(ChatMessage("assistant", response.content))
                transcript.append(
                    ChatMessage(
                        "user",
                        f"Tool {call['tool']} failed (attempt {retries}/{self.max_retries}): "
                        f"{step['error']}\nRead the real error, inspect the relevant file, "
                        f"and try the smallest safe correction.",
                    )
                )
                continue

            transcript.append(ChatMessage("assistant", response.content))
            transcript.append(
                ChatMessage("user", f"Tool {call['tool']} result:\n{_compact(step)}")
            )

        return self._ask(
            "Reached the maximum number of steps without finishing. "
            "The task needs a decision on how to proceed.",
            steps,
            retries,
        )

    def _execute_tool_call(self, call: dict[str, Any]) -> dict[str, Any]:
        tool = call["tool"]
        args = {k: v for k, v in call.items() if k != "tool"}
        result = self.tools.execute(
            self.project_id, self.workspace, tool, stage_key=self.stage_key, **args
        )
        step = {
            "tool": tool,
            "arguments": args,
            "ok": result.ok,
            "error": result.error,
            "output": result.output,
            # A permission gate or a transient failure is worth retrying or
            # escalating; a workspace violation or unknown tool is not.
            "retryable": _is_retryable(tool, result),
            "approval_id": result.meta.get("approval_id"),
        }
        if self.session_id:
            kind = MessageKind.TOOL_RESULT if result.ok else MessageKind.ERROR
            self.store.add_message(
                self.project_id, self.session_id, kind.value,
                f"{tool}: {'ok' if result.ok else result.error}",
                meta={"tool": tool, "arguments": args, "output": _safe(result.output)},
            )
        return step

    def apply_approved_edit(
        self, path: str, content: str
    ) -> dict[str, Any]:
        """Apply an edit after approval, verifying the file really changed."""
        try:
            target = self.workspace.resolve(path)
        except WorkspaceViolation as exc:
            return {"ok": False, "error": str(exc)}
        before = target.read_text(encoding="utf-8", errors="replace") if target.exists() else ""
        result = self.tools.execute(
            self.project_id, self.workspace, "write_file", stage_key=self.stage_key,
            path=path, content=content,
        )
        after = target.read_text(encoding="utf-8", errors="replace") if target.exists() else ""
        return {
            "ok": result.ok,
            "verified": result.ok and after == content,
            "changed": before != after,
            "path": path,
            "diff": result.meta.get("diff", ""),
            "error": result.error,
        }

    # ---------------- result helpers ----------------

    def _complete(self, content: str, steps: list[dict], retries: int) -> EngineResult:
        if self.session_id:
            self.store.add_message(
                self.project_id, self.session_id, MessageKind.RESULT.value, content
            )
        return EngineResult("complete", content, steps, retries)

    def _ask(self, content: str, steps: list[dict], retries: int) -> EngineResult:
        if self.session_id:
            self.store.add_message(
                self.project_id, self.session_id, MessageKind.CLARIFICATION.value, content
            )
        return EngineResult("needs_input", content, steps, retries)

    def _fail(self, error: str, steps: list[dict], retries: int) -> EngineResult:
        if self.session_id:
            self.store.add_message(
                self.project_id, self.session_id, MessageKind.ERROR.value, error
            )
        return EngineResult("error", error, steps, retries, error=error)

    @staticmethod
    def _retry_exhausted_message(call: dict, step: dict, retries: int) -> str:
        return (
            f"I was attempting the tool {call['tool']} and it failed {retries} times.\n"
            f"Last real error: {step.get('error') or 'unknown'}\n"
            f"Arguments used: {json.dumps(call)}\n"
            "I have stopped rather than guessing. A decision is required on how to proceed."
        )


def _parse_call(text: str) -> dict[str, Any] | None:
    from ..providers.base import parse_tool_call

    return parse_tool_call(text)


def _is_retryable(tool: str, result) -> bool:
    if result.ok:
        return False
    if result.meta.get("approval_id"):
        return False
    if "unknown tool" in result.error or "escapes workspace" in result.error:
        return False
    if "blocked by safety policy" in result.error:
        return False
    return True


def _compact(step: dict[str, Any], limit: int = 3000) -> str:
    text = json.dumps({k: v for k, v in step.items() if k != "retryable"}, default=str)
    return text[:limit]


def _safe(value: Any, limit: int = 3000) -> Any:
    if isinstance(value, str):
        return value[:limit]
    if isinstance(value, dict):
        return {k: _safe(v, limit) for k, v in list(value.items())[:20]}
    if isinstance(value, list):
        return [_safe(v, limit) for v in value[:20]]
    return value