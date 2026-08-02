import {
  evaluateReadiness,
  groupWorkflowGoals,
  nextZoom,
  projectGraph,
  resolveTemplate,
} from "./workflow-model.mjs";

const TERMINAL_STATES = new Set(["COMPLETED", "FAILED", "CANCELLED"]);
const DEFAULT_VOICES = {
  "ru-RU": "ru-RU-DmitryNeural",
  "en-US": "en-US-GuyNeural",
  "kk-KZ": "kk-KZ-DauletNeural",
};
const EFFECT_COPY = {
  "local-only": "Works only with local files. No social platform is contacted.",
  "downloads-source": "Reads or downloads the selected source. It does not publish anything.",
  "planning-only": "Creates local private or draft plans. It does not upload anything.",
  "contacts-youtube-private": "Contacts YouTube only after exact confirmation and creates private uploads.",
  "reads-profile": "Reads the selected creator profile to build an ordered video manifest.",
  "opens-google-consent": "Opens Google consent and stores the resulting credential in the local Vault.",
};
const CONFIG_BY_REQUIREMENT = {
  "source-folder": "folder-source-field",
  "source-url": "url-source-field",
  asr: "asr-controls",
  translation: "translation-controls",
  languages: "target-language-controls",
  voices: "target-language-controls",
  voice: "prepared-controls",
  platforms: "prepared-controls",
  "creator-options": "creator-controls",
  video: "publication-controls",
  metadata: "publication-controls",
  "publication-targets": "publication-controls",
  account: "publication-controls",
  "metadata-template": "release-controls",
  "release-account": "release-controls",
  "release-targets": "release-controls",
  "plan-run": "publication-execution-controls",
  "release-run": "publication-batch-execution-controls",
  confirmation: null,
  vault: null,
  "client-config": "youtube-connect-controls",
  "vault-destination": "youtube-connect-controls",
  credential: "youtube-connect-controls",
  label: "youtube-connect-controls",
};
const CONTROL_REGIONS = [
  "folder-source-field", "url-source-field", "asr-controls", "translation-controls",
  "target-language-controls", "prepared-controls", "creator-controls", "publication-controls",
  "release-controls", "publication-execution-controls", "publication-batch-execution-controls",
  "youtube-connect-controls",
];

const state = {
  catalog: [],
  workflow: null,
  goalId: null,
  sourceKind: null,
  templateId: null,
  currentRun: null,
  recentRuns: [],
  pollTimer: null,
  folder: null,
  selectedNode: null,
  zoom: 100,
  busy: false,
  accessRequired: false,
  workspaceId: sessionStorage.getItem("videoGraph.workspaceId") || "",
  contracts: null,
  connection: { contracts: false, health: false, access: false, catalog: false },
  connectionError: "",
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

async function api(path, options = {}) {
  const token = sessionStorage.getItem("videoGraph.accessToken");
  const workspaceId = sessionStorage.getItem("videoGraph.workspaceId");
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(workspaceId ? { "X-Workspace-Id": workspaceId } : {}),
      ...(options.headers || {}),
    },
  });
  let body;
  try {
    body = await response.json();
  } catch {
    body = {};
  }
  if (!response.ok) {
    const error = new Error(body.detail || body.resultClass || `HTTP ${response.status}`);
    error.body = body;
    error.status = response.status;
    throw error;
  }
  return body;
}

function envelope(contractId, correlationId, payload = {}) {
  if (!state.contracts?.commands?.[contractId]) throw new Error(`Unsupported command: ${contractId}`);
  return {
    contractId,
    contractVersion: state.contracts.contractVersion,
    operationId: crypto.randomUUID(),
    correlationId,
    payload,
  };
}

