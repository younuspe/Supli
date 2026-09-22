# SKILL: Supli

Supli is a local-first AI coding environment.

## Rules
1. Inspect the real workspace before planning or editing.
2. Never invent files, paths, commands, results, or completed work.
3. Keep all project operations inside the configured workspace.
4. Read relevant files before changing them.
5. Make the smallest safe change and verify it.
6. Run commands only through the controlled tool layer.
7. Never use git push or git pull automatically.
8. Respect approval gates for writes and command execution.
9. On failure, inspect the real error, correct safely, and retry only within limits.
10. If still stuck, stop and report the real file, command, error, and attempts.
11. Do not modify unrelated files.
12. Detect platform tools instead of assuming they exist.

## Workflow
Understand → Inspect → Plan → Edit → Run → Review → Retry → Complete / Ask

## Application milestones
0. UI → Backend → Ollama → Qwen → UI
1. Project Explorer + Workspace + Basic Editor
2. Chat + Supli Engine + Tools + Files
3. Planning + File-specific Edits + Diff + Review
4. Project State + SQLite + Stage State + History + Crash Recovery
5. Approvals + Permissions + Security
6. Terminal + Preview + Development Tools
7. AI Provider / Model Manager + Integrations
8. Multiplatform Tools + UI Designer
9. Advanced Context Management + Optional Semantic Retrieval / RAG
10. Security + Testing + Crash Recovery + Audit + Performance + Release

## Current checkpoint
Milestones 0–7 were completed during development. Milestone 8 is in progress: platform detection and the UI Designer foundation are implemented; component text, width and height properties were verified. X/Y properties were not completed.

The agent must preserve this checkpoint and must not claim Milestone 8 is finished.
