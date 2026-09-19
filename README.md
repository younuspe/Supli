# Supli

Supli is a local development workspace and AI coding environment.

It is designed to help define, develop, test, review, and manage software projects while keeping the real project files, roadmap, documents, tools, permissions, and development state under controlled user direction.

## Current Architecture

The current implementation is:

`Supli UI → Application/API Layer → Supli Agent Engine → Tool Layer → Workspace`

The agent engine remains usable independently of the UI.

## Implemented Foundation

```text
supli/
├── core/        state (SQLite), permissions, models, milestones
├── tools/       workspace confinement, tool registry, diff engine
├── providers/   Ollama and scripted providers behind one interface
├── agent/       context gathering, plan/edit/run/review/retry engine
├── api/         FastAPI application layer
└── service.py   application service the API calls
frontend/        Project Explorer, Code Editor, Supli Chat, dockable views
tests/           44 tests (confinement, permissions, diffs, recovery, API)
supli.py         entry point
```

`docs/STATUS.md` records exactly what is built and verified, and what is not.

## What Works Today

- Local web UI with Project Explorer, Code Editor, and Supli Chat
- Real workspace inspection and file read/write inside a confined workspace
- A bounded agent loop: inspect → plan → edit → run → review → retry → ask
- Plans built only from real filenames found in the workspace
- Diff-based edits with approve/reject; rejection leaves files untouched
- Eleven permission categories with conservative defaults and an approval gate
- SQLite project state: stages, actions, approvals, documents, messages, audit
- Crash recovery that marks interrupted actions as interrupted, never complete
- Terminal, Activity, Changes/Diff, Requirements, Approvals, Diagnostics,
  Stage Progress, and Platform Tools views
- Git access limited to read-only inspection; push/pull are refused
- Platform tool detection that reports absence as absence

## Not Yet Implemented

Preview, UI Designer, semantic retrieval/RAG, GitHub/GitLab integrations,
drag-and-dock layout rearrangement, and release packaging. See
`docs/STATUS.md` for the full and current list.

A live Ollama/Qwen round-trip has not been verified in the build environment;
the adapter is implemented and its failure path is tested.

## Running

```bash
pip install -r requirements.txt
python supli.py
```

Then open http://127.0.0.1:8000.

```bash
python -m pytest tests -q    # 44 tests
```

## AI Model

Supli connects to a local Ollama model and, when Ollama is unreachable, falls
back to a deterministic scripted provider so the application still runs. The
scripted provider is not an AI model.

Environment variables:

- `SUPLI_DB` — SQLite state path (default `~/.supli/supli.db`)
- `SUPLI_OLLAMA_URL` — default `http://localhost:11434`
- `SUPLI_OLLAMA_MODEL` — model name

## Development Principles

Supli follows these principles:

1. Read before changing.
2. Inspect before planning.
3. Use real filenames and paths.
4. Never invent project structure.
5. Never claim an action that was not performed.
6. Never claim a test passed without actually testing it.
7. Make small, verifiable changes.
8. Review failures using real diagnostics.
9. Retry only within defined limits.
10. Ask the user when it cannot safely continue.
11. Never automatically perform Git push or Git pull.
12. Do not modify unrelated files.
13. Do not silently bypass permissions.
14. Preserve project state.

## Project Definition

Supli supports a project-definition flow:

`Requirements → Capabilities → Behaviour → Roadmap → SKILL.md → README.md → Development`

A project may begin at any of these points. Important documents remain subject
to user review and approval.

## Roadmap

`Supli — Master Development Roadmap — Updated.md` is the authoritative
high-level development direction for Supli.

`SKILL.md` defines how Supli should behave while operating as an agent.

Supli must not create a competing roadmap.

## Technology Boundary

The roadmap is technology-aware but not technology-locked. FastAPI serves the application/API layer and SQLite holds project state because those milestones have begun. Tauri, React, Monaco, Docker, RAG, and GitPython remain options that have not been adopted.
