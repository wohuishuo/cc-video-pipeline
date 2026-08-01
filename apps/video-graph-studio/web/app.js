const TERMINAL_STATES = new Set(["COMPLETED", "FAILED", "CANCELLED"]);
const NODE_COPY = {
  source: { title: "Prepared folder", description: "Resolve the folder and validate its localization batch manifest.", owner: "source-intake", relationship: "Query", delivery: "DOMAIN_VERIFIED" },
  localize: { title: "Edge localization", description: "Generate Russian voice, mix original ambience and burn translated subtitles.", owner: "localization", relationship: "Adapter", delivery: "IMPLEMENTED" },
  verify: { title: "Verify output", description: "Require inspectable video files and matching execution receipts.", owner: "output-verification", relationship: "Policy", delivery: "DOMAIN_VERIFIED" },
};

const state = { currentRun: null, pollTimer: null, folder: null, selectedNode: "localize" };
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const body = await response.json();
  if (!response.ok) {
    const error = new Error(body.detail || body.resultClass || `HTTP ${response.status}`);
    error.body = body;
    throw error;
  }
  return body;
}

function envelope(contractId, correlationId, payload = {}) {
  return {
    contractId,
    contractVersion: "1.0",
    operationId: crypto.randomUUID(),
    correlationId,
    payload,
  };
}

function toast(message, error = false) {
  const element = $("#toast");
  element.textContent = message;
  element.className = error ? "visible error" : "visible";
  clearTimeout(element._timer);
  element._timer = setTimeout(() => { element.className = ""; }, 3500);
}

async function checkHealth() {
  try {
    const health = await api("/api/v1/health");
    const pill = $("#health-pill");
    pill.classList.add("ready");
    pill.lastChild.textContent = health.activeWorkers ? " 1 worker active" : " System ready";
  } catch (error) {
    $("#health-pill").lastChild.textContent = " Offline";
  }
}

async function openFolderBrowser() {
  const dialog = $("#folder-dialog");
  dialog.showModal();
  await loadFolder($("#source-root").value || "");
}

async function loadFolder(path) {
  try {
    const suffix = path ? `?path=${encodeURIComponent(path)}` : "";
    const folder = await api(`/api/v1/folders${suffix}`);
    state.folder = folder;
    $("#current-folder").textContent = folder.path;
    $("#folder-up").disabled = !folder.parent;
    $("#folder-media-count").textContent = `${folder.videoCount} video${folder.videoCount === 1 ? "" : "s"} in this folder`;
    const list = $("#folder-list");
    list.replaceChildren();
    folder.directories.forEach((directory) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "folder-row";
      button.innerHTML = `<i>◆</i><span></span>`;
      button.querySelector("span").textContent = directory.name;
      button.addEventListener("dblclick", () => loadFolder(directory.path));
      button.addEventListener("click", () => loadFolder(directory.path));
      list.append(button);
    });
    if (!folder.directories.length) {
      list.innerHTML = '<p class="muted">No child folders. You can still choose this folder.</p>';
    }
  } catch (error) {
    toast(error.message, true);
  }
}

function selectFolder() {
  if (!state.folder) return;
  $("#source-root").value = state.folder.path;
  $$(".source-preview").forEach((element) => { element.textContent = state.folder.path; });
}

async function submitRun(event) {
  event.preventDefault();
  const sourceRoot = $("#source-root").value.trim();
  const languages = $$('input[name="language"]:checked').map((item) => item.value);
  const platforms = $$('input[name="platform"]:checked').map((item) => item.value);
  const voice = $("#voice").value;
  if (!sourceRoot || !languages.length || !platforms.length) {
    toast("Choose a source, language and target.", true);
    return;
  }
  const correlationId = crypto.randomUUID();
  const button = $("#run-button");
  button.disabled = true;
  button.innerHTML = "<span>◌</span> Creating…";
  try {
    const create = await api("/api/v1/runs", {
      method: "POST",
      body: JSON.stringify({
        ...envelope("CMD-RUN-CREATE", correlationId, { sourceRoot, languages, voice, platforms }),
        contractId: "CMD-RUN-CREATE",
      }),
    });
    const runId = create.value.runId;
    await api(`/api/v1/runs/${runId}/start`, {
      method: "POST",
      body: JSON.stringify({ ...envelope("CMD-RUN-START", correlationId), contractId: "CMD-RUN-START" }),
    });
    toast("Graph admitted. Serial worker started.");
    await pollRun(runId);
  } catch (error) {
    toast(error.message, true);
    button.disabled = false;
    button.innerHTML = "<span>▶</span> Run graph";
  }
}