async function loadContracts() {
  const response = await api("/api/v1/contracts");
  const bundle = response.value?.bundle;
  const required = ["CMD-RUN-CREATE", "CMD-RUN-START", "CMD-RUN-CANCEL"];
  if (!bundle || bundle.schemaVersion !== 1 || !bundle.contractVersion || !required.every((key) => bundle.commands?.[key]) || !bundle.endpoints?.["GET /api/v1/contracts"]) {
    throw new Error("Contract unavailable");
  }
  state.contracts = bundle;
  state.connection.contracts = true;
}

function toast(message, error = false) {
  const element = $("#toast");
  element.textContent = message;
  element.className = error ? "visible error" : "visible";
  clearTimeout(element._timer);
  element._timer = setTimeout(() => { element.className = ""; }, 3500);
}

function bootstrapAccess() {
  const fragment = new URLSearchParams(location.hash.slice(1));
  const token = fragment.get("access_token");
  const workspaceId = fragment.get("workspace");
  if (token && workspaceId) {
    sessionStorage.setItem("videoGraph.accessToken", token);
    sessionStorage.setItem("videoGraph.workspaceId", workspaceId);
    history.replaceState(null, "", `${location.pathname}${location.search}`);
  }
}

function hasWorkspaceAccess() {
  if (!state.accessRequired) return true;
  return Boolean(sessionStorage.getItem("videoGraph.accessToken"))
    && sessionStorage.getItem("videoGraph.workspaceId") === state.workspaceId;
}

async function loadHealth() {
  const health = await api("/api/v1/health");
  state.connection.health = true;
  state.accessRequired = health.accessRequired === true;
  state.workspaceId = health.workspaceId || sessionStorage.getItem("videoGraph.workspaceId") || "";
  state.connection.access = hasWorkspaceAccess();
  const accessButton = $("#access-button");
  accessButton.hidden = !state.accessRequired;
  accessButton.classList.toggle("required", !state.connection.access);
  accessButton.textContent = state.connection.access ? state.workspaceId : "Access required";
  $("#access-workspace").value = state.workspaceId;
  return health;
}

async function loadCatalog() {
  const response = await api("/api/v1/capabilities");
  const catalog = response.capabilities || response.value?.capabilities || response.value || [];
  if (!Array.isArray(catalog) || !catalog.length || catalog.some((item) => !item.templateId || !Array.isArray(item.nodes))) {
    throw new Error("Workflow Catalog unavailable");
  }
  state.catalog = catalog;
  state.connection.catalog = true;
  renderGoalOptions();
}

async function reconnect() {
  const reconnectButton = $("#reconnect-button");
  reconnectButton.disabled = true;
  reconnectButton.textContent = "Checking…";
  state.contracts = null;
  state.connection = { contracts: false, health: false, access: false, catalog: false };
  state.connectionError = "";
  let health = null;
  const errors = [];
  try {
    await loadContracts();
  } catch (error) {
    errors.push(error.status === 404
      ? "Server version mismatch: restart Studio so the contracts endpoint is available."
      : `Client contract: ${error.message}`);
  }
  try {
    health = await loadHealth();
  } catch (error) {
    const denied = ["REJECTED_UNAUTHORIZED", "REJECTED_WORKSPACE"].includes(error.body?.resultClass);
    errors.push(denied ? "Workspace access was rejected." : `Studio service: ${error.message}`);
    if (denied) $("#access-button").hidden = false;
  }
  if (state.connection.health && state.connection.access) {
    try {
      await loadCatalog();
    } catch (error) {
      errors.push(`Workflow Catalog: ${error.message}`);
    }
    try {
      await refreshRunList();
    } catch (error) {
      errors.push(`Run history: ${error.message}`);
    }
  } else if (state.connection.health && !state.connection.access) {
    errors.push("Connect this browser session to the admitted workspace.");
  }
  state.connectionError = errors.join(" ");
  renderConnection(health);
  renderReadiness();
  reconnectButton.disabled = false;
  reconnectButton.textContent = "Reconnect";
}

