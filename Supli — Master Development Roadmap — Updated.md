# Supli — Master Development Roadmap

## 1. Purpose

Supli is a local development workspace and AI coding environment.

Its purpose is to provide a controlled workspace where the user can:

- define a project
- manage requirements
- create and manage a roadmap
- manage SKILL.md
- manage README.md
- develop through an AI agent
- inspect and edit files
- run development tools
- review changes
- control project stages
- test software
- manage integrations
- manage AI providers and models
- manage permissions and security
- preserve project state
- resume work after interruption

Supli must remain grounded in the real project.

It must not invent files, actions, results, project state, tests, or completed work.

---

# 2. Existing Foundation

The current working foundation is:

```text
~/Supli/
├── Agent/
│   ├── README.md
│   └── SKILL.md
├── roadmap.md
└── Supli.py
```

Current agent foundation:

```text
Supli
  ↓
Ollama
  ↓
Qwen
  ↓
Tools
  ↓
Workspace
```

Current working capabilities include:

- local Ollama connection
- Qwen model
- SKILL.md loading
- workspace restriction
- directory inspection
- file reading
- file writing
- command execution
- retry/review
- ask-when-stuck behaviour
- exact-command handling
- real error inspection
- terminal agent workflow

Stage 8 of the original agent roadmap has been verified with an end-to-end coding task.

The existing agent foundation must be preserved while the larger application is built around it.

---

# 3. Core Principle

Supli must always operate from reality.

Rules:

1. Read before changing.
2. Inspect before planning.
3. Use real filenames and paths.
4. Never invent project structure.
5. Never claim an action that did not happen.
6. Never claim a test passed unless it actually passed.
7. Make small, verifiable changes.
8. Review failures using real diagnostic information.
9. Retry only within a defined limit.
10. Ask the user when the agent cannot safely continue.
11. Do not automatically push or pull Git.
12. Do not modify unrelated files.
13. Do not silently bypass permissions.
14. Preserve project state.

---

# 4. Project Definition Pipeline

Supli should support this overall workflow:

```text
Requirements
      ↓
Capabilities
      ↓
Behaviour
      ↓
Roadmap
      ↓
SKILL.md
      ↓
README.md
      ↓
Development
```

However, the user may begin with any of these documents.

Possible starting points:

- Requirements
- Capabilities
- Behaviour
- Roadmap
- SKILL.md
- README.md

Supli analyses the supplied information and identifies what is missing.

It then proposes the next document.

It must not automatically approve or move to the next stage.

---

# 5. Confirmation Gates

Every important generated project document must have:

```text
Review
Edit
Approve
Reject
```

The user remains in control.

Examples:

```text
Requirements generated
        ↓
Review
        ↓
Approve
        ↓
Roadmap generated
        ↓
Review
        ↓
Approve
```

The same principle applies to:

- SKILL.md
- README.md
- major architecture decisions
- major code changes
- security requirements
- integrations
- release decisions

---

# 6. Requirements / Capabilities / Behaviour

This is an optional project-definition window.

It should not permanently occupy the main interface.

It may be opened through:

```text
Project → Requirements
Project → Capabilities
Project → Behaviour
```

or:

```text
View → Requirements
```

It should support:

- requirements
- capabilities
- behaviour
- target platforms
- security requirements
- uploaded `.md` documents

Actions:

```text
Save
Cancel
```

The window can close after the decision.

---

# 7. Roadmap Management

Supli must treat the roadmap as a living project document.

Capabilities:

- view roadmap
- edit roadmap
- generate roadmap
- revise roadmap
- compare roadmap versions
- approve changes
- track completed work
- track pending work
- record stage history

Important distinction:

The user's numbered requirement checklist is **not the development stages**.

The roadmap may contain development stages, while the requirements checklist defines areas that must not be forgotten.

---

# 8. SKILL.md Management

SKILL.md is the project's persistent agent specification.

Supli should:

- read SKILL.md
- display SKILL.md
- edit SKILL.md
- generate SKILL.md
- review changes
- approve changes
- preserve versions
- load the approved version for agent sessions

SKILL.md should remain separate from temporary conversational instructions.

