"""Persistent project state on SQLite (roadmap §21, §22, §36).

Schema relationships:
    projects 1--n documents
    projects 1--n stages 1--n actions
    projects 1--n approvals
    projects 1--n sessions 1--n messages
    projects 1--n permissions
    projects 1--n events   (audit trail)
"""

from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .models import (
    ActionState,
    Approval,
    ApprovalState,
    Document,
    Message,
    Project,
    StageState,
    new_id,
    now,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    workspace TEXT NOT NULL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    content TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_documents_project ON documents(project_id, name);

CREATE TABLE IF NOT EXISTS stages (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    key TEXT NOT NULL,
    title TEXT NOT NULL,
    state TEXT NOT NULL,
    ord INTEGER NOT NULL,
    updated_at REAL NOT NULL,
    UNIQUE(project_id, key)
);

CREATE TABLE IF NOT EXISTS actions (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    stage_key TEXT,
    kind TEXT NOT NULL,
    name TEXT NOT NULL,
    state TEXT NOT NULL,
    detail TEXT NOT NULL DEFAULT '{}',
    result TEXT NOT NULL DEFAULT '{}',
    error TEXT NOT NULL DEFAULT '',
    retries INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    finished_at REAL
);
CREATE INDEX IF NOT EXISTS idx_actions_project ON actions(project_id, created_at);

CREATE TABLE IF NOT EXISTS approvals (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    summary TEXT NOT NULL,
    payload TEXT NOT NULL DEFAULT '{}',
    state TEXT NOT NULL,
    created_at REAL NOT NULL,
    decided_at REAL,
    decision_note TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_approvals_project ON approvals(project_id, state);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    created_at REAL NOT NULL,
    last_seen_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    session_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    content TEXT NOT NULL,
    meta TEXT NOT NULL DEFAULT '{}',
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, created_at);

CREATE TABLE IF NOT EXISTS permissions (
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    permission TEXT NOT NULL,
    state TEXT NOT NULL,
    updated_at REAL NOT NULL,
    PRIMARY KEY (project_id, permission)
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    payload TEXT NOT NULL DEFAULT '{}',
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_project ON events(project_id, id);
"""


class StateStore:
    """Thread-safe SQLite-backed state store.

    A single connection guarded by a lock is sufficient here because the
    application is local and single-process; it avoids SQLite's cross-thread
    connection restrictions.
    """

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    @contextmanager
    def _cursor(self) -> Iterator[sqlite3.Cursor]:
        with self._lock:
            cur = self._conn.cursor()
            try:
                yield cur
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise
            finally:
                cur.close()

    # ---------------- projects ----------------

    def create_project(self, name: str, workspace: str) -> Project:
        project = Project(id=new_id(), name=name, workspace=str(Path(workspace).resolve()))
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO projects (id, name, workspace, created_at) VALUES (?,?,?,?)",
                (project.id, project.name, project.workspace, project.created_at),
            )
        return project

    def get_project(self, project_id: str) -> Project | None:
        with self._cursor() as cur:
            row = cur.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
        return Project(**dict(row)) if row else None

    def list_projects(self) -> list[Project]:
        with self._cursor() as cur:
            rows = cur.execute("SELECT * FROM projects ORDER BY created_at").fetchall()
        return [Project(**dict(r)) for r in rows]

    # ---------------- documents ----------------

    def upsert_document(self, project_id: str, name: str, content: str) -> Document:
        """Write a document, bumping its version when content changes."""
        with self._cursor() as cur:
            row = cur.execute(
                "SELECT * FROM documents WHERE project_id=? AND name=?",
                (project_id, name),
            ).fetchone()
            ts = now()
            if row is None:
                doc = Document(id=new_id(), project_id=project_id, name=name, content=content)
                cur.execute(
                    "INSERT INTO documents (id, project_id, name, content, version, created_at, updated_at)"
                    " VALUES (?,?,?,?,?,?,?)",
                    (doc.id, doc.project_id, doc.name, doc.content, doc.version, doc.created_at, doc.updated_at),
                )
                return doc
            if row["content"] == content:
                return Document(**dict(row))
            cur.execute(
                "UPDATE documents SET content=?, version=version+1, updated_at=? WHERE id=?",
                (content, ts, row["id"]),
            )
            updated = dict(row)
            updated.update(content=content, version=row["version"] + 1, updated_at=ts)
            return Document(**updated)

    def get_document(self, project_id: str, name: str) -> Document | None:
        with self._cursor() as cur:
            row = cur.execute(
                "SELECT * FROM documents WHERE project_id=? AND name=?",
                (project_id, name),
            ).fetchone()
        return Document(**dict(row)) if row else None

    def list_documents(self, project_id: str) -> list[Document]:
        with self._cursor() as cur:
            rows = cur.execute(
                "SELECT * FROM documents WHERE project_id=? ORDER BY name",
                (project_id,),
            ).fetchall()
        return [Document(**dict(r)) for r in rows]

    def document_versions(self, project_id: str, name: str) -> list[dict[str, Any]]:
        """Version metadata for a document.

        Full historical bodies are not retained yet; this reports the current
        version and timestamps so the UI can show revision state honestly.
        """
        doc = self.get_document(project_id, name)
        if doc is None:
            return []
        return [
            {
                "version": doc.version,
                "created_at": doc.created_at,
                "updated_at": doc.updated_at,
                "current": True,
            }
        ]

    # ---------------- stages ----------------

    def init_stages(self, project_id: str, stages: list[tuple[str, str]]) -> None:
        with self._cursor() as cur:
            for i, (key, title) in enumerate(stages):
                cur.execute(
                    "INSERT OR IGNORE INTO stages (id, project_id, key, title, state, ord, updated_at)"
                    " VALUES (?,?,?,?,?,?,?)",
                    (new_id(), project_id, key, title, StageState.NOT_STARTED.value, i, now()),
                )

    def list_stages(self, project_id: str) -> list[dict[str, Any]]:
        with self._cursor() as cur:
            rows = cur.execute(
                "SELECT * FROM stages WHERE project_id=? ORDER BY ord", (project_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    def set_stage_state(self, project_id: str, key: str, state: str) -> None:
        with self._cursor() as cur:
            cur.execute(
                "UPDATE stages SET state=?, updated_at=? WHERE project_id=? AND key=?",
                (state, now(), project_id, key),
            )
        self.log_event(project_id, "stage_transition", {"key": key, "state": state})

    def current_stage(self, project_id: str) -> dict[str, Any] | None:
        for stage in self.list_stages(project_id):
            if stage["state"] in (StageState.IN_PROGRESS.value, StageState.PAUSED.value):
                return stage
        for stage in self.list_stages(project_id):
            if stage["state"] == StageState.NOT_STARTED.value:
                return stage
        return None

    # ---------------- actions ----------------

    def start_action(
        self, project_id: str, kind: str, name: str, stage_key: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> str:
        """Record an action as PENDING before it runs.

        Writing the row first is what makes crash recovery possible: a PENDING
        row left behind means the process died mid-action.
        """
        action_id = new_id()
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO actions (id, project_id, stage_key, kind, name, state, detail, created_at)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (
                    action_id, project_id, stage_key, kind, name,
                    ActionState.PENDING.value, json.dumps(detail or {}), now(),
                ),
            )
        return action_id

    def finish_action(
        self, action_id: str, success: bool, result: dict[str, Any] | None = None,
        error: str = "", retries: int = 0,
    ) -> None:
        with self._cursor() as cur:
            cur.execute(
                "UPDATE actions SET state=?, result=?, error=?, retries=?, finished_at=? WHERE id=?",
                (
                    ActionState.SUCCESS.value if success else ActionState.FAILED.value,
                    json.dumps(result or {}), error, retries, now(), action_id,
                ),
            )

    def list_actions(self, project_id: str, limit: int = 100) -> list[dict[str, Any]]:
        with self._cursor() as cur:
            rows = cur.execute(
                "SELECT * FROM actions WHERE project_id=? ORDER BY created_at DESC LIMIT ?",
                (project_id, limit),
            ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["detail"] = json.loads(d["detail"])
            d["result"] = json.loads(d["result"])
            out.append(d)
        return out

    def last_actions(self, project_id: str) -> dict[str, Any]:
        with self._cursor() as cur:
            def one(where: str, params: tuple) -> dict[str, Any] | None:
                row = cur.execute(
                    f"SELECT * FROM actions WHERE project_id=? AND {where}"
                    " ORDER BY created_at DESC LIMIT 1",
                    (project_id, *params),
                ).fetchone()
                if not row:
                    return None
                d = dict(row)
                d["detail"] = json.loads(d["detail"])
                d["result"] = json.loads(d["result"])
                return d

            return {
                "last_action": one("1=1", ()),
                "last_successful_action": one("state=?", (ActionState.SUCCESS.value,)),
                "last_failed_action": one("state=?", (ActionState.FAILED.value,)),
            }

    def interrupted_actions(self, project_id: str) -> list[dict[str, Any]]:
        """Actions still marked PENDING: they did not provably complete."""
        with self._cursor() as cur:
            rows = cur.execute(
                "SELECT * FROM actions WHERE project_id=? AND state=? ORDER BY created_at",
                (project_id, ActionState.PENDING.value),
            ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["detail"] = json.loads(d["detail"])
            out.append(d)
        return out

    def mark_interrupted(self, project_id: str) -> int:
        with self._cursor() as cur:
            cur.execute(
                "UPDATE actions SET state=?, finished_at=? WHERE project_id=? AND state=?",
                (ActionState.INTERRUPTED.value, now(), project_id, ActionState.PENDING.value),
            )
            return cur.rowcount

    # ---------------- approvals ----------------

    def create_approval(
        self, project_id: str, kind: str, summary: str, payload: dict[str, Any],
    ) -> Approval:
        approval = Approval(
            id=new_id(), project_id=project_id, kind=kind, summary=summary, payload=payload
        )
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO approvals (id, project_id, kind, summary, payload, state, created_at)"
                " VALUES (?,?,?,?,?,?,?)",
                (
                    approval.id, project_id, kind, summary,
                    json.dumps(payload), approval.state, approval.created_at,
                ),
            )
        self.log_event(project_id, "approval_requested", {"id": approval.id, "kind": kind})
        return approval

    def decide_approval(self, approval_id: str, approved: bool, note: str = "") -> Approval | None:
        state = ApprovalState.APPROVED.value if approved else ApprovalState.REJECTED.value
        with self._cursor() as cur:
            cur.execute(
                "UPDATE approvals SET state=?, decided_at=?, decision_note=? WHERE id=?",
                (state, now(), note, approval_id),
            )
            row = cur.execute("SELECT * FROM approvals WHERE id=?", (approval_id,)).fetchone()
        if not row:
            return None
        approval = self._approval_from_row(row)
        self.log_event(
            approval.project_id,
            "approval_decided",
            {"id": approval_id, "state": state, "note": note},
        )
        return approval

    def get_approval(self, approval_id: str) -> Approval | None:
        with self._cursor() as cur:
            row = cur.execute("SELECT * FROM approvals WHERE id=?", (approval_id,)).fetchone()
        return self._approval_from_row(row) if row else None

    def list_approvals(self, project_id: str, state: str | None = None) -> list[Approval]:
        sql = "SELECT * FROM approvals WHERE project_id=?"
        params: list[Any] = [project_id]
        if state:
            sql += " AND state=?"
            params.append(state)
        sql += " ORDER BY created_at DESC"
        with self._cursor() as cur:
            rows = cur.execute(sql, tuple(params)).fetchall()
        return [self._approval_from_row(r) for r in rows]

    @staticmethod
    def _approval_from_row(row: sqlite3.Row) -> Approval:
        d = dict(row)
        d["payload"] = json.loads(d["payload"])
        return Approval(**d)

    # ---------------- sessions & messages ----------------

    def create_session(self, project_id: str) -> str:
        session_id = new_id()
        ts = now()
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO sessions (id, project_id, created_at, last_seen_at) VALUES (?,?,?,?)",
                (session_id, project_id, ts, ts),
            )
        return session_id

    def touch_session(self, session_id: str) -> None:
        with self._cursor() as cur:
            cur.execute("UPDATE sessions SET last_seen_at=? WHERE id=?", (now(), session_id))

    def add_message(
        self, project_id: str, session_id: str, kind: str, content: str,
        meta: dict[str, Any] | None = None,
    ) -> Message:
        message = Message(
            id=new_id(), project_id=project_id, session_id=session_id,
            kind=kind, content=content, meta=meta or {},
        )
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO messages (id, project_id, session_id, kind, content, meta, created_at)"
                " VALUES (?,?,?,?,?,?,?)",
                (
                    message.id, project_id, session_id, kind, content,
                    json.dumps(message.meta), message.created_at,
                ),
            )
        return message

    def list_messages(self, session_id: str, limit: int = 200) -> list[Message]:
        with self._cursor() as cur:
            rows = cur.execute(
                "SELECT * FROM messages WHERE session_id=? ORDER BY created_at LIMIT ?",
                (session_id, limit),
            ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["meta"] = json.loads(d["meta"])
            out.append(Message(**d))
        return out

    # ---------------- permissions ----------------

    def set_permission(self, project_id: str, permission: str, state: str) -> None:
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO permissions (project_id, permission, state, updated_at) VALUES (?,?,?,?)"
                " ON CONFLICT(project_id, permission) DO UPDATE SET state=excluded.state,"
                " updated_at=excluded.updated_at",
                (project_id, permission, state, now()),
            )
        self.log_event(
            project_id, "permission_decision", {"permission": permission, "state": state}
        )

    def get_permissions(self, project_id: str) -> dict[str, str]:
        with self._cursor() as cur:
            rows = cur.execute(
                "SELECT permission, state FROM permissions WHERE project_id=?", (project_id,)
            ).fetchall()
        return {r["permission"]: r["state"] for r in rows}

    # ---------------- audit events ----------------

    def log_event(self, project_id: str, type_: str, payload: dict[str, Any] | None = None) -> None:
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO events (project_id, type, payload, created_at) VALUES (?,?,?,?)",
                (project_id, type_, json.dumps(payload or {}), now()),
            )

    def list_events(self, project_id: str, limit: int = 200) -> list[dict[str, Any]]:
        with self._cursor() as cur:
            rows = cur.execute(
                "SELECT * FROM events WHERE project_id=? ORDER BY id DESC LIMIT ?",
                (project_id, limit),
            ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["payload"] = json.loads(d["payload"])
            out.append(d)
        return out