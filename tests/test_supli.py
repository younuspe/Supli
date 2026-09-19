"""Test suite for Supli.

These test real code paths: a real SQLite database, a real workspace on disk,
and real tool execution. The only stand-in is the provider, which is scripted
so results are deterministic and no live model is required.

Run: python -m pytest tests -q
"""

from __future__ import annotations

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supli.core.models import Permission, PermissionState  # noqa: E402
from supli.core.permissions import PermissionManager  # noqa: E402
from supli.core.state import StateStore  # noqa: E402
from supli.providers import (  # noqa: E402
    ChatMessage,
    ProviderRegistry,
    ProviderResponse,
    ScriptedProvider,
)
from supli.service import SupliService  # noqa: E402
from supli.tools.registry import ToolRegistry  # noqa: E402
from supli.tools.workspace import Workspace, WorkspaceViolation  # noqa: E402


@pytest.fixture()
def store(tmp_path):
    s = StateStore(tmp_path / "state.db")
    yield s
    s.close()


@pytest.fixture()
def workspace_dir(tmp_path):
    root = tmp_path / "ws"
    root.mkdir()
    (root / "main.py").write_text("print('hi')\n")
    (root / "roadmap.md").write_text("# Roadmap\n\n- item one\n")
    return root


@pytest.fixture()
def service(store):
    return SupliService(store, ProviderRegistry(ScriptedProvider()))


@pytest.fixture()
def project(service, workspace_dir):
    return service.create_project("test", str(workspace_dir))


# ---------------- workspace confinement ----------------

def test_path_escape_is_rejected(workspace_dir):
    ws = Workspace(workspace_dir)
    with pytest.raises(WorkspaceViolation):
        ws.resolve("../../etc/passwd")


def test_absolute_path_outside_is_rejected(workspace_dir):
    ws = Workspace(workspace_dir)
    with pytest.raises(WorkspaceViolation):
        ws.resolve("/etc/passwd")


def test_symlink_escape_is_rejected(workspace_dir, tmp_path):
    outside = tmp_path / "outside.txt"
    outside.write_text("secret")
    link = workspace_dir / "link.txt"
    link.symlink_to(outside)
    ws = Workspace(workspace_dir)
    with pytest.raises(WorkspaceViolation):
        ws.resolve("link.txt")


def test_internal_path_resolves(workspace_dir):
    ws = Workspace(workspace_dir)
    assert ws.resolve("main.py").name == "main.py"


# ---------------- permissions ----------------

def test_defaults_are_conservative(store, project):
    manager = PermissionManager(store)
    manager.ensure_defaults(project["id"])
    assert manager.check(project["id"], Permission.READ_FILE.value).allowed
    assert manager.check(project["id"], Permission.GITHUB.value).state == PermissionState.DENIED.value
    assert manager.check(project["id"], Permission.DELETE_FILE.value).needs_approval


def test_ask_permission_creates_approval_instead_of_running(store, project, workspace_dir):
    manager = PermissionManager(store)
    manager.ensure_defaults(project["id"])
    registry = ToolRegistry(store, manager)
    result = registry.execute(project["id"], Workspace(workspace_dir), "delete_file", path="main.py")
    assert not result.ok
    assert result.meta["approval_id"]
    assert (workspace_dir / "main.py").exists()


def test_denied_permission_never_runs(store, project, workspace_dir):
    manager = PermissionManager(store)
    manager.ensure_defaults(project["id"])
    manager.set(project["id"], Permission.RUN_COMMAND.value, PermissionState.DENIED.value)
    registry = ToolRegistry(store, manager)
    result = registry.execute(project["id"], Workspace(workspace_dir), "run_command", command="echo hi")
    assert not result.ok
    assert "denied" in result.error


def test_deleting_after_approval_actually_deletes(service, project, workspace_dir):
    result = service.tools.execute(
        project["id"], Workspace(workspace_dir), "delete_file", path="main.py"
    )
    service.decide_approval(project["id"], result.meta["approval_id"], True)
    assert not (workspace_dir / "main.py").exists()