async function pollRun(runId) {
  clearTimeout(state.pollTimer);
  try {
    const run = await api(`/api/v1/runs/${runId}`);
    state.currentRun = run;
    renderRun(run);
    if (TERMINAL_STATES.has(run.status)) {
      $("#run-button").disabled = false;
      $("#run-button").innerHTML = "<span>▶</span> Run graph";
      await checkHealth();
      return;
    }
    state.pollTimer = setTimeout(() => pollRun(runId), 900);
  } catch (error) {
    toast(error.message, true);
    state.pollTimer = setTimeout(() => pollRun(runId), 2500);
  }
}

function renderRun(run) {
  const byNode = Object.fromEntries(run.steps.map((step) => [step.nodeId, step]));
  $$(".graph-node").forEach((node) => {
    const step = byNode[node.dataset.nodeId];
    const status = (step?.status || "WAITING").toLowerCase();
    node.classList.remove("running", "completed", "failed", "cancelled", "interrupted");
    if (["running", "completed", "failed", "cancelled", "interrupted"].includes(status)) node.classList.add(status);
    node.querySelector(".node-status").textContent = step?.status || "WAITING";
  });
  const complete = run.steps.filter((step) => step.status === "COMPLETED").length;
  $("#run-progress").textContent = `${complete} / ${run.steps.length}`;
  $("#progress-bar").style.width = `${Math.round(complete / run.steps.length * 100)}%`;
  $("#run-id").textContent = `${run.runId} · ${run.status}`;
  $("#activity-summary").textContent = `${run.status} · ${run.logs.length} log entries`;
  $("#log-output").textContent = run.logs.length
    ? run.logs.map((row) => `${String(row.sequence).padStart(3, "0")}  ${row.message}`).join("\n")
    : "Run admitted. Waiting for worker output…";
  $("#log-output").scrollTop = $("#log-output").scrollHeight;
  focusNode(state.selectedNode);
}

function focusNode(nodeId) {
  state.selectedNode = nodeId;
  $$(".graph-node").forEach((node) => node.classList.toggle("selected", node.dataset.nodeId === nodeId));
  const copy = NODE_COPY[nodeId];
  $("#inspector-title").textContent = copy.title;
  $("#inspector-description").textContent = copy.description;
  const properties = $$(".property code");
  properties[0].textContent = copy.owner;
  properties[1].textContent = copy.relationship;
  properties[2].textContent = copy.delivery;
  const step = state.currentRun?.steps.find((item) => item.nodeId === nodeId);
  $("#inspector-state").textContent = step?.status || "WAITING";
}

function bindEvents() {
  $("#run-form").addEventListener("submit", submitRun);
  $("#browse-folder").addEventListener("click", openFolderBrowser);
  $("#folder-up").addEventListener("click", () => state.folder?.parent && loadFolder(state.folder.parent));
  $("#choose-folder").addEventListener("click", selectFolder);
  $("#toggle-activity").addEventListener("click", () => $("#activity-log").classList.toggle("collapsed"));
  $("#clear-view").addEventListener("click", () => { $("#log-output").textContent = "View cleared. Durable logs remain stored."; });
  $$(".graph-node").forEach((node) => node.addEventListener("click", () => focusNode(node.dataset.nodeId)));
  $$('[data-focus-node]').forEach((button) => button.addEventListener("click", () => focusNode(button.dataset.focusNode)));
  $("#source-root").addEventListener("input", (event) => $$(".source-preview").forEach((element) => { element.textContent = event.target.value || "Not selected"; }));
}

bindEvents();
checkHealth();
focusNode("localize");

