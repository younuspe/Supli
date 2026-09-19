"""Application service layer (roadmap §10).

The API layer talks only to this service; the UI never reaches into the
engine or store directly. This keeps the agent engine usable independently
of the UI.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .agent.engine import SupliEngine
from .core.models import (
    ApprovalState,
    MessageKind,
    PermissionState,
    StageState,
)
from .core.permissions import PermissionManager
from .core.stages import MILESTONES, milestone_keys
from .core.state import StateStore
from .providers.base import ProviderError, ProviderRegistry
from .tools.diff import diff_stats, make_diff
from .tools.registry import ToolRegistry
from .tools.workspace import Workspace

PROJECT_DOCUMENTS = ("roadmap.md", "SKILL.md", "README.md")


class SupliService:
    def __init__(self, store: StateStore, providers: ProviderRegistry) -> None:
        self.store = store
        self.providers = providers
        self.permissions = PermissionManager(store)
        self.tools = ToolRegistry(store, self.permissions)

    # ---------------- projects ----------------

    def create_project(self, name: str, workspace: str) -> dict[str, Any]:
        project = self.store.create_project(name, workspace)
        self.store.init_stages(project.id, MILESTONES)
        self.permissions.ensure_defaults(project.id)
        self.store.log_event(project.id, "project_created", {"name": name})
        return project.to_dict()

    def get_project(self, project_id: str) -> dict[str, Any]:
        project = self.store.get_project(project_id)
        if project is None:
            raise KeyError(f"no such project: {project_id}")
        return project.to_dict()

    def list_projects(self) -> list[dict[str, Any]]:
        return [p.to_dict() for p in self.store.list_projects()]

    def workspace(self, project_id: str) -> Workspace:
        return Workspace(self.store.get_project(project_id).workspace)

    # ---------------- explorer / editor (M1) ----------------

    def tree(self, project_id: str) -> list[dict[str, Any]]:
        return self.workspace(project_id).tree()

    def read_file(self, project_id: str, path: str) -> dict[str, Any]:
        result = self.tools.execute(project_id, self.workspace(project_id), "read_file", path=path)
        if not result.ok:
            raise ValueError(result.error)
        return {"path": path, "content": result.output, "meta": result.meta}

    def save_file(self, project_id: str, path: str, content: str) -> dict[str, Any]:
        """Direct editor save (M1). Reviewed edits go through the approval flow."""
        workspace = self.workspace(project_id)
        target = workspace.resolve(path)
        before = target.read_text(encoding="utf-8", errors="replace") if target.exists() else ""
        result = self.tools.execute(project_id, workspace, "write_file", path=path, content=content)
        if not result.ok:
            raise ValueError(result.error)
        return {
            "path": path,
            "created": result.output["created"],
            "diff": result.meta.get("diff", ""),
            "changed": before != content,
        }

    # ---------------- documents (M2/M3) ----------------

    def seed_documents(self, project_id: str) -> list[dict[str, Any]]:
        """Copy roadmap/SKILL/README from the workspace into project state."""
        workspace = self.workspace(project_id)
        seeded = []
        for name in PROJECT_DOCUMENTS:
            candidate = workspace.root / name
            if candidate.exists():
                content = candidate.read_text(encoding="utf-8", errors="replace")
                doc = self.store.upsert_document(project_id, name, content)
                seeded.append(doc.to_dict())
        return seeded

    def list_documents(self, project_id: str) -> list[dict[str, Any]]:
        return [d.to_dict() for d in self.store.list_documents(project_id)]

    def get_document(self, project_id: str, name: str) -> dict[str, Any]:
        doc = self.store.get_document(project_id, name)
        if doc is None:
            raise KeyError(f"no such document: {name}")
        return doc.to_dict()

    def propose_document(self, project_id: str, name: str, content: str) -> dict[str, Any]:
        """Documents are important: change requires approval (SKILL §11)."""
        current = self.store.get_document(project_id, name)
        existing = current.content if current else ""
        diff = make_diff(existing, content, name)
        approval = self.store.create_approval(
            project_id,
            kind="document",
            summary=f"Update {name}",
            payload={"name": name, "content": content, "diff": diff},
        )
        return {
            "approval_id": approval.id,
            "name": name,
            "diff": diff,
            "stats": diff_stats(diff),
        }

    def apply_document(self, project_id: str, name: str, content: str) -> dict[str, Any]:
        doc = self.store.upsert_document(project_id, name, content)
        self.store.log_event(project_id, "document_updated", {"name": name, "version": doc.version})
        return doc.to_dict()

    # ---------------- approvals (M3/M5) ----------------

    def list_approvals(self, project_id: str, state: str | None = None) -> list[dict[str, Any]]:
        return [a.to_dict() for a in self.store.list_approvals(project_id, state)]

    def decide_approval(
        self, project_id: str, approval_id: str, approved: bool, note: str = ""
    ) -> dict[str, Any]:
        approval = self.store.get_approval(approval_id)
        if approval is None or approval.project_id != project_id:
            raise KeyError(f"no such approval: {approval_id}")
        if approval.state != ApprovalState.PENDING.value:
            raise ValueError(f"approval already {approval.state}")
        decided = self.store.decide_approval(approval_id, approved, note)
        applied: dict[str, Any] | None = None

        if approved:
            if approval.kind == "document":
                applied = self.apply_document(
                    project_id, approval.payload["name"], approval.payload["content"]
                )
            elif approval.kind == "file_edit":
                engine = SupliEngine(
                    self.store, self.workspace(project_id), self.tools, self.providers.active()
                )
                engine.project_id = project_id
                applied = engine.apply_approved_edit(
                    approval.payload["path"], approval.payload["content"]
                )
            elif approval.kind == "permission":
                permission = approval.payload["permission"]
                self.permissions.set(project_id, permission, PermissionState.ALLOWED.value)
                applied = {"permission": permission, "state": PermissionState.ALLOWED.value}
                # Granting permission alone would silently drop the request the
                # user just approved, so the blocked tool call is re-run now.
                tool = approval.payload.get("tool")
                if tool:
                    result = self.tools.execute(
                        project_id, self.workspace(project_id), tool,
                        **approval.payload.get("arguments", {}),
                    )
                    applied = {
                        **applied,
                        "tool": tool,
                        "executed": result.ok,
                        "output": result.output,
                        "error": result.error,
                    }
        return {"approval": decided.to_dict(), "applied": applied}

    def propose_file_edit(self, project_id: str, path: str, content: str) -> dict[str, Any]:
        workspace = self.workspace(project_id)
        result = self.tools.execute(
            project_id, workspace, "propose_edit", path=path, content=content
        )
        if not result.ok:
            raise ValueError(result.error)
        if not result.output["changed"]:
            return {"changed": False, "path": path, "diff": ""}
        approval = self.store.create_approval(
            project_id,
            kind="file_edit",
            summary=f"Edit {path}",
            payload={"path": path, "content": content, "diff": result.output["diff"]},
        )
        return {
            "changed": True,
            "approval_id": approval.id,
            "path": path,
            "diff": result.output["diff"],
            "stats": diff_stats(result.output["diff"]),
        }

    # ---------------- permissions (M5) ----------------

    def get_permissions(self, project_id: str) -> dict[str, str]:
        return self.permissions.all(project_id)

    def set_permission(self, project_id: str, permission: str, state: str) -> dict[str, str]:
        self.permissions.set(project_id, permission, state)
        return self.permissions.all(project_id)

    # ---------------- stages (M4) ----------------

    def list_stages(self, project_id: str) -> list[dict[str, Any]]:
        return self.store.list_stages(project_id)

    def current_stage(self, project_id: str) -> dict[str, Any] | None:
        return self.store.current_stage(project_id)

    def set_stage_state(self, project_id: str, key: str, state: str) -> dict[str, Any]:
        if key not in milestone_keys():
            raise ValueError(f"unknown stage: {key}")
        if state not in {s.value for s in StageState}:
            raise ValueError(f"unknown stage state: {state}")
        self.store.set_stage_state(project_id, key, state)
        return {"key": key, "state": state, "stages": self.list_stages(project_id)}

    # ---------------- chat + engine (M2/M3) ----------------

    def chat(self, project_id: str, message: str, session_id: str | None = None) -> dict[str, Any]:
        session_id = session_id or self.store.create_session(project_id)
        self.store.touch_session(session_id)
        current = self.store.current_stage(project_id)
        engine = SupliEngine(
            self.store,
            self.workspace(project_id),
            self.tools,
            self.providers.active(),
            session_id=session_id,
            stage_key=current["key"] if current else None,
        )
        engine.project_id = project_id
        try:
            result = engine.run(message)
        except ProviderError as exc:
            self.store.add_message(
                project_id, session_id, MessageKind.ERROR.value, str(exc)
            )
            result = None
            error = str(exc)
        return {
            "session_id": session_id,
            "result": result.to_dict() if result else None,
            "error": "" if result else error,
            "messages": [m.to_dict() for m in self.store.list_messages(session_id)],
        }

    def plan(self, project_id: str, request: str, paths: list[str] | None = None) -> dict[str, Any]:
        engine = SupliEngine(
            self.store, self.workspace(project_id), self.tools, self.providers.active()
        )
        engine.project_id = project_id
        return engine.plan(request, paths)

    def inspect(self, project_id: str, request: str = "") -> dict[str, Any]:
        engine = SupliEngine(
            self.store, self.workspace(project_id), self.tools, self.providers.active()
        )
        engine.project_id = project_id
        inspection = engine.inspect(request)
        inspection.pop("_bundle", None)
        return inspection

    def run_command(self, project_id: str, command: str, timeout: int = 60) -> dict[str, Any]:
        result = self.tools.execute(
            project_id, self.workspace(project_id), "run_command",
            command=command, timeout=timeout,
        )
        if result.meta.get("approval_id"):
            return {"ok": False, "needs_approval": result.meta["approval_id"], "error": result.error}
        return result.to_dict()

    def detect_tools(self, project_id: str) -> dict[str, Any]:
        result = self.tools.execute(project_id, self.workspace(project_id), "detect_tools")
        if result.meta.get("approval_id"):
            return {
                "ok": False,
                "needs_approval": result.meta["approval_id"],
                "error": result.error,
                "permission": result.meta.get("permission"),
            }
        return result.to_dict()

    # ---------------- history / audit (M4/M10) ----------------

    def history(self, project_id: str, limit: int = 100) -> dict[str, Any]:
        return {
            "actions": self.store.list_actions(project_id, limit),
            "events": self.store.list_events(project_id, limit),
            "last": self.store.last_actions(project_id),
        }

    # ---------------- recovery (M4) ----------------

    def recover(self, project_id: str) -> dict[str, Any]:
        """Reconstruct state after an interruption (roadmap §22).

        PENDING actions are real evidence the process died mid-action; they are
        marked INTERRUPTED and never reported as completed.
        """
        interrupted = self.store.interrupted_actions(project_id)
        marked = self.store.mark_interrupted(project_id)
        pending_approvals = [
            a.to_dict() for a in self.store.list_approvals(project_id, ApprovalState.PENDING.value)
        ]
        current = self.store.current_stage(project_id)
        history = self.store.list_actions(project_id, limit=200)
        last_test = next(
            (
                a for a in history
                if a["kind"] in {"tool", "command"}
                and ("test" in a["name"].lower() or "test" in str(a.get("detail", {})).lower())
            ),
            None,
        )
        report = {
            "current_stage": current,
            "interrupted_actions": [
                {"id": a["id"], "name": a["name"], "detail": a["detail"]} for a in interrupted
            ],
            "interrupted_count": marked,
            "pending_approvals": pending_approvals,
            "last_known_test": last_test,
            "summary": self.store.last_actions(project_id),
        }
        self.store.log_event(
            project_id, "recovery_run", {"interrupted": marked, "pending": len(pending_approvals)}
        )
        return report

    # ---------------- providers (M7) ----------------

    def provider_status(self) -> dict[str, Any]:
        return self.providers.status()

    def activate_provider(self, name: str) -> dict[str, Any]:
        self.providers.activate(name)
        return self.providers.status()

    def provider_models(self, name: str) -> list[str]:
        provider = self.providers.get(name)
        if provider is None:
            raise KeyError(f"unknown provider: {name}")
        return provider.models()

    # ---------------- integrations (M7) ----------------

    def git_status(self, project_id: str) -> dict[str, Any]:
        result = self.tools.execute(project_id, self.workspace(project_id), "git", args="status")
        if result.meta.get("approval_id"):
            return {"ok": False, "needs_approval": result.meta["approval_id"], "error": result.error}
        return result.to_dict()