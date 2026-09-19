# Supli — Development Roadmap

This is the working development roadmap for the Supli application code.
`Supli — Master Development Roadmap — Updated.md` remains the authoritative
high-level direction; this file tracks the application milestones against the
code in this repository and must not contradict the Master Roadmap.

Application milestones are distinct from agent capability stages
(see `SKILL.md` §23).

## Status Legend

- **done** — implemented and verified by a test or a real run
- **partial** — the core exists; the named sub-capability does not
- **todo** — not started

Verification detail lives in `docs/STATUS.md`.

---

## Milestone 0 — Vertical Slice — done

`UI → Backend → Provider → UI`

Proven with the running application: a message typed in the browser reaches the
API layer, is answered by the provider, and is rendered and persisted.

Remaining to fully close: verify against a live Ollama/Qwen instance.

## Milestone 1 — Project Explorer + Workspace + Basic Editor — done

Explorer, confined workspace access, file open/edit/save with real diffs.

## Milestone 2 — Chat + Engine + Tools + Files — done

Chat roles distinguished; tools behind the permission gate; bounded context.

## Milestone 3 — Planning + File Edits + Diff + Review — done

Plans use real files only; edits require approval; rejection is a no-op.

## Milestone 4 — Project State + SQLite + Stages + History + Recovery — done

Persistent state, milestone tracking, audit trail, interrupted-action recovery.

Outstanding: retain historical document bodies, not just the current version.

## Milestone 5 — Approvals + Permissions + Security — done

Eleven permission categories, approval gate, workspace confinement.

Outstanding: sandboxed execution beyond the workspace restriction.

## Milestone 6 — Terminal + Preview + Development Tools — partial

Terminal and platform tool detection are implemented and verified.
**Preview is not implemented.**

## Milestone 7 — Provider / Model Manager + Integrations — partial

Provider abstraction, activation, model listing, and status are implemented.
Read-only git inspection is implemented.
**GitHub/GitLab integrations are not implemented.**

## Milestone 8 — Multiplatform Tools + UI Designer — partial

Platform tool detection is implemented.
**The UI Designer is not implemented.**

## Milestone 9 — Advanced Context Management + Retrieval — partial

Bounded lexical context with explicit-path preference is implemented.
**Semantic retrieval / RAG is not implemented** and remains optional.

## Milestone 10 — Security + Testing + Recovery + Audit + Performance + Release — partial

44 tests, audit trail, and recovery are implemented.
**Performance profiling and release packaging are not implemented.**

---

## Immediate Next Work

1. Verify Milestone 0 against a live Ollama instance.
2. Retain historical document versions in state.
3. Implement Preview (Milestone 6).
4. Add GitHub/GitLab integrations with explicit authorization (Milestone 7).
5. Implement the UI Designer (Milestone 8).

## Boundary

Do not build the whole application at once. Prefer vertical slices, and do not
mark an item complete without evidence from the real project.