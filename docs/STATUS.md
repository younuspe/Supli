# Supli — Implementation Status

This file records what is actually built and verified. It exists to keep the
README honest: features are only listed here when there is code and a test or a
real run behind them.

Last verified: 2026-09-19, `python -m pytest tests -q` → **44 passed**.

The environment used for verification had **no Ollama instance**, so the
provider round-trip was verified with the scripted provider. The Ollama adapter
is implemented and its failure path is tested, but a live Qwen round-trip has
**not** been verified here. See "Unverified" below.

---

## Milestone 0 — Vertical Slice

`UI → Backend → Provider → UI`

**Implemented and verified.** The browser UI sends a message, the API layer
forwards it, the provider answers, and the response is rendered and persisted.
Verified by driving the running app in a browser and by inspecting the stored
messages.

Remaining to fully close: verify against a live Ollama/Qwen instance.

## Milestone 1 — Project Explorer + Workspace + Basic Editor

**Implemented and verified.** Explorer lists real workspace files; opening a file
loads it into the editor; saving writes it and reports the real diff.

## Milestone 2 — Chat + Engine + Tools + Files

**Implemented and verified.** Chat distinguishes user, plan, tool activity, tool
result, approval request, result, error, and clarification. Tools execute
through the permission gate. Context gathering sends only relevant files.

## Milestone 3 — Planning + File Edits + Diff + Review

**Implemented and verified.** Plans are built from real filenames discovered in
the workspace (a test asserts every file named in a plan exists on disk). Edits
are proposed as unified diffs and require approval. Rejection leaves the file
byte-identical (tested). Approval was also exercised against the running server.

## Milestone 4 — Project State + SQLite + Stages + History + Recovery

**Implemented and verified.** All state is in SQLite. Actions are recorded as
`pending` before they run; recovery marks leftover `pending` rows as
`interrupted` and never reports them as complete (tested).

## Milestone 5 — Approvals + Permissions + Security

**Implemented and verified.** Eleven permission categories with conservative
defaults. Read/write/command allowed; delete/network/git/security ask; GitHub,
external service, system access, platform tools denied. Workspace confinement
rejects `..` escapes, absolute outside paths, and symlink escapes (all tested).
Git push/pull/fetch are refused regardless of permission (tested).

## Milestone 6 — Terminal + Preview + Development Tools

**Implemented and verified (partial).** A terminal dock runs real commands with
timeouts and output capture. A Platform Tools view detects what is actually
installed. **Preview is not implemented.**

## Milestone 7 — AI Provider / Model Manager + Integrations

**Implemented and verified (partial).** Provider abstraction with Ollama and
Scripted providers, runtime activation, model listing, and status reporting.
Git integration is read-only inspection. **GitHub/GitLab integrations are not
implemented.**

## Milestone 8 — Multiplatform Tools + UI Designer

**Implemented and verified (partial).** Platform tool detection covers Python,
Node, Docker, Git, compilers, and mobile SDKs, reporting absence as absence.
**The UI Designer is not implemented.**

## Milestone 9 — Advanced Context Management + Retrieval

**Implemented and verified (partial).** Bounded lexical context gathering with
explicit-path preference. **Semantic retrieval / RAG is deliberately not
implemented**; the roadmap marks it as optional and later.

## Milestone 10 — Security + Testing + Recovery + Audit + Performance + Release

**Implemented and verified (partial).** 44 tests covering confinement,
permissions, git safety, diffs, approvals, recovery, engine retry limits,
context bounds, stages, audit, and the API. **Performance profiling and
packaging/release are not implemented.**

---

## Unverified

- **Live Ollama/Qwen round-trip.** The adapter is written and its error path is
  tested, but no Ollama instance was reachable during verification.
- **Ollama model listing/selection against a real server.**

## Not implemented

- Preview (Milestone 6)
- UI Designer (Milestone 8)
- Semantic retrieval / RAG (Milestone 9)
- GitHub/GitLab integrations (Milestone 7)
- Document version history beyond current-version metadata; historical bodies
  are not retained
- Dock drag/resize/split; views can be opened, closed, and reopened, but not
  rearranged
- Performance profiling and release workflow (Milestone 10)

---

## Running

```bash
pip install -r requirements.txt
python supli.py                 # http://127.0.0.1:8000
python -m pytest tests -q       # 44 tests
```

Environment variables: `SUPLI_DB` (SQLite path), `SUPLI_OLLAMA_URL`,
`SUPLI_OLLAMA_MODEL`.

## Known design decisions

- Provider selection is automatic: Ollama is activated when reachable,
  otherwise the scripted provider is used so the app still runs.
- `roadmap.md`, `SKILL.md`, and `README.md` are treated as *project documents*
  and their modification requires approval, per SKILL §11.
- The workspace restriction is enforced with `realpath`, so symlinks cannot be
  used to escape.