# ---------------- git safety ----------------

@pytest.mark.parametrize("args", ["push origin main", "pull", "fetch", "remote add x y"])
def test_git_write_verbs_are_blocked(store, project, workspace_dir, args):
    manager = PermissionManager(store)
    manager.ensure_defaults(project["id"])
    manager.set(project["id"], Permission.GIT.value, PermissionState.ALLOWED.value)
    registry = ToolRegistry(store, manager)
    result = registry.execute(project["id"], Workspace(workspace_dir), "git", args=args)
    assert not result.ok, f"git {args} should be blocked"


def test_dangerous_command_is_blocked(store, project, workspace_dir):
    manager = PermissionManager(store)
    manager.ensure_defaults(project["id"])
    registry = ToolRegistry(store, manager)
    result = registry.execute(project["id"], Workspace(workspace_dir), "run_command", command="rm -rf /")
    assert not result.ok


# ---------------- files ----------------

def test_write_then_read_round_trip(service, project):
    service.save_file(project["id"], "new.txt", "content here")
    assert service.read_file(project["id"], "new.txt")["content"] == "content here"


def test_reading_missing_file_errors(service, project):
    with pytest.raises(ValueError):
        service.read_file(project["id"], "nope.txt")


def test_write_reports_real_diff(service, project):
    result = service.save_file(project["id"], "main.py", "print('bye')\n")
    assert result["changed"]
    assert "-print('hi')" in result["diff"]


# ---------------- documents ----------------

def test_document_version_increments_on_change(store, project):
    store.upsert_document(project["id"], "roadmap.md", "v1")
    doc = store.upsert_document(project["id"], "roadmap.md", "v2")
    assert doc.version == 2


def test_document_unchanged_content_does_not_bump_version(store, project):
    store.upsert_document(project["id"], "roadmap.md", "same")
    doc = store.upsert_document(project["id"], "roadmap.md", "same")
    assert doc.version == 1


def test_document_change_requires_approval(service, project):
    service.apply_document(project["id"], "roadmap.md", "original")
    result = service.propose_document(project["id"], "roadmap.md", "changed")
    assert result["approval_id"]
    assert service.get_document(project["id"], "roadmap.md")["content"] == "original"


def test_approved_document_change_applies(service, project):
    service.apply_document(project["id"], "roadmap.md", "original")
    result = service.propose_document(project["id"], "roadmap.md", "changed")
    service.decide_approval(project["id"], result["approval_id"], True)
    assert service.get_document(project["id"], "roadmap.md")["content"] == "changed"


def test_rejected_document_change_leaves_content(service, project):
    service.apply_document(project["id"], "roadmap.md", "original")
    result = service.propose_document(project["id"], "roadmap.md", "changed")
    service.decide_approval(project["id"], result["approval_id"], False)
    assert service.get_document(project["id"], "roadmap.md")["content"] == "original"


# ---------------- file edit approval ----------------

def test_rejected_file_edit_leaves_file_byte_identical(service, project, workspace_dir):
    before = (workspace_dir / "main.py").read_bytes()
    proposal = service.propose_file_edit(project["id"], "main.py", "print('nope')\n")
    service.decide_approval(project["id"], proposal["approval_id"], False)
    assert (workspace_dir / "main.py").read_bytes() == before


def test_approved_file_edit_applies_and_verifies(service, project, workspace_dir):
    proposal = service.propose_file_edit(project["id"], "main.py", "print('yes')\n")
    result = service.decide_approval(project["id"], proposal["approval_id"], True)
    assert result["applied"]["verified"]
    assert (workspace_dir / "main.py").read_text() == "print('yes')\n"


def test_approval_cannot_be_decided_twice(service, project):
    proposal = service.propose_file_edit(project["id"], "main.py", "print('x')\n")
    service.decide_approval(project["id"], proposal["approval_id"], True)
    with pytest.raises(ValueError):
        service.decide_approval(project["id"], proposal["approval_id"], True)


