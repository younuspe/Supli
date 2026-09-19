/* Supli UI shell.
   The UI holds no agent logic: it renders state and calls the API layer. */

const $ = (sel) => document.querySelector(sel);
const el = (tag, cls, text) => {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined) node.textContent = text;
  return node;
};

const state = {
  projectId: null,
  project: null,
  currentFile: null,
  editorDirty: false,
  sessionId: null,
  approvals: [],
  panes: { explorer: true, editor: true, chat: true },
  docks: {
    terminal: { title: "Terminal", render: renderTerminal },
    activity: { title: "Activity", render: renderActivity },
    changes: { title: "Changes / Diff", render: renderChanges },
    requirements: { title: "Requirements", render: renderRequirements },
    approvals: { title: "Approvals", render: renderApprovals },
    diagnostics: { title: "Diagnostics", render: renderDiagnostics },
    stages: { title: "Stage Progress", render: renderStages },
    tools: { title: "Platform Tools", render: renderPlatformTools },
  },
  activeDock: "activity",
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const text = await response.text();
  let body;
  try { body = text ? JSON.parse(text) : null; } catch { body = { detail: text }; }
  if (!response.ok) {
    const detail = body && body.detail ? JSON.stringify(body.detail) : response.statusText;
    throw new Error(detail);
  }
  return body;
}

function setStatus(message, isError = false) {
  $("#status-text").textContent = message;
  $("#status-text").style.color = isError ? "var(--err)" : "";
}

/* ---------------- projects ---------------- */

async function loadProjects() {
  const projects = await api("/api/projects");
  const select = $("#project-select");
  select.innerHTML = "";
  if (projects.length === 0) {
    const opt = el("option", null, "No projects");
    opt.value = "";
    select.appendChild(opt);
    return;
  }
  for (const p of projects) {
    const opt = el("option", null, p.name);
    opt.value = p.id;
    select.appendChild(opt);
  }
  const stored = localStorage.getItem("supli.project");
  const chosen = projects.find((p) => p.id === stored) || projects[0];
  select.value = chosen.id;
  await openProject(chosen.id);
}

async function openProject(projectId) {
  state.projectId = projectId;
  state.currentFile = null;
  state.sessionId = null;
  localStorage.setItem("supli.project", projectId);
  state.project = await api(`/api/projects/${projectId}`);
  $("#editor").value = "";
  $("#editor-title").textContent = "CODE EDITOR";
  $("#chat-log").innerHTML = "";
  setStatus(`Opened project ${state.project.name}`);
  await Promise.all([refreshTree(), refreshBadges()]);
  refreshDock();
}

async function refreshBadges() {
  const providers = await api("/api/providers");
  const active = providers.providers.find((p) => p.provider === providers.active);
  $("#provider-badge").textContent = `provider: ${providers.active}${active && !active.available ? " (unavailable)" : ""}`;
  const stages = await api(`/api/projects/${state.projectId}/stages`);
  const current = stages.current;
  $("#stage-badge").textContent = `stage: ${current ? current.key : "none"}`;
  const approvals = await api(`/api/projects/${state.projectId}/approvals?state=pending`);
  state.approvals = approvals;
  const badge = $("#approval-badge");
  badge.textContent = `approvals: ${approvals.length}`;
  badge.classList.toggle("hidden", approvals.length === 0);
  badge.classList.toggle("warn", approvals.length > 0);
}

/* ---------------- explorer ---------------- */

async function refreshTree() {
  const entries = await api(`/api/projects/${state.projectId}/tree`);
  const tree = $("#file-tree");
  tree.innerHTML = "";
  if (entries.length === 0) {
    tree.appendChild(el("li", "dir", "(empty workspace)"));
    return;
  }
  for (const entry of entries) {
    const li = el("li", entry.is_dir ? "dir" : "file");
    const label = entry.is_dir ? "▸ " : "  ";
    li.textContent = label + entry.name;
    if (!entry.is_dir) {
      if (["roadmap.md", "SKILL.md", "README.md"].includes(entry.name)) {
        const span = el("span", "doc");
        li.textContent = label;
        span.textContent = entry.name;
        li.appendChild(span);
      }
      li.onclick = () => openFile(entry.path);
    }
    tree.appendChild(li);
  }
}

