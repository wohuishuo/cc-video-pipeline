const TERMINAL_STATES = new Set(["COMPLETED", "FAILED", "CANCELLED"]);
const TEMPLATE_NODE_COPY = {
  "prepared-localization": {
    source: { title: "Prepared folder", description: "Resolve the folder and validate its localization batch manifest.", owner: "source-intake", relationship: "Query", delivery: "DOMAIN_VERIFIED" },
    localize: { title: "Edge localization", description: "Generate Russian voice, mix original ambience and burn translated subtitles.", owner: "localization", relationship: "Adapter", delivery: "IMPLEMENTED" },
    verify: { title: "Verify output", description: "Require inspectable video files and matching execution receipts.", owner: "output-verification", relationship: "Policy", delivery: "DOMAIN_VERIFIED" },
  },
  "folder-intake": {
    source: { title: "Local folder", description: "Resolve one allowed local folder without copying its media.", owner: "source-intake", relationship: "Input", delivery: "DOMAIN_VERIFIED" },
    localize: { title: "Discover media", description: "Build a deterministic manifest and idempotent intake receipt.", owner: "source-intake", relationship: "Command", delivery: "DOMAIN_VERIFIED" },
    verify: { title: "Verify source", description: "Check every declared media path and digest before continuation.", owner: "source-intake", relationship: "Policy", delivery: "DOMAIN_VERIFIED" },
  },
  "url-intake": {
    source: { title: "Social URL", description: "Accept one supported YouTube, Bilibili, Douyin or TikTok URL.", owner: "source-intake", relationship: "Input", delivery: "DOMAIN_VERIFIED" },
    localize: { title: "Download 1080p", description: "Invoke Platform I/O anonymously first with bounded quality fallback.", owner: "platform-io", relationship: "Adapter", delivery: "DOMAIN_VERIFIED" },
    verify: { title: "Verify source", description: "Check downloaded media and commit a reusable source manifest.", owner: "source-intake", relationship: "Policy", delivery: "DOMAIN_VERIFIED" },
  },
};

