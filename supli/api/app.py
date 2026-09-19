"""Application / API layer (roadmap §10).

Thin HTTP surface over SupliService. No agent logic lives here.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from supli.core.state import StateStore
from supli.providers import OllamaProvider, ProviderRegistry, ScriptedProvider
from supli.service import SupliService

DEFAULT_DB = os.environ.get("SUPLI_DB", str(Path.home() / ".supli" / "supli.db"))
OLLAMA_URL = os.environ.get("SUPLI_OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("SUPLI_OLLAMA_MODEL", "")


def build_registry() -> ProviderRegistry:
    """Register available providers.

    Scripted is always present so the path is usable offline; Ollama is the
    real foundation and becomes active when reachable.
    """
    registry = ProviderRegistry()
    ollama = OllamaProvider(OLLAMA_URL, OLLAMA_MODEL) if OLLAMA_MODEL else OllamaProvider(OLLAMA_URL)
    scripted = ScriptedProvider()
    registry.register(scripted)
    registry.register(ollama)
    if ollama.status().get("available"):
        registry.activate(ollama.name)
    else:
        registry.activate(scripted.name)
    return registry


class ProjectIn(BaseModel):
    name: str
    workspace: str


class FileIn(BaseModel):
    path: str
    content: str


class ChatIn(BaseModel):
    message: str
    session_id: str | None = None


class PlanIn(BaseModel):
    request: str
    paths: list[str] | None = None


class DocumentIn(BaseModel):
    name: str
    content: str


class DecisionIn(BaseModel):
    approved: bool
    note: str = ""


class PermissionIn(BaseModel):
    permission: str
    state: str


class StageIn(BaseModel):
    key: str
    state: str


class CommandIn(BaseModel):
    command: str
    timeout: int = 60


def create_app(db_path: str | None = None) -> FastAPI:
    store = StateStore(db_path or DEFAULT_DB)
    service = SupliService(store, build_registry())

    app = FastAPI(title="Supli", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.service = service
    app.state.store = store



    def guard(fn, *args, **kwargs) -> Any:
        try:
            return fn(*args, **kwargs)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    # ---------------- meta ----------------

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {"ok": True, "providers": service.provider_status()}

    # ---------------- projects ----------------

    @app.get("/api/projects")
    def list_projects() -> list[dict[str, Any]]:
        return service.list_projects()

    @app.post("/api/projects")
    def create_project(body: ProjectIn) -> dict[str, Any]:
        return guard(service.create_project, body.name, body.workspace)

    @app.get("/api/projects/{project_id}")
    def get_project(project_id: str) -> dict[str, Any]:
        return guard(service.get_project, project_id)

    @app.get("/api/projects/{project_id}/tree")
    def tree(project_id: str) -> list[dict[str, Any]]:
        return guard(service.tree, project_id)

    @app.get("/api/projects/{project_id}/inspect")
    def inspect(project_id: str, request: str = "") -> dict[str, Any]:
        return guard(service.inspect, project_id, request)

    # ---------------- files ----------------

    @app.get("/api/projects/{project_id}/file")
    def read_file(project_id: str, path: str) -> dict[str, Any]:
        return guard(service.read_file, project_id, path)

    @app.put("/api/projects/{project_id}/file")
    def save_file(project_id: str, body: FileIn) -> dict[str, Any]:
        return guard(service.save_file, project_id, body.path, body.content)

    @app.post("/api/projects/{project_id}/file/propose")
    def propose_file(project_id: str, body: FileIn) -> dict[str, Any]:
        return guard(service.propose_file_edit, project_id, body.path, body.content)

    # ---------------- chat / plan ----------------

    @app.post("/api/projects/{project_id}/chat")
    def chat(project_id: str, body: ChatIn) -> dict[str, Any]:
        return guard(service.chat, project_id, body.message, body.session_id)

    @app.post("/api/projects/{project_id}/plan")
    def plan(project_id: str, body: PlanIn) -> dict[str, Any]:
        return guard(service.plan, project_id, body.request, body.paths)

    @app.get("/api/projects/{project_id}/messages")
    def messages(project_id: str, session_id: str) -> list[dict[str, Any]]:
        return [m.to_dict() for m in store.list_messages(session_id)]

    # ---------------- documents ----------------

    @app.get("/api/projects/{project_id}/documents")
    def documents(project_id: str) -> list[dict[str, Any]]:
        return guard(service.list_documents, project_id)

    @app.post("/api/projects/{project_id}/documents/seed")
    def seed_documents(project_id: str) -> list[dict[str, Any]]:
        return guard(service.seed_documents, project_id)

    @app.get("/api/projects/{project_id}/documents/{name}")
    def get_document(project_id: str, name: str) -> dict[str, Any]:
        return guard(service.get_document, project_id, name)

    @app.post("/api/projects/{project_id}/documents/propose")
    def propose_document(project_id: str, body: DocumentIn) -> dict[str, Any]:
        return guard(service.propose_document, project_id, body.name, body.content)

    # ---------------- approvals ----------------

    @app.get("/api/projects/{project_id}/approvals")
    def approvals(project_id: str, state: str | None = None) -> list[dict[str, Any]]:
        return guard(service.list_approvals, project_id, state)

    @app.post("/api/projects/{project_id}/approvals/{approval_id}/decide")
    def decide(project_id: str, approval_id: str, body: DecisionIn) -> dict[str, Any]:
        return guard(service.decide_approval, project_id, approval_id, body.approved, body.note)

    # ---------------- permissions ----------------

    @app.get("/api/projects/{project_id}/permissions")
    def permissions(project_id: str) -> dict[str, str]:
        return guard(service.get_permissions, project_id)

    @app.post("/api/projects/{project_id}/permissions")
    def set_permission(project_id: str, body: PermissionIn) -> dict[str, str]:
        return guard(service.set_permission, project_id, body.permission, body.state)

    # ---------------- stages ----------------

    @app.get("/api/projects/{project_id}/stages")
    def stages(project_id: str) -> dict[str, Any]:
        return {
            "stages": guard(service.list_stages, project_id),
            "current": service.current_stage(project_id),
        }

    @app.post("/api/projects/{project_id}/stages")
    def set_stage(project_id: str, body: StageIn) -> dict[str, Any]:
        return guard(service.set_stage_state, project_id, body.key, body.state)

    # ---------------- terminal / tools / history / recovery ----------------

    @app.post("/api/projects/{project_id}/command")
    def command(project_id: str, body: CommandIn) -> dict[str, Any]:
        return guard(service.run_command, project_id, body.command, body.timeout)

    @app.get("/api/projects/{project_id}/tools")
    def detect_tools(project_id: str) -> dict[str, Any]:
        return guard(service.detect_tools, project_id)

    @app.get("/api/projects/{project_id}/history")
    def history(project_id: str, limit: int = 100) -> dict[str, Any]:
        return guard(service.history, project_id, limit)

    @app.post("/api/projects/{project_id}/recover")
    def recover(project_id: str) -> dict[str, Any]:
        return guard(service.recover, project_id)

    @app.get("/api/projects/{project_id}/git")
    def git(project_id: str) -> dict[str, Any]:
        return guard(service.git_status, project_id)

    # ---------------- providers ----------------

    @app.get("/api/providers")
    def providers() -> dict[str, Any]:
        return service.provider_status()

    @app.post("/api/providers/{name}/activate")
    def activate(name: str) -> dict[str, Any]:
        return guard(service.activate_provider, name)

    @app.get("/api/providers/{name}/models")
    def models(name: str) -> list[str]:
        return guard(service.provider_models, name)

    # ---------------- static frontend ----------------

    frontend_dir = Path(__file__).resolve().parents[2] / "frontend"
    if frontend_dir.exists():
        app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

        @app.get("/")
        def index() -> FileResponse:
            return FileResponse(str(frontend_dir / "index.html"))

    return app