function renderConnection(health) {
  const pill = $("#health-pill");
  pill.classList.toggle("ready", Object.values(state.connection).every(Boolean));
  if (!state.connection.health) pill.lastElementChild.textContent = "Offline";
  else if (!state.connection.access) pill.lastElementChild.textContent = "Access required";
  else if (!state.connection.contracts) pill.lastElementChild.textContent = "Restart required";
  else if (!state.connection.catalog) pill.lastElementChild.textContent = "Catalog unavailable";
  else if (health?.activeWorkers) pill.lastElementChild.textContent = `1 worker active${health.queuedRuns ? ` / ${health.queuedRuns} queued` : ""}`;
  else pill.lastElementChild.textContent = health?.queuedRuns ? `${health.queuedRuns} queued` : "System ready";
}

function saveAccess(event) {
  event.preventDefault();
  const workspaceId = $("#access-workspace").value.trim();
  const token = $("#access-token").value.trim();
  if (!workspaceId || !token) return;
  sessionStorage.setItem("videoGraph.workspaceId", workspaceId);
  sessionStorage.setItem("videoGraph.accessToken", token);
  $("#access-token").value = "";
  $("#access-dialog").close();
  reconnect();
}

function clearAccess() {
  sessionStorage.removeItem("videoGraph.workspaceId");
  sessionStorage.removeItem("videoGraph.accessToken");
  $("#access-token").value = "";
  $("#access-dialog").close();
  reconnect();
}

function renderGoalOptions() {
  const select = $("#workflow-goal");
  const previous = state.goalId;
  select.replaceChildren();
  for (const section of groupWorkflowGoals(state.catalog)) {
    const group = document.createElement("optgroup");
    group.label = section.group;
    for (const goal of section.goals) {
      const option = document.createElement("option");
      option.value = goal.goalId;
      option.textContent = goal.title;
      group.append(option);
    }
    select.append(group);
  }
  const goals = groupWorkflowGoals(state.catalog).flatMap((section) => section.goals);
  const preferred = goals.find((goal) => goal.goalId === previous)
    || goals.find((goal) => goal.goalId === "dub") || goals[0];
  if (preferred) {
    select.value = preferred.goalId;
    selectGoal(preferred.goalId);
  }
}

function selectGoal(goalId) {
  const goal = groupWorkflowGoals(state.catalog).flatMap((section) => section.goals)
    .find((item) => item.goalId === goalId);
  if (!goal) return;
  state.goalId = goalId;
  const sourceControls = $("#source-kind-controls");
  const sourceVariants = goal.variants.filter((variant) => ["folder", "url"].includes(variant.sourceKind));
  sourceControls.hidden = sourceVariants.length < 2;
  const preferredKind = goal.variants.some((variant) => variant.sourceKind === state.sourceKind)
    ? state.sourceKind
    : goal.variants.find((variant) => variant.sourceKind === "url")?.sourceKind || goal.variants[0].sourceKind;
  state.sourceKind = preferredKind;
  $$('input[name="source-kind"]').forEach((input) => {
    input.checked = input.value === preferredKind;
    input.disabled = !goal.variants.some((variant) => variant.sourceKind === input.value);
  });
  applyWorkflow(resolveTemplate(state.catalog, goalId, preferredKind));
}

function applyWorkflow(workflow) {
  state.workflow = workflow;
  state.templateId = workflow?.templateId || null;
  state.currentRun = null;
  state.selectedNode = workflow?.nodes?.[0]?.id || null;
  for (const id of CONTROL_REGIONS) $("#" + id).hidden = true;
  const requirements = new Set(workflow?.requirements || []);
  for (const requirement of requirements) {
    const region = CONFIG_BY_REQUIREMENT[requirement];
    if (region) $("#" + region).hidden = false;
  }
  if (requirements.has("plan-run")) $("#publication-execution-controls").hidden = false;
  if (requirements.has("release-run")) $("#publication-batch-execution-controls").hidden = false;
  $("#workflow-summary").innerHTML = workflow
    ? `<strong></strong><span></span>` : "<strong>Choose an outcome</strong>";
  if (workflow) {
    $("#workflow-summary strong").textContent = workflow.title;
    $("#workflow-summary span").textContent = workflow.summary;
    $("#canvas-title").textContent = workflow.title;
    $("#canvas-description").textContent = workflow.summary;
    $("#save-state").textContent = `${workflow.templateId} · draft`;
  }
  if (workflow?.templateId === "publication-execute") populateLatestPublicationPlan();
  if (workflow?.templateId === "publication-batch-execute") populateLatestPublicationBatchPlan();
  renderGraph();
  renderReadiness();
}