---

# 9. README.md Management

README.md describes the project for humans.

Supli should support:

- creation
- editing
- generation
- review
- approval
- version history

README.md must reflect the actual project rather than imagined capabilities.

---

# 10. Workspace Architecture

The final application should separate:

```text
Supli UI
   ↓
Application / API Layer
   ↓
Supli Agent Engine
   ↓
Tool Layer
   ↓
Workspace / Project
```

The UI must not contain the core agent logic.

The agent engine must remain usable independently of the UI.

This allows:

- terminal use
- desktop UI
- future editor integration
- future mobile interfaces
- testing without the UI

The exact framework for the UI/backend is intentionally not locked at this stage.

---

# 11. Vertical Slice — Milestone 0

Before building the entire application, prove the complete basic path.

Target:

```text
Supli UI
   ↓
Backend connection
   ↓
Ollama
   ↓
Qwen
   ↓
Response
   ↓
UI
```

The first vertical slice should demonstrate:

- application starts
- chat appears
- user sends a message
- Supli receives it
- Qwen receives it
- response returns
- response appears in the UI

Only after this works should the larger UI system be expanded.

This is a validation milestone, not a replacement for the Master Roadmap.

---

# 12. Main UI Shell

The main interface should resemble a simple development environment.

Permanent areas:

```text
Project Explorer
Code Editor
Supli Chat
```

Example:

```text
┌─────────────────────────────────────────────────────────────┐
│ Supli  File  Edit  View  Project  Stage  AI  Tools  Help   │
├─────────────────────────────────────────────────────────────┤
│ New  Open  Save  Start  Stop  Resume  Model                │
├──────────────┬──────────────────────────┬───────────────────┤
│ PROJECT      │ CODE EDITOR              │ SUPLI CHAT        │
│              │                          │                   │
│ files        │                          │                   │
│ folders      │                          │                   │
│ roadmap      │                          │                   │
│ SKILL        │                          │                   │
│ README       │                          │                   │
├──────────────┴──────────────────────────┴───────────────────┤
│ Optional dockable area                                     │
└─────────────────────────────────────────────────────────────┘
```

---

# 13. Dockable View System

Optional areas should not permanently clutter the interface.

Possible views:

- Terminal
- Preview
- UI Designer
- Stage Progress
- Activity
- Changes / Diff
- Requirements
- Approvals
- Diagnostics

Views should support:

- dock
- undock
- move
- resize
- split
- tabs
- close
- reopen
- reset layout

---

# 14. Face / Identity

Supli should have a consistent identity.

The identity should be part of the UI but should not interfere with development.

The identity can appear in:

- application shell
- chat
- loading state
- agent status
- critical warnings

---

# 15. Chat

Supli Chat is a permanent main area.

It should support:

- normal conversation
- project questions
- development requests
- agent status
- tool activity
- errors
- approvals
- clarification requests
- final results

The chat must distinguish between:

```text
User request
AI reasoning/plan
Tool activity
Tool result
Approval request
Final result
```

---

# 16. Tools

Tools must be separate from the AI model.

The model requests a capability.

Supli decides whether that capability can actually be used.

Initial tools include:

- filesystem
- file reading
- file writing
- terminal
- testing

Future tools may include:

- browser
- web/API
- Git
- GitHub
- documents
- media
- platform tools
- security tools

Tool access must pass through permissions.

---

# 17. File Editing

File editing must be controlled.

Required principles:

```text
Inspect
   ↓
Understand
   ↓
Propose change
   ↓
Review
   ↓
Apply
   ↓
Test
   ↓
Review result
```

For larger changes, Supli should provide a diff before approval.

Direct uncontrolled overwriting should not be the final interaction model.

---

# 18. Code Editor

The code editor should support:

- multiple files
- tabs
- syntax highlighting
- search
- find/replace
- manual editing
- AI editing
- diff review
- accept/reject
- multiple programming languages

Inline completion is a later capability.

The editor technology is not locked yet.

---

# 19. Development Agent Panel

The development agent should provide a visible workflow:

```text
Understand
   ↓
Inspect
   ↓
Plan
   ↓
Edit
   ↓
Run
   ↓
Review
   ↓
Retry
   ↓
Complete / Ask
```