async function openFile(path) {
  const file = await api(`/api/projects/${state.projectId}/file?path=${encodeURIComponent(path)}`);
  state.currentFile = path;
  $("#editor").value = file.content;
  $("#editor-title").textContent = `CODE EDITOR — ${path}`;
  setStatus(`Opened ${path} (${file.content.length} chars)`);
}

/* ---------------- chat ---------------- */

function addMessage(kind, body, meta) {
  const node = el("div", `msg ${kind}`);
  node.appendChild(el("div", "kind", kind.replace(/_/g, " ")));
  node.appendChild(el("div", "body", body));
  if (meta && meta.tool) {
    node.appendChild(el("div", "kind", `tool: ${meta.tool}`));
  }
  const log = $("#chat-log");
  log.appendChild(node);
  log.scrollTop = log.scrollHeight;
  return node;
}

async function sendChat(message) {
  if (!message.trim()) return;
  addMessage("user", message);
  setStatus("Supli is working…");
  try {
    const response = await api(`/api/projects/${state.projectId}/chat`, {
      method: "POST",
      body: JSON.stringify({ message, session_id: state.sessionId }),
    });
    state.sessionId = response.session_id;
    renderSession(response.messages);
    const result = response.result;
    if (result && result.status === "needs_approval") {
      await refreshBadges();
      openDock("approvals");
      setStatus("Approval required.", true);
    } else if (result && result.status === "needs_input") {
      setStatus("Supli needs your input.", true);
    } else if (response.error) {
      setStatus(response.error, true);
    } else {
      setStatus("Done.");
    }
    await refreshBadges();
  } catch (error) {
    addMessage("error", String(error.message || error));
    setStatus(String(error.message || error), true);
  }
}

function renderSession(messages) {
  const log = $("#chat-log");
  log.innerHTML = "";
  for (const m of messages) {
    addMessage(m.kind, m.content, m.meta);
  }
}

/* ---------------- dock ----------------

   Views are removable/reopenable: closing removes the tab, and the View menu
   plus the command palette can bring it back. */

function openDock(name) {
  state.activeDock = name;
  refreshDock();
}

function closeDock(name) {
  delete state.docks[name];
  if (state.activeDock === name) {
    state.activeDock = Object.keys(state.docks)[0] || null;
  }
  refreshDock();
}

function availableViews() {
  const all = {
    terminal: { title: "Terminal", render: renderTerminal },
    activity: { title: "Activity", render: renderActivity },
    changes: { title: "Changes / Diff", render: renderChanges },
    requirements: { title: "Requirements", render: renderRequirements },
    approvals: { title: "Approvals", render: renderApprovals },
    diagnostics: { title: "Diagnostics", render: renderDiagnostics },
    stages: { title: "Stage Progress", render: renderStages },
    tools: { title: "Platform Tools", render: renderPlatformTools },
  };
  return all;
}

function refreshDock() {
  const tabs = $("#dock-tabs");
  tabs.innerHTML = "";
  const names = Object.keys(state.docks);
  for (const name of names) {
    const button = el("button", name === state.activeDock ? "active" : null, state.docks[name].title);
    button.onclick = () => openDock(name);
    tabs.appendChild(button);
  }
  tabs.appendChild(el("span", "spacer"));
  const closeButton = el("button", null, "× close view");
  closeButton.onclick = () => state.activeDock && closeDock(state.activeDock);
  if (state.activeDock) tabs.appendChild(closeButton);

  const body = $("#dock-body");
  body.innerHTML = "";
  if (state.activeDock && state.docks[state.activeDock]) {
    state.docks[state.activeDock].render(body);
  } else {
    body.appendChild(el("div", null, "No views open. Use View or Ctrl+K to open one."));
  }
}

