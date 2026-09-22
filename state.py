import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / ".supli" / "state.db"

def _now():
    return datetime.now(timezone.utc).isoformat()

def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("""CREATE TABLE IF NOT EXISTS project_state
        (key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL)""")
    con.execute("""CREATE TABLE IF NOT EXISTS history
        (id INTEGER PRIMARY KEY AUTOINCREMENT, event TEXT NOT NULL, details TEXT, created_at TEXT NOT NULL)""")
    con.execute("""CREATE TABLE IF NOT EXISTS approvals
        (id INTEGER PRIMARY KEY AUTOINCREMENT, tool TEXT NOT NULL, arguments TEXT NOT NULL,
         status TEXT NOT NULL, created_at TEXT NOT NULL)""")
    con.commit()
    return con

def set_state(key, value):
    with get_connection() as con:
        con.execute("INSERT INTO project_state(key,value,updated_at) VALUES(?,?,?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",
                    (key, value, _now()))
        con.commit()

def get_state(key, default=None):
    with get_connection() as con:
        row = con.execute("SELECT value FROM project_state WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

def add_history(event, details=""):
    with get_connection() as con:
        con.execute("INSERT INTO history(event,details,created_at) VALUES(?,?,?)", (event, details, _now()))
        con.commit()

def add_approval(tool, arguments):
    with get_connection() as con:
        cur = con.execute("INSERT INTO approvals(tool,arguments,status,created_at) VALUES(?,?,?,?)",
                          (tool, arguments, "pending", _now()))
        con.commit()
        return cur.lastrowid

def get_pending_approvals():
    with get_connection() as con:
        return [dict(r) for r in con.execute(
            "SELECT * FROM approvals WHERE status='pending' ORDER BY id").fetchall()]

def resolve_approval(approval_id, status):
    with get_connection() as con:
        con.execute("UPDATE approvals SET status=? WHERE id=?", (status, approval_id))
        con.commit()