function checkedValues(name) {
  return $$(`input[name="${name}"]:checked`).map((item) => item.value);
}

function readDraftValues() {
  const targetLanguages = checkedValues("language");
  return {
    sourceRoot: $("#source-root").value.trim(),
    sourceUrl: $("#source-url").value.trim(),
    sourceLanguage: $("#source-language").value,
    asrModel: $("#asr-model").value,
    asrDevice: $("#asr-device").value,
    translationDevice: $("#translation-device").value,
    translationBatchSize: Number($("#translation-batch-size").value),
    targetLanguages,
    targetVoices: Object.fromEntries(targetLanguages.map((language) => [language, DEFAULT_VOICES[language]])),
    sourceVolume: 0.12,
    voice: $("#voice").value,
    platforms: checkedValues("platform"),
    maxItems: Number($("#creator-max-items").value),
    authenticationFile: $("#authentication-file").value.trim(),
    videoPath: $("#publication-video").value.trim(),
    metadataPath: $("#publication-metadata").value.trim(),
    publicationTargets: checkedValues("publication-target"),
    account: $("#publication-account").value.trim(),
    planRunId: $("#publication-plan-run-id").value.trim(),
    confirmation: state.templateId === "publication-batch-execute"
      ? $("#release-execution-confirmation").value.trim() : $("#publication-confirmation").value.trim(),
    credentialVaultPath: state.templateId === "publication-batch-execute"
      ? $("#release-credential-vault-path").value.trim()
      : state.templateId === "youtube-connect" ? $("#youtube-vault-path").value.trim()
      : $("#credential-vault-path").value.trim(),
    releasePlanRunId: $("#release-plan-run-id").value.trim(),
    metadataTemplatePath: $("#release-metadata-template").value.trim(),
    releaseAccount: $("#release-account").value.trim(),
    releaseTargets: checkedValues("release-target"),
    clientConfigPath: $("#youtube-client-config").value.trim(),
    credentialId: $("#youtube-credential-id").value.trim(),
    label: $("#youtube-credential-label").value.trim(),
  };
}

function renderReadiness() {
  const result = evaluateReadiness({ connection: state.connection, workflow: state.workflow, values: readDraftValues() });
  const list = $("#readiness-list");
  list.replaceChildren();
  for (const check of result.checks) {
    const item = document.createElement("li");
    item.className = check.status;
    const label = document.createElement("span");
    label.textContent = check.label;
    const detail = document.createElement("small");
    detail.textContent = check.detail;
    item.append(label, detail);
    list.append(item);
  }
  const error = $("#connection-error");
  error.hidden = !state.connectionError;
  error.textContent = state.connectionError;
  const effect = $("#effect-summary");
  effect.textContent = EFFECT_COPY[result.effect] || "No platform action selected.";
  effect.classList.toggle("risk", ["contacts-youtube-private", "opens-google-consent"].includes(result.effect));
  $("#run-button").disabled = !result.ready || state.busy;
  return result;
}