# ---------------- crash recovery ----------------

def test_pending_action_is_never_reported_complete(store, project):
    store.start_action(project["id"], "tool", "write_file")
    report_probe = store.interrupted_actions(project["id"])
    assert len(report_probe) == 1
    assert report_probe[0]["state"] == "pending"


def test_recovery_marks_interrupted(service, store, project):
    store.start_action(project["id"], "tool", "write_file")
    report = service.recover(project["id"])
    assert report["interrupted_count"] == 1
    assert store.interrupted_actions(project["id"]) == []
    assert store.list_actions(project["id"])[0]["state"] == "interrupted"


def test_finished_action_is_not_interrupted(store, project):
    action = store.start_action(project["id"], "tool", "read_file")
    store.finish_action(action, True)
    assert store.interrupted_actions(project["id"]) == []


# ---------------- engine behaviour ----------------

class RetryProvider(ScriptedProvider):
    """Fails a tool call then succeeds, to exercise bounded retry."""

    def __init__(self):
        super().__init__()
        self.calls = 0

    def chat(self, messages, model=None):
        self.calls += 1
        if self.calls <= 2:
            return ProviderResponse(
                content='```json\n{"tool": "read_file", "path": "missing.txt"}\n```',
                model="test", provider="retry",
            )
        return ProviderResponse(content="Recovered after inspecting the error.", model="test", provider="retry")


class AlwaysFailProvider(ScriptedProvider):
    def __init__(self):
        super().__init__()
        self.calls = 0

    def chat(self, messages, model=None):
        self.calls += 1
        return ProviderResponse(
            content='```json\n{"tool": "read_file", "path": "missing.txt"}\n```',
            model="test", provider="fail",
        )


def test_engine_retries_then_succeeds(store, workspace_dir):
    from supli.agent.engine import SupliEngine

    provider = RetryProvider()
    engine = SupliEngine(store, Workspace(workspace_dir), ToolRegistry(store, PermissionManager(store)), provider)
    project = store.create_project("t", str(workspace_dir))
    engine.project_id = project.id
    result = engine.run("read a file")
    assert result.status == "complete"
    assert result.retries >= 1


def test_engine_stops_after_retry_limit(store, workspace_dir):
    from supli.agent.engine import SupliEngine

    provider = AlwaysFailProvider()
    engine = SupliEngine(
        store, Workspace(workspace_dir), ToolRegistry(store, PermissionManager(store)),
        provider, max_retries=2,
    )
    project = store.create_project("t", str(workspace_dir))
    engine.project_id = project.id
    result = engine.run("read a missing file")
    assert result.status == "needs_input"
    assert result.retries == 2
    assert "missing.txt" in result.content


def test_engine_reports_provider_error_honestly(store, workspace_dir):
    from supli.agent.engine import SupliEngine
    from supli.providers import ProviderError

    class Broken(ScriptedProvider):
        def chat(self, messages, model=None):
            raise ProviderError("ollama unreachable")

    engine = SupliEngine(
        store, Workspace(workspace_dir), ToolRegistry(store, PermissionManager(store)), Broken()
    )
    project = store.create_project("t", str(workspace_dir))
    engine.project_id = project.id
    result = engine.run("hello")
    assert result.status == "error"
    assert "unreachable" in result.error


def test_plan_uses_real_filenames_only(store, workspace_dir):
    from supli.agent.engine import SupliEngine

    engine = SupliEngine(
        store, Workspace(workspace_dir), ToolRegistry(store, PermissionManager(store)),
        ScriptedProvider(),
    )
    project = store.create_project("t", str(workspace_dir))
    engine.project_id = project.id
    plan = engine.plan("update main.py")
    assert "main.py" in plan["files"]
    for step in plan["steps"]:
        for f in step["files"]:
            assert (workspace_dir / f).exists(), f"plan invented a file: {f}"