async function renderTerminal(body) {
  const form = el("div", "field");
  const input = el("input");
  input.placeholder = "command to run in the workspace root";
  const out = el("pre", null, "");
  const run = el("button", "primary", "Run");
  run.style.marginTop = "6px";
  run.onclick = async () => {
    out.textContent = "running…";
    try {
      const result = await api(`/api/projects/${state.projectId}/command`, {
        method: "POST",
        body: JSON.stringify({ command: input.value, timeout: 60 }),
      });
      if (result.needs_approval) {
        out.textContent = `permission required (approval ${result.needs_approval}). Approve it in Approvals, then retry.`;
      } else {
        const o = result.output || {};
        out.textContent = `$ ${input.value}\nexit=${o.returncode}\n${o.stdout || ""}${o.stderr || ""}`;
      }
    } catch (error) {
      out.textContent = String(error.message || error);
    }
    await refreshBadges();
  };
  body.appendChild(input);
  body.appendChild(run);
  body.appendChild(out);
}

async function renderActivity(body) {
  try {
    const history = await api(`/api/projects/${state.projectId}/history?limit=60`);
    if (!history.actions.length) {
      body.appendChild(el("div", null, "No activity recorded yet."));
      return;
    }
    for (const action of history.actions) {
      const row = el("div", "tool-activity");
      const pill = el("span", `pill ${action.state === "success" ? "ok" : "fail"}`, action.state);
      row.appendChild(pill);
      row.appendChild(el("span", null, ` ${action.kind}:${action.name}`));
      if (action.error) row.appendChild(el("span", null, ` — ${action.error}`));
      body.appendChild(row);
    }
  } catch (error) {
    body.appendChild(el("div", null, String(error.message || error)));
  }
}

async function renderChanges(body) {
  const approvals = await api(`/api/projects/${state.projectId}/approvals`);
  const withDiff = approvals.filter((a) => a.payload && a.payload.diff);
  if (!withDiff.length) {
    body.appendChild(el("div", null, "No proposed changes yet."));
    return;
  }
  for (const approval of withDiff) {
    body.appendChild(el("div", null, `${approval.kind} — ${approval.summary} [${approval.state}]`));
    body.appendChild(renderDiff(approval.payload.diff));
  }
}

function renderDiff(diff) {
  const pre = el("pre", "diff");
  for (const line of diff.split("\n")) {
    const span = el("div",
      line.startsWith("+") && !line.startsWith("+++") ? "add"
        : line.startsWith("-") && !line.startsWith("---") ? "del"
        : line.startsWith("@@") ? "hunk" : null);
    span.textContent = line;
    pre.appendChild(span);
  }
  return pre;
}

async function renderApprovals(body) {
  const approvals = await api(`/api/projects/${state.projectId}/approvals?state=pending`);
  if (!approvals.length) {
    body.appendChild(el("div", null, "No pending approvals."));
    return;
  }
  for (const approval of approvals) {
    const card = el("div", "tool-activity");
    card.appendChild(el("div", null, `${approval.kind}: ${approval.summary}`));
    if (approval.payload && approval.payload.diff) {
      card.appendChild(renderDiff(approval.payload.diff));
    }
    const approve = el("button", "primary", "Approve");
    const reject = el("button", "danger", "Reject");
    approve.onclick = () => decide(approval.id, true);
    reject.onclick = () => decide(approval.id, false);
    card.appendChild(approve);
    card.appendChild(reject);
    body.appendChild(card);
  }
}