function renderGraph() {
  const graph = projectGraph(state.workflow, state.currentRun);
  const track = $("#graph-track");
  track.replaceChildren();
  $("#graph-empty-state").hidden = graph.length > 0;
  $("#node-count").textContent = `${graph.length} step${graph.length === 1 ? "" : "s"}`;
  $("#loop-count").textContent = `${new Set(graph.map((node) => node.loop)).size} loops`;
  graph.forEach((node, index) => {
    if (index) {
      const edge = document.createElement("div");
      edge.className = "graph-edge";
      const relationship = state.workflow.edges[index - 1]?.relationship || "Fact";
      edge.innerHTML = "<span></span>";
      edge.querySelector("span").textContent = relationship;
      track.append(edge);
    }
    const button = document.createElement("button");
    const status = String(node.status || "WAITING").toLowerCase();
    button.type = "button";
    button.className = `graph-node ${String(node.relationship).toLowerCase()} ${status}`;
    button.dataset.nodeId = node.id;
    button.innerHTML = `
      <span class="node-head"><span class="step-number"></span><span class="node-status"></span></span>
      <span class="node-content"><span class="loop-badge"></span><h3></h3><p></p>
      <span class="node-meta"><span>Owner <b class="node-owner"></b></span><span class="node-relationship"></span></span></span>`;
    button.querySelector(".step-number").textContent = `STEP ${String(node.step).padStart(2, "0")}`;
    button.querySelector(".node-status").textContent = node.status;
    button.querySelector(".loop-badge").textContent = `${node.loop} Loop`;
    button.querySelector("h3").textContent = node.title;
    button.querySelector("p").textContent = node.description;
    button.querySelector(".node-owner").textContent = node.owner;
    button.querySelector(".node-relationship").textContent = node.relationship;
    track.append(button);
  });
  if (!graph.some((node) => node.id === state.selectedNode)) state.selectedNode = graph[0]?.id || null;
  setZoom(state.zoom);
  focusNode(state.selectedNode);
}

function handleGraphNodeClick(event) {
  const node = event.target.closest("[data-node-id]");
  if (node && $("#graph-track").contains(node)) focusNode(node.dataset.nodeId);
}

function focusNode(nodeId) {
  state.selectedNode = nodeId;
  $$(".graph-node").forEach((node) => node.classList.toggle("selected", node.dataset.nodeId === nodeId));
  const node = projectGraph(state.workflow, state.currentRun).find((item) => item.id === nodeId);
  if (!node) return;
  $("#inspector-step").textContent = String(node.step).padStart(2, "0");
  $("#inspector-title").textContent = node.title;
  $("#inspector-description").textContent = node.description;
  $("#inspector-state").textContent = node.status;
  $("#inspector-state").className = `state ${String(node.status).toLowerCase()}`;
  $("#inspector-loop").textContent = node.loop;
  $("#inspector-owner").textContent = node.owner;
  $("#inspector-relationship").textContent = node.relationship;
  $("#inspector-retry").textContent = node.retry;
  $("#inspector-output").textContent = node.output;
}

function setZoom(value) {
  state.zoom = Math.max(60, Math.min(140, Math.round(value)));
  $("#graph-track").style.setProperty("--graph-zoom", String(state.zoom / 100));
  $("#zoom-level").textContent = `${state.zoom}%`;
}

function fitGraph() {
  const count = state.workflow?.nodes?.length || 0;
  if (!count) return setZoom(100);
  const available = Math.max(260, $("#graph-grid").clientWidth - 64);
  const natural = count * 210 + Math.max(0, count - 1) * 52 + 84;
  setZoom(Math.min(100, Math.max(60, Math.floor(available / natural * 100))));
  $("#graph-grid").scrollTo({ left: 0, top: 0, behavior: "smooth" });
}

function templateForRun(run) {
  return run.graph.graphId === "prepared-folder-edge" ? "prepared-localization" : run.graph.graphId;
}