def test_ask_prefix_produces_clarification(store, workspace_dir):
    from supli.agent.engine import SupliEngine

    class Asking(ScriptedProvider):
        def chat(self, messages, model=None):
            return ProviderResponse(content="ASK: which file should I change?", model="t", provider="ask")

    engine = SupliEngine(
        store, Workspace(workspace_dir), ToolRegistry(store, PermissionManager(store)), Asking()
    )
    project = store.create_project("t", str(workspace_dir))
    engine.project_id = project.id
    result = engine.run("do something vague")
    assert result.status == "needs_input"
    assert "which file" in result.content


# ---------------- context ----------------

def test_context_is_bounded(store, workspace_dir):
    from supli.agent.context import ContextGatherer

    for i in range(50):
        (workspace_dir / f"file_{i}.py").write_text("x = 1\n" * 500)
    gatherer = ContextGatherer(Workspace(workspace_dir), max_files=3, max_chars=5000)
    bundle = gatherer.gather("update file")
    assert len(bundle.files) <= 3
    assert bundle.total_chars <= 6000


def test_context_prefers_explicit_paths(store, workspace_dir):
    from supli.agent.context import ContextGatherer

    bundle = ContextGatherer(Workspace(workspace_dir)).gather("anything", explicit_paths=["main.py"])
    assert bundle.files[0]["path"] == "main.py"


# ---------------- stages ----------------

def test_new_project_has_all_milestones(service, project):
    stages = service.list_stages(project["id"])
    assert len(stages) == 11
    assert {s["key"] for s in stages} >= {"m0", "m5", "m10"}


def test_stage_state_transitions_and_audits(service, project, store):
    service.set_stage_state(project["id"], "m0", "in_progress")
    assert service.current_stage(project["id"])["key"] == "m0"
    service.set_stage_state(project["id"], "m0", "complete")
    events = [e for e in store.list_events(project["id"]) if e["type"] == "stage_transition"]
    assert len(events) == 2


def test_unknown_stage_is_rejected(service, project):
    with pytest.raises(ValueError):
        service.set_stage_state(project["id"], "bogus", "in_progress")


# ---------------- audit ----------------

def test_tool_calls_are_recorded_in_history(service, project):
    service.read_file(project["id"], "main.py")
    actions = service.history(project["id"])["actions"]
    assert any(a["name"] == "read_file" and a["state"] == "success" for a in actions)


def test_denied_permission_is_audited(service, store, project, workspace_dir):
    service.set_permission(project["id"], Permission.RUN_COMMAND.value, PermissionState.DENIED.value)
    service.tools.execute(project["id"], Workspace(workspace_dir), "run_command", command="echo hi")
    events = [e for e in store.list_events(project["id"]) if e["type"] == "permission_denied"]
    assert events


# ---------------- API ----------------

@pytest.fixture()
def client(tmp_path):
    from fastapi.testclient import TestClient

    from supli.api.app import create_app

    return TestClient(create_app(str(tmp_path / "api.db")))


def test_health_reports_providers(client):
    body = client.get("/api/health").json()
    assert body["ok"]
    assert {p["provider"] for p in body["providers"]["providers"]} >= {"scripted", "ollama"}


def test_project_lifecycle_over_api(client, workspace_dir):
    project = client.post(
        "/api/projects", json={"name": "api", "workspace": str(workspace_dir)}
    ).json()
    assert client.get(f"/api/projects/{project['id']}").json()["name"] == "api"
    assert client.get(f"/api/projects/{project['id']}/stages").json()["stages"]


def test_api_rejects_unknown_project(client):
    assert client.get("/api/projects/missing").status_code == 404


def test_api_file_escape_returns_error(client, workspace_dir):
    project = client.post(
        "/api/projects", json={"name": "api", "workspace": str(workspace_dir)}
    ).json()
    response = client.get(
        f"/api/projects/{project['id']}/file", params={"path": "../../etc/passwd"}
    )
    assert response.status_code == 400


def test_api_ui_is_served(client):
    assert client.get("/").status_code == 200
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/styles.css").status_code == 200