Planning must use real project files.

Every implementation step should identify the real files it intends to inspect or change.

Supli must never invent:

- File A
- File B
- imaginary folders
- imaginary project structure

---

# 20. Project Stage Control

Stage control belongs to the project workflow.

Controls:

- Current Stage
- Start
- Stop
- Pause
- Resume
- Restart Stage
- Select Stage
- Revision
- Review
- Approve
- Stage History

Stopping a project must not erase its state.

---

# 21. Project State and Persistent Memory

Supli must remember project state.

State should eventually include:

- current stage
- current task
- last action
- last successful action
- last failed action
- files changed
- tests performed
- pending approvals
- unresolved problems
- previous sessions
- document versions
- stage history

For the full application, use a local persistent state store.

**SQLite is the preferred direction**, because project state will eventually contain relationships between:

- projects
- stages
- tasks
- actions
- files
- approvals
- tests
- history
- sessions

The exact schema should be designed before implementation.

---

# 22. Crash Recovery

Crash recovery is a required capability.

If Supli closes during a project operation, reopening Supli must reconstruct the last known state from persistent project state.

It must identify:

- last completed action
- current stage
- incomplete action
- pending approval
- last known test result
- files changed before interruption

It must not pretend an interrupted action completed.

The user must be able to:

```text
Resume
Restart Stage
Select Stage
Review State
```

---

# 23. Terminal / Command Environment

Terminal execution is a controlled tool.

The final application should support:

- terminal output
- command history
- running tests
- builds
- diagnostics
- stopping commands
- command status
- timeout handling

Commands must remain subject to permissions.

The current workspace restriction remains a foundational security rule.

---

# 24. Preview

Preview should be an optional view.

Possible targets:

- Web
- Desktop
- Tablet
- Mobile
- Android

The preview system should detect what the project actually supports.

It must not claim that a platform can be previewed when the required tools are unavailable.

---

# 25. UI Designer

The UI Designer is a later capability.

Possible features:

- visual components
- layout
- properties
- responsive views
- Web
- Tablet
- Mobile
- Desktop
- Android

Example layouts:

```text
Code + Terminal
Code + Preview
Code + Android Preview
UI Designer + Preview
Editor + Terminal + Chat
```

---

# 26. Integrations

Supli should eventually support controlled integrations with:

- Git
- GitHub
- GitLab
- AI providers
- other authorized applications/services

Every integration requires:

```text
Connect
   ↓
Authenticate
   ↓
User approval
   ↓
Permission scope
   ↓
Connected
```

No integration should silently gain unrestricted access.

Git push/pull remain explicitly controlled.

---

# 27. AI Provider and Model Management

Current foundation:

```text
Ollama
   ↓
Qwen
   ↓
Supli
```

Future provider support may include:

- Ollama
- OpenAI
- Google
- OpenRouter
- other local/custom providers

The system should provide:

- provider status
- connection status
- model selection
- project-specific model selection
- AI settings
- failure diagnostics

The architecture should not assume one provider forever.

---

# 28. Context Management

Supli must not send an entire project to the model on every request.

Context gathering should become a dedicated capability.

Workflow:

```text
User request
   ↓
Understand required context
   ↓
Inspect project
   ↓
Identify relevant files
   ↓
Read relevant content
   ↓
Build model context
```

Small local models should receive only the context required for the current task.

Semantic retrieval / RAG may be introduced later if normal project retrieval becomes insufficient.

RAG is therefore a **future optimization**, not a foundation requirement.

---

# 29. Multiplatform Tools

Supli should eventually detect available development tools for:

- Web
- Tablet
- Mobile
- Android
- macOS
- Windows
- Linux
- Server
- other targets

Possible tools include:

- SDKs
- compilers
- package managers
- browsers
- emulators
- connected devices
- build tools
- testing tools
- security tools

Supli must detect actual availability instead of assuming a platform tool exists.

---

# 30. Security and Protection

Security is a selectable project requirement.

Possible requirements:

