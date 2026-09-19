"""Roadmap milestone definitions (Master Roadmap §40).

These are application/architecture milestones. They are deliberately distinct
from the agent capability stages in SKILL.md §23, which must not be conflated.
"""

from __future__ import annotations

MILESTONES: list[tuple[str, str]] = [
    ("m0", "Milestone 0 — Vertical Slice (UI → Backend → Provider → UI)"),
    ("m1", "Milestone 1 — Project Explorer + Workspace + Basic Editor"),
    ("m2", "Milestone 2 — Chat + Supli Engine + Tools + Files"),
    ("m3", "Milestone 3 — Planning + File Edits + Diff + Review"),
    ("m4", "Milestone 4 — Project State + SQLite + Stage State + History + Recovery"),
    ("m5", "Milestone 5 — Approvals + Permissions + Security"),
    ("m6", "Milestone 6 — Terminal + Preview + Development Tools"),
    ("m7", "Milestone 7 — AI Provider / Model Manager + Integrations"),
    ("m8", "Milestone 8 — Multiplatform Tools + UI Designer"),
    ("m9", "Milestone 9 — Advanced Context Management + Optional Retrieval"),
    ("m10", "Milestone 10 — Security + Testing + Recovery + Audit + Performance + Release"),
]


def milestone_keys() -> list[str]:
    return [key for key, _ in MILESTONES]