async function decide(approvalId, approved) {
  try {
    const result = await api(
      `/api/projects/${state.projectId}/approvals/${approvalId}/decide`,
      { method: "POST", body: JSON.stringify({ approved, note: "" }) },
    );
    setStatus(approved ? "Approved and applied." : "Rejected.");
    if (approved && result.applied && result.applied.verified === false) {
      setStatus("Approved, but the file did not match the proposed content.", true);
    }
    await refreshBadges();
    refreshDock();
    await refreshTree();
  } catch (error) {
    setStatus(String(error.message || error), true);
  }
}

async function renderRequirements(body) {
  const documents = await api(`/api/projects/${state.projectId}/documents`);
  if (!documents.length) {
    body.appendChild(el("div", null, "No project documents stored."));
    const seed = el("button", "primary", "Load roadmap.md / SKILL.md / README.md");
    seed.onclick = async () => {
      await api(`/api/projects/${state.projectId}/documents/seed`, { method: "POST" });
      refreshDock();
    };
    body.appendChild(seed);
    return;
  }
  for (const doc of documents) {
    body.appendChild(el("div", null, `${doc.name} — version ${doc.version} (${doc.content.length} chars)`));
  }
}

async function renderDiagnostics(body) {
  const health = await api("/api/health");
  const lines = [
    `workspace: ${state.project ? state.project.workspace : "—"}`,
    `active provider: ${health.providers.active}`,
    ...health.providers.providers.map(
      (p) => `  ${p.provider}: available=${p.available} local=${p.local}` +
        (p.error ? ` error=${p.error}` : ""),
    ),
    `current stage: ${$("#stage-badge").textContent}`,
  ];
  body.appendChild(el("pre", null, lines.join("\n")));
}

async function renderStages(body) {
  const data = await api(`/api/projects/${state.projectId}/stages`);
  for (const stage of data.stages) {
    const row = el("div", "tool-activity");
    row.appendChild(el("span", `pill ${stage.state === "complete" ? "ok" : ""}`, stage.state));
    row.appendChild(el("span", null, ` ${stage.key} — ${stage.title}`));
    const start = el("button", null, "Start");
    start.onclick = async () => {
      await api(`/api/projects/${state.projectId}/stages`, {
        method: "POST", body: JSON.stringify({ key: stage.key, state: "in_progress" }),
      });
      await refreshBadges(); refreshDock();
    };
    const done = el("button", null, "Complete");
    done.onclick = async () => {
      await api(`/api/projects/${state.projectId}/stages`, {
        method: "POST", body: JSON.stringify({ key: stage.key, state: "complete" }),
      });
      await refreshBadges(); refreshDock();
    };
    row.appendChild(start); row.appendChild(done);
    body.appendChild(row);
  }
}

async function renderPlatformTools(body) {
  const result = await api(`/api/projects/${state.projectId}/tools`);
  if (result.needs_approval) {
    body.appendChild(el("div", null,
      `Platform tool detection requires permission (approval ${result.needs_approval}).`));
    return;
  }
  if (!result.ok) { body.appendChild(el("div", null, result.error)); return; }
  const entries = Object.entries(result.output || {});
  const pre = el("pre");
  pre.textContent = entries.map(([k, v]) => `${k.padEnd(10)} ${v || "not found"}`).join("\n");
  body.appendChild(pre);
}

/* ---------------- command palette (M6) ---------------- */

function paletteCommands() {
  const commands = [
    { label: "New Project", run: newProject },
    { label: "Refresh tree", run: refreshTree },
    { label: "Seed project documents", run: async () => {
        await api(`/api/projects/${state.projectId}/documents/seed`, { method: "POST" });
        setStatus("Documents seeded."); } },
    { label: "Inspect workspace", run: inspectWorkspace },
    { label: "Build plan", run: buildPlan },
    { label: "Propose edit for current file", run: proposeEdit },
    { label: "Run crash recovery", run: recover },
    { label: "Refresh provider status", run: refreshProviders },
  ];
  for (const [name, view] of Object.entries(availableViews())) {
    commands.push({ label: `View: ${view.title}`, run: () => {
      state.docks[name] = view; openDock(name); } });
  }
  for (const name of Object.keys(state.panes)) {
    commands.push({ label: `Toggle pane: ${name}`, run: () => togglePane(name) });
  }
  return commands;
}

