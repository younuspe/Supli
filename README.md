# Supli

Supli is a local development workspace and AI coding environment.

It is designed to help define, develop, test, review, and manage software projects while keeping the real project files, roadmap, documents, tools, permissions, and development state under controlled user direction.

## Current Architecture

The current working foundation is:

`Supli → Ollama → Qwen → Tools → Workspace`

The longer-term architecture defined by the Master Development Roadmap is:

`Supli UI → Application/API Layer → Supli Agent Engine → Tool Layer → Workspace/Project`

The existing agent foundation must remain reliable while the larger application is built around it.

## Current Foundation

The current workspace contains:

```text
~/Supli/
├── Agent/
│   ├── README.md
│   └── SKILL.md
├── roadmap.md
├── Supli.py
└── Supli — Master Development Roadmap — Updated.md

The actual workspace should always be inspected before making assumptions about files or structure.

## AI Model

Supli currently uses a local Ollama model:

`hf.co/saidutta69/Qwen2.5-Coder-7B-Instruct-heretic:Q4_K_M`

Ollama runs locally and Supli communicates with it through the local Ollama API.

The current setup is local-first. External AI providers are future capabilities defined by the roadmap and are not required for the current foundation.

## Current Agent Capabilities

The existing Supli agent currently supports:

- Local Ollama and Qwen
- SKILL.md loading
- Workspace restriction
- Directory inspection
- File reading
- File writing
- Command execution
- Real command-error inspection
- Review and retry
- Ask-when-stuck behaviour
- Exact-command handling
- Controlled command retries
- Safe stopping after defined retry limits
- Real verification of command results

The original terminal-agent Stage 8 has been verified with an end-to-end coding task.

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

A project may begin at any of these points.

Supli should identify missing information and propose the next useful document or step. Important documents must remain subject to user review and approval.

## Roadmap

`Supli — Master Development Roadmap — Updated.md` is the authoritative high-level development direction for Supli.

`roadmap.md` contains the existing agent-development roadmap and verified agent capability stages.

The Master Roadmap distinguishes between application/architecture milestones, agent capability stages, and requirement areas.

Supli must not create a competing roadmap.

## SKILL.md

`Agent/SKILL.md` defines how Supli should behave while operating as an agent.

It covers reality and inspection rules, context management, file operations, command execution, review and retry, asking when stuck, confirmation gates, project documents, project state, crash recovery, tools, permissions and safety, security, integrations, AI providers, platform tools, architecture, milestones, agent capability stages, UI direction, stage control, preview and UI designer, build/test/release, history and audit, continuity, completion, and technology boundaries.

The SKILL is behaviour guidance. It does not replace the roadmap.


## Planned Application Development

The Master Roadmap defines this development direction:

1. Preserve the existing agent foundation.
2. Prove the UI → Backend → Ollama → Qwen → UI vertical slice.
3. Build the workspace architecture.
4. Build the main UI shell.
5. Add the project explorer.
6. Connect chat to the agent engine.
7. Build the requirements/document system.
8. Add project state.
9. Add stage control.
10. Add the code editor.
11. Build the development agent panel.
12. Add diff and approval workflows.
13. Expand terminal and tools.
14. Add preview.
15. Add AI provider/model management.
16. Add Git and other integrations.
17. Add multiplatform tools.
18. Add security and permissions.
19. Add the UI designer.
20. Add advanced context management.
21. Build/test/release workflows.
22. Harden the application.

These are planned capabilities, not claims that they already exist.

## Main UI Direction

The planned permanent application shell contains:

- Project Explorer
- Code Editor
- Supli Chat

Additional views may include:

- Terminal
- Preview
- UI Designer
- Stage Progress
- Activity
- Changes/Diff
- Requirements
- Approvals
- Diagnostics

Views should eventually support docking, undocking, moving, resizing, splitting, tabs, closing, reopening, and reset.

## Development Agent Workflow

The intended workflow is:

`Understand → Inspect → Plan → Edit → Run → Review → Retry → Complete / Ask`

Plans must use real files discovered from the workspace.

Supli must never invent placeholder structures such as File A, File B, or imaginary folders when describing an implementation plan.

## File Editing

The intended controlled editing workflow is:

`Inspect → Understand → Propose → Review → Apply → Test → Review`

Larger changes should eventually provide a visible diff and approval step before application.


## Project State and Recovery

The planned system will preserve:

- current stage
- current task
- last action
- last successful action
- failures
- files changed
- tests performed
- pending approvals
- unresolved problems
- document versions
- stage history
- previous sessions

Persistent state and crash recovery are planned capabilities.

An interrupted action must never automatically be treated as completed.

## Tools

Current tools include:

- filesystem inspection
- file reading
- file writing
- terminal command execution

Future tool categories may include:

- browser/web
- APIs
- Git
- GitHub/GitLab
- documents
- media
- platform tools
- security tools

All tool access must remain controlled through permissions.

## Security and Permissions

Potential permission areas include:

- read
- write
- delete
- command execution
- network access
- Git
- GitHub
- external services
- system access
- platform access
- security operations

Dangerous capabilities must not silently become available.

## AI Providers and Models

The current foundation is:

`Ollama → Qwen → Supli`

The roadmap allows future support for additional providers and models.

The architecture must avoid making Supli permanently dependent on one provider.

## Integrations

Future integrations follow:

`Connect → Authenticate → User Approval → Permission Scope → Connected`

Supli must not silently grant unrestricted external access.


## Technology Boundary

The Master Roadmap is technology-aware but not technology-locked.

Tauri, React, FastAPI, WebSockets, Monaco, SQLite, RAG, Docker, GitPython, and similar technologies are options to evaluate at the appropriate milestones.

They are not all immediate requirements.

## Agent Capability Stages

The existing agent roadmap contains:

1. Stable Agent Foundation
2. Context Gathering
3. Planning
4. Safe File Editing
5. Command Execution
6. Review and Retry
7. Ask When Stuck
8. Complete Terminal Agent
9. Editor Integration
10. Inline Completions
11. Final Integration and Hardening

Stage 8 has been verified.

These agent capability stages are separate from the larger application's architecture milestones.

## Current Status

The existing terminal-agent foundation is working and has been tested.

The larger Supli application is still under development.

Features described as planned must not be represented as implemented until they have been built and verified.

## Working Rule

Supli should grow from the working foundation rather than replacing it wholesale.

The priority is:

`Reliable Agent → UI–AI Vertical Slice → Incremental Application Development → State / Safety / Approvals → Advanced Capabilities`

Supli must remain grounded in the real workspace, real files, real command results, real tests, and approved project direction.