const state = { currentRun: null, pollTimer: null, folder: null, selectedNode: "localize", templateId: "prepared-localization" };
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
  const sourceUrl = $("#source-url").value.trim();
  const languages = $$('input[name="language"]:checked').map((item) => item.value);
  const platforms = $$('input[name="platform"]:checked').map((item) => item.value);
  const voice = $("#voice").value;
  const needsFolder = state.templateId !== "url-intake";
  if ((needsFolder && !sourceRoot) || (!needsFolder && !sourceUrl)) {
    toast("Choose a source folder or supported social URL.", true);
    return;
  }
  if (state.templateId === "prepared-localization" && (!languages.length || !platforms.length)) {
    toast("Choose a source, language and target.", true);
    return;
  }
  const correlationId = crypto.randomUUID();
  const button = $("#run-button");
  button.disabled = true;
  setRunControlsBusy(true);
  button.innerHTML = "<span>◌</span> Creating…";
  try {
    const payload = state.templateId === "url-intake"
      ? { templateId: state.templateId, sourceUrl, maxHeight: 1080 }
      : state.templateId === "folder-intake"
        ? { templateId: state.templateId, sourceRoot }
        : { templateId: state.templateId, sourceRoot, languages, voice, platforms };
    const create = await api("/api/v1/runs", {
      method: "POST",
      body: JSON.stringify({
        ...envelope("CMD-RUN-CREATE", correlationId, payload),
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
    setRunControlsBusy(false);
    button.innerHTML = "<span>▶</span> Run graph";
  }
}

function setRunControlsBusy(busy) {
  $$('#run-form input[name="template"]').forEach((input) => { input.disabled = busy; });
}

function resetRunProjection() {
  state.currentRun = null;
  $$(".graph-node").forEach((node) => {
    node.classList.remove("running", "completed", "failed", "cancelled", "interrupted");
    node.querySelector(".node-status").textContent = node.dataset.stepId ? "WAITING" : "READY";
  });
  $("#run-progress").textContent = state.templateId === "prepared-localization" ? "0 / 3" : "0 / 2";
  $("#progress-bar").style.width = "0%";
  $("#run-id").textContent = "No active run";
  $("#activity-summary").textContent = "Waiting for a run";
  $("#log-output").textContent = "Choose a source and run the graph. Durable logs will appear here.";
}

function selectTemplate(templateId) {
  state.templateId = templateId;
  const urlMode = templateId === "url-intake";
  const sourceRoot = $("#source-root");
  const sourceUrl = $("#source-url");
  $("#url-source-field").hidden = !urlMode;
  sourceRoot.closest(".source-field").hidden = urlMode;
  sourceRoot.required = !urlMode;
  sourceUrl.required = urlMode;
  const intakeMode = templateId !== "prepared-localization";
  $$('[aria-label="Target languages"], .voice-field, [aria-label="Target platforms"]').forEach((element) => {
    element.classList.toggle("control-muted", intakeMode);
  });
  $$('.template-field .choice').forEach((label) => {
    label.classList.toggle("active", label.querySelector("input").value === templateId);
  });
  const copy = templateId === "prepared-localization"
    ? ["Prepared folder", "Validate batch manifest", "Edge localization", "Voice · mix · hard subtitles", "Verify output", "Inspect files and receipts"]
    : templateId === "folder-intake"
      ? ["Local folder", "Resolve an allowed source", "Discover media", "Build deterministic manifest", "Verify source", "Check files and receipt"]
      : ["Social URL", "YouTube · Bilibili · Douyin · TikTok", "Download 1080p", "Anonymous first · cookie optional", "Verify source", "Check files and receipt"];
  ["source-node-title", "source-node-description", "process-node-title", "process-node-description", "output-node-title", "output-node-description"]
    .forEach((id, index) => { $(`#${id}`).textContent = copy[index]; });
  const stepIds = templateId === "prepared-localization" ? ["source", "localize", "verify"] : ["", "intake", "verify"];
  $$(".graph-node").forEach((node, index) => { node.dataset.stepId = stepIds[index]; });
  const paletteCopy = templateId === "prepared-localization"
    ? ["Prepared folder", "Local query", "Edge localization", "Serial adapter", "Verify outputs", "Receipt policy"]
    : templateId === "folder-intake"
      ? ["Local folder", "Local input", "Discover media", "Serial command", "Verify source", "Manifest policy"]
      : ["Social URL", "Remote input", "Download 1080p", "Platform adapter", "Verify source", "Manifest policy"];
  ["palette-source-title", "palette-source-detail", "palette-process-title", "palette-process-detail", "palette-output-title", "palette-output-detail"]
    .forEach((id, index) => { $(`#${id}`).textContent = paletteCopy[index]; });
  $(".workspace-label").textContent = templateId === "prepared-localization" ? "Prepared Folder Localization" : templateId === "folder-intake" ? "Folder Source Intake" : "Social URL Intake";
  $$(".source-preview").forEach((element) => { element.textContent = (urlMode ? sourceUrl.value : sourceRoot.value) || "Not selected"; });
  resetRunProjection();
  focusNode(state.selectedNode);
}

async function pollRun(runId) {
  clearTimeout(state.pollTimer);
  try {
    const run = await api(`/api/v1/runs/${runId}`);
    state.currentRun = run;
    renderRun(run);
    if (TERMINAL_STATES.has(run.status)) {
      $("#run-button").disabled = false;
      setRunControlsBusy(false);
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
    const step = byNode[node.dataset.stepId];
    const fallbackStatus = node.dataset.stepId ? "WAITING" : "READY";
    const status = (step?.status || fallbackStatus).toLowerCase();
    node.classList.remove("running", "completed", "failed", "cancelled", "interrupted");
    if (["running", "completed", "failed", "cancelled", "interrupted"].includes(status)) node.classList.add(status);
    node.querySelector(".node-status").textContent = step?.status || fallbackStatus;
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
  const copy = TEMPLATE_NODE_COPY[state.templateId][nodeId];
  $("#inspector-title").textContent = copy.title;
  $("#inspector-description").textContent = copy.description;
  const properties = $$(".property code");
  properties[0].textContent = copy.owner;
  properties[1].textContent = copy.relationship;
  properties[2].textContent = copy.delivery;
  const node = $(`.graph-node[data-node-id="${nodeId}"]`);
  const step = state.currentRun?.steps.find((item) => item.nodeId === node?.dataset.stepId);
  $("#inspector-state").textContent = step?.status || (node?.dataset.stepId ? "WAITING" : "READY");
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
  $("#source-url").addEventListener("input", (event) => $$(".source-preview").forEach((element) => { element.textContent = event.target.value || "Not selected"; }));
  $$('input[name="template"]').forEach((input) => input.addEventListener("change", () => selectTemplate(input.value)));
}

bindEvents();
checkHealth();
focusNode("localize");
selectTemplate("prepared-localization");