- authentication
- authorization
- secrets protection
- dependency security
- input validation
- file/path protection
- network protection
- permission review
- secure configuration
- privacy/data protection
- security testing
- platform security
- release security

Security checks should become part of project readiness.

---

# 31. Sandboxing

Terminal and development execution must eventually have stronger isolation than the current basic workspace restriction.

Possible isolation technologies may include:

- restricted local execution
- virtual environments
- containers
- platform sandboxing
- other controlled execution environments

The specific technology must be selected based on the target platform and actual security requirements.

Docker is therefore a **possible implementation**, not a mandatory architectural dependency.

---

# 32. Permissions and Safety

Supli should have explicit permission categories.

Examples:

```text
Read file
Write file
Delete file
Run command
Network access
Git
GitHub
External service
System access
Platform tool
Security tool
```

Permissions should be:

- visible
- reviewable
- project-specific where appropriate
- revocable
- logged

Dangerous capabilities must not silently become available.

---

# 33. Pending Approvals

Because Supli uses confirmation gates, the UI needs a clear approval system.

Possible pending approvals:

- generated roadmap
- SKILL.md
- README.md
- code changes
- file deletion
- security changes
- integrations
- permissions
- release actions

The UI should provide a visible:

```text
Pending Approvals
```

area or badge.

---

# 34. Command Palette

Add a command palette similar to development environments.

It should allow quick access to:

- files
- views
- stages
- commands
- project actions
- AI actions
- tools
- settings

This should be implemented as part of the UI shell rather than the current terminal foundation.

---

# 35. Changes / Diff

Changes must be visible and reversible.

The final UI should support:

```text
Before
   ↓
Proposed Change
   ↓
Diff
   ↓
Approve / Reject
   ↓
Apply
   ↓
Test
```

The exact diff technology is not locked yet.

---

# 36. History / Changes / Audit

Supli should maintain a project activity record.

Track:

- user requests
- agent actions
- tool calls
- files changed
- commands executed
- test results
- approvals
- rejected actions
- errors
- retries
- stage transitions
- integrations
- permission decisions

This provides both history and auditability.

---

# 37. Build / Test / Release

Supli should eventually manage:

```text
Development
   ↓
Build
   ↓
Test
   ↓
Security Review
   ↓
Release Review
   ↓
Release
```

Build/test/release capabilities depend on the actual project and available platform tools.

Supli must verify results rather than assuming success.

---

# 38. Settings / Configuration

Settings should eventually include:

- AI provider
- model
- workspace
- permissions
- security
- integrations
- appearance
- editor
- terminal
- preview
- notifications
- project settings

Global settings and project settings should remain distinguishable.

---

# 39. Architecture Evolution

The architecture should evolve incrementally.

Initial:

```text
Supli.py
   ↓
Ollama
   ↓
Qwen
   ↓
Tools
```

Then:

```text
Supli UI
   ↓
Application/API Layer
   ↓
Supli Engine
   ↓
Tools
   ↓
Workspace
```

Later:

```text
                    ┌── AI Providers
                    │
UI → Application → Agent Engine → Tool Layer
                         │             │
                         │             ├── Files
                         │             ├── Terminal
                         │             ├── Git
                         │             ├── Browser
                         │             └── Platform Tools
                         │
                         └── Project State
                               ↓
                             SQLite
```

The exact frameworks and communication technologies should be selected when their implementation milestone begins.

---

# 40. Development Strategy

Do not build the whole application at once.

Use vertical slices.

## Milestone 0

Prove:

```text
UI → Backend → Ollama → Qwen → UI
```

## Milestone 1

Add:

```text
Project Explorer
+
Workspace access
+
Basic Editor
```

## Milestone 2

Connect the existing agent:

```text
Chat
 ↓
Supli Engine
 ↓
Tools
 ↓
Files
```

## Milestone 3

Add:

```text
Planning
+
File-specific edits
+
Diff
+
Review
```

## Milestone 4

Add:

```text
Project State
+
SQLite
+
Stage State
+
History
+
Crash Recovery
```

## Milestone 5

Add:

```text
Approvals
+
Permissions
+
Security
```

## Milestone 6

Add:

```text
Terminal
+
Preview
+
Development Tools
```