async function refreshRunList() {
  const [runsResponse, queue] = await Promise.all([api("/api/v1/runs"), api("/api/v1/queue")]);
  state.recentRuns = runsResponse.runs || [];
  if (state.templateId === "publication-execute") populateLatestPublicationPlan();
  if (state.templateId === "publication-batch-execute") populateLatestPublicationBatchPlan();
  $("#queue-count").textContent = `${queue.queuedRuns || 0} waiting`;
  const list = $("#run-list");
  list.replaceChildren();
  for (const run of state.recentRuns.slice(0, 8)) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `run-row${state.currentRun?.runId === run.runId ? " selected" : ""}`;
    button.innerHTML = "<strong></strong><b></b><small></small>";
    button.querySelector("strong").textContent = run.graph.graphId;
    button.querySelector("b").className = run.status.toLowerCase();
    button.querySelector("b").textContent = run.status;
    button.querySelector("small").textContent = run.runId.slice(0, 13);
    button.addEventListener("click", () => selectRun(run));
    list.append(button);
  }
  if (!state.recentRuns.length) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = "No runs yet.";
    list.append(empty);
  }
}

function selectRun(run) {
  const templateId = templateForRun(run);
  const workflow = state.catalog.find((item) => item.templateId === templateId);
  if (workflow) {
    state.goalId = workflow.goalId;
    state.sourceKind = workflow.sourceKind;
    $("#workflow-goal").value = workflow.goalId;
    applyWorkflow(workflow);
  }
  state.currentRun = run;
  renderRun(run);
  if (!TERMINAL_STATES.has(run.status)) pollRun(run.runId);
}

function populateLatestPublicationPlan() {
  const planRun = state.recentRuns.find((run) => run.status === "COMPLETED" && run.graph?.graphId === "publication-plan" && run.parameters?.targetPlatforms?.length === 1 && run.parameters.targetPlatforms[0] === "youtube" && run.parameters?.credentialIds?.youtube);
  const fact = planRun?.steps?.find((step) => step.nodeId === "plan-publication" && step.status === "COMPLETED")?.result;
  if (!planRun || !fact?.manifestSha256) return;
  if (!$("#publication-plan-run-id").value) $("#publication-plan-run-id").value = planRun.runId;
  if (!$("#publication-confirmation").value) $("#publication-confirmation").value = fact.manifestSha256;
}

function populateLatestPublicationBatchPlan() {
  const releaseRun = state.recentRuns.find((run) => run.status === "COMPLETED" && ["folder-release", "url-release"].includes(run.graph?.graphId) && run.parameters?.targetPlatforms?.length === 1 && run.parameters.targetPlatforms[0] === "youtube" && run.parameters?.credentialIds?.youtube);
  const fact = releaseRun?.steps?.find((step) => step.nodeId === "plan-publication-batch" && step.status === "COMPLETED")?.result;
  if (!releaseRun || !fact?.manifestSha256) return;
  if (!$("#release-plan-run-id").value) $("#release-plan-run-id").value = releaseRun.runId;
  if (!$("#release-execution-confirmation").value) $("#release-execution-confirmation").value = fact.manifestSha256;
}

async function openFolderBrowser() {
  $("#folder-dialog").showModal();
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
    for (const directory of folder.directories) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "folder-row";
      button.innerHTML = "<i>◆</i><span></span>";
      button.querySelector("span").textContent = directory.name;
      button.addEventListener("click", () => loadFolder(directory.path));
      list.append(button);
    }
    if (!folder.directories.length) list.innerHTML = '<p class="muted">No child folders. You can still choose this folder.</p>';
  } catch (error) {
    toast(error.message, true);
  }
}

function selectFolder() {
  if (!state.folder) return;
  $("#source-root").value = state.folder.path;
  renderReadiness();
}