function openPalette() {
  const palette = $("#palette");
  palette.classList.remove("hidden");
  const input = $("#palette-input");
  input.value = "";
  renderPaletteCommands("");
  input.focus();
}

function renderPaletteCommands(query) {
  const list = $("#palette-list");
  list.innerHTML = "";
  const matches = paletteCommands().filter(
    (c) => c.label.toLowerCase().includes(query.toLowerCase()),
  );
  matches.forEach((command, index) => {
    const li = el("li", index === 0 ? "active" : null, command.label);
    li.onclick = () => { $("#palette").classList.add("hidden"); command.run(); };
    list.appendChild(li);
  });
}

/* ---------------- panes ---------------- */

function togglePane(name) {
  state.panes[name] = !state.panes[name];
  const node = document.querySelector(`.pane-${name}`);
  node.style.display = state.panes[name] ? "" : "none";
}

/* ---------------- actions ---------------- */

async function newProject() {
  const name = prompt("Project name?");
  if (!name) return;
  const workspace = prompt("Workspace path (absolute)?");
  if (!workspace) return;
  try {
    const project = await api("/api/projects", {
      method: "POST", body: JSON.stringify({ name, workspace }),
    });
    await loadProjects();
    await openProject(project.id);
    setStatus(`Created project ${project.name}`);
  } catch (error) {
    setStatus(String(error.message || error), true);
  }
}

async function inspectWorkspace() {
  try {
    const result = await api(`/api/projects/${state.projectId}/inspect`);
    state.docks.diagnostics = availableViews().diagnostics;
    openDock("diagnostics");
    setStatus(`Workspace inspected: ${result.tree.length} entries, ${result.context_files.length} context files`);
  } catch (error) {
    setStatus(String(error.message || error), true);
  }
}

async function buildPlan() {
  const request = prompt("What should Supli plan?");
  if (!request) return;
  try {
    const plan = await api(`/api/projects/${state.projectId}/plan`, {
      method: "POST", body: JSON.stringify({ request }),
    });
    const lines = plan.steps.map((s, i) =>
      `${i + 1}. ${s.description}${s.files.length ? ` [${s.files.join(", ")}]` : ""}`);
    modal("Plan", el("pre", null,
      `Workspace: ${plan.workspace}\nFiles: ${plan.files.join(", ") || "(none)"}\n\n${lines.join("\n")}`));
    setStatus(`Plan built from ${plan.files.length} real file(s)`);
  } catch (error) {
    setStatus(String(error.message || error), true);
  }
}

async function proposeEdit() {
  if (!state.currentFile) { setStatus("No file open.", true); return; }
  const content = $("#editor").value;
  try {
    const result = await api(`/api/projects/${state.projectId}/file/propose`, {
      method: "POST", body: JSON.stringify({ path: state.currentFile, content }),
    });
    if (!result.changed) { setStatus("No changes to propose."); return; }
    await refreshBadges();
    state.docks.changes = availableViews().changes;
    state.docks.approvals = availableViews().approvals;
    openDock("approvals");
    setStatus(`Proposed edit for ${state.currentFile} — awaiting approval.`);
  } catch (error) {
    setStatus(String(error.message || error), true);
  }
}

async function recover() {
  try {
    const report = await api(`/api/projects/${state.projectId}/recover`, { method: "POST" });
    const lines = [
      `current stage: ${report.current_stage ? report.current_stage.key + " — " + report.current_stage.title : "none"}`,
      `interrupted actions: ${report.interrupted_count}`,
      ...report.interrupted_actions.map((a) => `  ${a.name} (${a.id.slice(0, 8)})`),
      `pending approvals: ${report.pending_approvals.length}`,
      `last successful: ${report.summary.last_successful_action ? report.summary.last_successful_action.name : "none"}`,
    ];
    modal("Crash Recovery Report", el("pre", null, lines.join("\n")));
    await refreshBadges();
  } catch (error) {
    setStatus(String(error.message || error), true);
  }
}