## Milestone 7

Add:

```text
AI Provider / Model Manager
+
Integrations
```

## Milestone 8

Add:

```text
Multiplatform Tools
+
UI Designer
```

## Milestone 9

Add:

```text
Advanced Context Management
+
Optional Semantic Retrieval / RAG
```

## Milestone 10

Hardening:

```text
Security
+
Testing
+
Crash Recovery
+
Audit
+
Performance
+
Release
```

---

# 41. Existing Agent Development Stages

The original agent stages remain important:

```text
Stage 1 — Stable Agent Foundation
Stage 2 — Context Gathering
Stage 3 — Planning
Stage 4 — Safe File Editing
Stage 5 — Command Execution
Stage 6 — Review and Retry
Stage 7 — Ask When Stuck
Stage 8 — Complete Terminal Agent
Stage 9 — Editor Integration
Stage 10 — Inline Completions
Stage 11 — Final Integration and Hardening
```

These are **agent capability stages**.

They are not the same thing as the application's UI/architecture milestones.

Stage 8 has already been verified.

---

# 42. 24 Requirement Areas

The following requirement checklist remains unchanged:

1. Workspace / Main Application
2. Face / Identity
3. Chat Area
4. Tools
5. File Editing
6. Code Editor
7. Development Agent Panel
8. Stage Control
9. Integrations
10. Multiplatform Tools
11. Requirements / Capabilities / Behaviour
12. Roadmap Management
13. SKILL.md Management
14. README.md Management
15. Project State / Memory
16. Preview / UI Designer
17. Terminal / Command Environment
18. Security & Protection
19. AI Provider & Model Management
20. Permissions & Safety
21. Project Settings
22. History / Changes / Audit
23. Build / Test / Release
24. Settings / Configuration

These numbers are a **requirements checklist**, not development stages.

---

# 43. Implementation Direction

The application should evolve approximately in this direction:

```text
Existing Supli Agent Foundation
              ↓
Vertical Slice
              ↓
Workspace Architecture
              ↓
Main UI Shell
              ↓
Project Explorer
              ↓
Chat Connection
              ↓
Requirements / Document System
              ↓
Project State
              ↓
Stage Control
              ↓
Code Editor
              ↓
Development Agent Panel
              ↓
Diff / Approval System
              ↓
Terminal / Tools
              ↓
Preview
              ↓
AI Provider / Model Manager
              ↓
Git / Integrations
              ↓
Multiplatform Tools
              ↓
Security / Permissions
              ↓
UI Designer
              ↓
Advanced Context Management
              ↓
Build / Test / Release
              ↓
Hardening
```

This is an **implementation direction**, not another numbered requirement list.

---

# 44. Definition of Done

Supli is not considered complete merely because the UI exists.

The finished system must be able to:

1. Understand a real project.
2. Inspect real files.
3. Maintain project requirements.
4. Maintain a roadmap.
5. Maintain SKILL.md.
6. Maintain README.md.
7. Respect confirmation gates.
8. Plan using real files.
9. Edit files safely.
10. Show proposed changes.
11. Run commands safely.
12. Review real results.
13. Retry within limits.
14. Ask when stuck.
15. Preserve project state.
16. Recover after a crash.
17. Track history and changes.
18. Manage permissions.
19. Perform required security checks.
20. Manage AI providers/models.
21. Support integrations with explicit authorization.
22. Detect available platform tools.
23. Build and test real projects.
24. Never invent actions or results.
25. Never silently perform dangerous external actions.

---

# 45. Important Boundary

The roadmap is intentionally **technology-aware but not technology-locked**.

The recommendations for:

- Tauri
- React
- FastAPI
- WebSockets
- Monaco
- SQLite
- RAG
- Docker
- GitPython

are not all immediate implementation requirements.

They are architectural options to evaluate at the appropriate milestone.

The priority remains:

```text
Make the existing Supli agent reliable
        ↓
Prove the UI-to-AI vertical slice
        ↓
Build the application incrementally
        ↓
Add state, safety and approvals
        ↓
Add advanced development capabilities
```

Supli should grow from the working foundation rather than being replaced by a completely new system.