function buildPayload(values) {
  const templateId = state.templateId;
  const sourcePayload = state.workflow.sourceKind === "url" || state.workflow.sourceKind === "creator"
    ? { sourceUrl: values.sourceUrl, maxHeight: 1080 } : { sourceRoot: values.sourceRoot };
  const asrDevice = values.asrDevice;
  const transcriptPayload = {
    templateId, ...sourcePayload, sourceLanguage: values.sourceLanguage,
    asrModel: values.asrModel, asrDevice,
    asrComputeType: asrDevice === "cpu" ? "int8" : asrDevice === "cuda" ? "float16" : "default",
  };
  const translationPayload = {
    ...transcriptPayload, targetLanguages: values.targetLanguages,
    translationModel: "facebook/nllb-200-distilled-600M",
    translationDevice: values.translationDevice, translationBatchSize: values.translationBatchSize,
  };
  const voicePayload = { ...translationPayload, targetVoices: values.targetVoices };
  if (templateId === "youtube-connect") return { templateId, clientConfigPath: values.clientConfigPath, credentialVaultPath: values.credentialVaultPath, credentialId: values.credentialId, label: values.label };
  if (templateId === "publication-plan") {
    const credentialId = $("#publication-credential-id").value.trim();
    return { templateId, videoPath: values.videoPath, metadataPath: values.metadataPath, targetPlatforms: values.publicationTargets, account: values.account, credentialIds: credentialId && values.publicationTargets.includes("youtube") ? { youtube: credentialId } : {}, public: false };
  }
  if (templateId === "publication-execute") return { templateId, planRunId: values.planRunId, confirmation: values.confirmation, credentialVaultPath: values.credentialVaultPath };
  if (templateId === "publication-batch-execute") return { templateId, releasePlanRunId: values.releasePlanRunId, confirmation: values.confirmation, credentialVaultPath: values.credentialVaultPath };
  if (templateId === "creator-profile") return { templateId, sourceUrl: values.sourceUrl, maxItems: values.maxItems, authenticationFile: values.authenticationFile || undefined };
  if (templateId === "creator-batch-dub") return { ...voicePayload, sourceUrl: values.sourceUrl, maxItems: values.maxItems, authenticationFile: values.authenticationFile || undefined, sourceVolume: values.sourceVolume };
  if (templateId.endsWith("-release")) {
    const credentialId = $("#release-credential-id").value.trim();
    return { ...voicePayload, sourceVolume: values.sourceVolume, metadataTemplatePath: values.metadataTemplatePath, targetPlatforms: values.releaseTargets, targetAccounts: Object.fromEntries(values.releaseTargets.map((platform) => [platform, values.releaseAccount])), credentialIds: credentialId && values.releaseTargets.includes("youtube") ? { youtube: credentialId } : {}, public: false };
  }
  if (templateId.endsWith("-dub")) return { ...voicePayload, sourceVolume: values.sourceVolume };
  if (templateId.endsWith("-voice")) return voicePayload;
  if (templateId.endsWith("-translation")) return translationPayload;
  if (templateId.endsWith("-transcription")) return transcriptPayload;
  if (templateId.endsWith("-intake")) return { templateId, ...sourcePayload };
  return { templateId, sourceRoot: values.sourceRoot, languages: values.targetLanguages, voice: values.voice, platforms: values.platforms };
}

async function submitRun(event) {
  event.preventDefault();
  if (!renderReadiness().ready) return;
  const correlationId = crypto.randomUUID();
  state.busy = true;
  setRunControlsBusy(true);
  $("#run-button").textContent = "Creating Graph…";
  renderReadiness();
  try {
    const payload = buildPayload(readDraftValues());
    const create = await api("/api/v1/runs", {
      method: "POST",
      body: JSON.stringify({ ...envelope("CMD-RUN-CREATE", correlationId, payload), contractId: "CMD-RUN-CREATE" }),
    });
    const runId = create.value.runId;
    await api(`/api/v1/runs/${runId}/start`, {
      method: "POST",
      body: JSON.stringify({ ...envelope("CMD-RUN-START", correlationId), contractId: "CMD-RUN-START" }),
    });
    toast("Graph admitted. Its Loops will execute one at a time.");
    state.busy = false;
    setRunControlsBusy(false);
    $("#run-button").textContent = "Create & run Graph";
    await refreshRunList();
    pollRun(runId);
  } catch (error) {
    state.busy = false;
    setRunControlsBusy(false);
    $("#run-button").textContent = "Create & run Graph";
    state.connectionError = error.message;
    toast(error.message, true);
    renderReadiness();
  }
}