async function refreshProviders() {
  const status = await api("/api/providers");
  const lines = [`active: ${status.active}`];
  for (const p of status.providers) {
    lines.push(`${p.provider}: available=${p.available} local=${p.local}` +
      (p.error ? `\n  error: ${p.error}` : "") +
      (p.models && p.models.length ? `\n  models: ${p.models.join(", ")}` : ""));
  }
  modal("AI Providers", el("pre", null, lines.join("\n")));
  await refreshBadges();
}

/* ---------------- modal ---------------- */

function modal(title, content, actions) {
  $("#modal-title").textContent = title;
  const body = $("#modal-body");
  body.innerHTML = "";
  body.appendChild(content);
  const actionBar = $("#modal-actions");
  actionBar.innerHTML = "";
  const close = el("button", null, "Close");
  close.onclick = () => $("#modal").classList.add("hidden");
  actionBar.appendChild(close);
  if (actions) actions.forEach((a) => actionBar.appendChild(a));
  $("#modal").classList.remove("hidden");
}

/* ---------------- wiring ---------------- */

$("#project-select").onchange = (event) => openProject(event.target.value);
$("#new-project").onclick = newProject;
$("#btn-save").onclick = async () => {
  if (!state.currentFile) { setStatus("No file open.", true); return; }
  try {
    await api(`/api/projects/${state.projectId}/file`, {
      method: "PUT",
      body: JSON.stringify({ path: state.currentFile, content: $("#editor").value }),
    });
    setStatus(`Saved ${state.currentFile}`);
    await refreshTree();
  } catch (error) { setStatus(String(error.message || error), true); }
};
$("#btn-danger").onclick = proposeEdit;
$("#btn-plan").onclick = buildPlan;
$("#btn-inspect").onclick = inspectWorkspace;
$("#btn-recover").onclick = recover;
$("#btn-palette").onclick = openPalette;

$("#editor").addEventListener("input", () => {
  state.editorDirty = true;
  setStatus(`Unsaved changes in ${state.currentFile || "editor"}`);
});

$("#chat-form").onsubmit = (event) => {
  event.preventDefault();
  const text = $("#chat-text").value;
  $("#chat-text").value = "";
  sendChat(text);
};
$("#chat-text").addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    $("#chat-form").requestSubmit();
  }
});

document.querySelectorAll("[data-close]").forEach((button) => {
  button.onclick = () => togglePane(button.dataset.close);
});

document.querySelectorAll(".menu button").forEach((button) => {
  button.onclick = () => openMenu(button.dataset.menu);
});

function openMenu(name) {
  const commands = paletteCommands();
  const list = el("div");
  list.appendChild(el("div", null, `${name} menu`));
  for (const command of commands) {
    const item = el("div", "tool-activity");
    const button = el("button", null, command.label);
    button.onclick = () => { $("#modal").classList.add("hidden"); command.run(); };
    item.appendChild(button);
    list.appendChild(item);
  }
  modal(name, list);
}

$("#palette-input").addEventListener("input", (event) => renderPaletteCommands(event.target.value));
$("#palette-input").addEventListener("keydown", (event) => {
  if (event.key === "Escape") $("#palette").classList.add("hidden");
  if (event.key === "Enter") {
    const active = $("#palette-list li.active") || $("#palette-list li");
    if (active) active.click();
  }
});

document.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
    event.preventDefault();
    openPalette();
  }
  if (event.key === "Escape") {
    $("#palette").classList.add("hidden");
    $("#modal").classList.add("hidden");
  }
});

window.addEventListener("load", async () => {
  try {
    await loadProjects();
    refreshDock();
  } catch (error) {
    setStatus(String(error.message || error), true);
  }
});