function setRunControlsBusy(busy) {
  $("#workflow-goal").disabled = busy;
  $$('input[name="source-kind"]').forEach((input) => { input.disabled = busy; });
}

async function pollRun(runId) {
  clearTimeout(state.pollTimer);
  try {
    const run = await api(`/api/v1/runs/${runId}`);
    state.currentRun = run;
    renderRun(run);
    await refreshRunList();
    if (TERMINAL_STATES.has(run.status)) {
      state.busy = false;
      setRunControlsBusy(false);
      $("#run-button").textContent = "Create & run Graph";
      renderReadiness();
      return;
    }
    state.pollTimer = setTimeout(() => pollRun(runId), 900);
  } catch (error) {
    toast(error.message, true);
    state.pollTimer = setTimeout(() => pollRun(runId), 2500);
  }
}

function renderRun(run) {
  state.currentRun = run;
  renderGraph();
  const steps = run.steps || [];
  const complete = steps.filter((step) => step.status === "COMPLETED").length;
  $("#run-progress").textContent = `${complete} / ${steps.length}`;
  $("#progress-bar").style.width = `${steps.length ? Math.round(complete / steps.length * 100) : 0}%`;
  $("#run-id").textContent = `${run.runId} · ${run.status}`;
  $("#save-state").textContent = `${state.templateId} · ${run.status}`;
  const logs = run.logs || [];
  $("#activity-summary").textContent = `${run.status} · ${logs.length} log entries`;
  $("#log-output").textContent = logs.length
    ? logs.map((row) => `${String(row.sequence).padStart(3, "0")}  ${row.message}`).join("\n")
    : "Run admitted. Waiting for worker output…";
  $("#log-output").scrollTop = $("#log-output").scrollHeight;
}

function toggleActivity() {
  const collapsed = $("#activity-log").classList.toggle("collapsed");
  $("#toggle-activity").textContent = collapsed ? "Show log" : "Hide log";
  $("#toggle-activity").setAttribute("aria-expanded", String(!collapsed));
}

function bindEvents() {
  $("#run-form").addEventListener("submit", submitRun);
  $("#workflow-goal").addEventListener("change", (event) => selectGoal(event.target.value));
  $$('input[name="source-kind"]').forEach((input) => input.addEventListener("change", () => {
    state.sourceKind = input.value;
    applyWorkflow(resolveTemplate(state.catalog, state.goalId, state.sourceKind));
  }));
  $("#run-form").addEventListener("input", renderReadiness);
  $("#run-form").addEventListener("change", renderReadiness);
  $("#reconnect-button").addEventListener("click", reconnect);
  $("#graph-track").addEventListener("click", handleGraphNodeClick);
  $("#zoom-in").addEventListener("click", () => setZoom(nextZoom(state.zoom, "in")));
  $("#zoom-out").addEventListener("click", () => setZoom(nextZoom(state.zoom, "out")));
  $("#fit-graph").addEventListener("click", fitGraph);
  $("#browse-folder").addEventListener("click", openFolderBrowser);
  $("#folder-up").addEventListener("click", () => state.folder?.parent && loadFolder(state.folder.parent));
  $("#choose-folder").addEventListener("click", selectFolder);
  $("#toggle-activity").addEventListener("click", toggleActivity);
  $("#clear-view").addEventListener("click", () => { $("#log-output").textContent = "View cleared. Durable logs remain stored."; });
  $("#access-button").addEventListener("click", () => $("#access-dialog").showModal());
  $("#access-form").addEventListener("submit", saveAccess);
  $("#clear-access").addEventListener("click", clearAccess);
}

async function bootstrap() {
  bootstrapAccess();
  bindEvents();
  renderGraph();
  renderReadiness();
  await reconnect();
}

bootstrap();
