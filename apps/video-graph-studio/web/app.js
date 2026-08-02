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
  "folder-transcription": {
    source: { title: "Folder intake", description: "Discover local media and commit a reusable source manifest.", owner: "source-intake", relationship: "Command", delivery: "DOMAIN_VERIFIED" },
    localize: { title: "Serial transcription", description: "Transcribe one verified media item at a time with resumable checkpoints.", owner: "transcription", relationship: "Command", delivery: "DOMAIN_VERIFIED" },
    verify: { title: "Verify transcripts", description: "Check source, JSON and SRT fingerprints before continuation.", owner: "transcription", relationship: "Policy", delivery: "DOMAIN_VERIFIED" },
  },
  "url-transcription": {
    source: { title: "URL intake", description: "Download one supported social video and commit its source manifest.", owner: "source-intake", relationship: "Command", delivery: "DOMAIN_VERIFIED" },
    localize: { title: "Serial transcription", description: "Transcribe one verified media item at a time with resumable checkpoints.", owner: "transcription", relationship: "Command", delivery: "DOMAIN_VERIFIED" },
    verify: { title: "Verify transcripts", description: "Check source, JSON and SRT fingerprints before continuation.", owner: "transcription", relationship: "Policy", delivery: "DOMAIN_VERIFIED" },
  },
  "folder-translation": {
    source: { title: "Folder intake", description: "Discover local media and preserve a verified source fact.", owner: "source-intake", relationship: "Command", delivery: "DOMAIN_VERIFIED" },
    localize: { title: "Serial translation", description: "Transcribe, verify and translate every language/media work item sequentially.", owner: "translation", relationship: "Command", delivery: "DOMAIN_VERIFIED" },
    verify: { title: "Verify translations", description: "Require exact language/media coverage and matching JSON/SRT fingerprints.", owner: "translation", relationship: "Policy", delivery: "DOMAIN_VERIFIED" },
  },
  "url-translation": {
    source: { title: "URL intake", description: "Download one supported social video and preserve a verified source fact.", owner: "source-intake", relationship: "Command", delivery: "DOMAIN_VERIFIED" },
    localize: { title: "Serial translation", description: "Transcribe, verify and translate every language/media work item sequentially.", owner: "translation", relationship: "Command", delivery: "DOMAIN_VERIFIED" },
    verify: { title: "Verify translations", description: "Require exact language/media coverage and matching JSON/SRT fingerprints.", owner: "translation", relationship: "Policy", delivery: "DOMAIN_VERIFIED" },
  },
  "folder-voice": {
    source: { title: "Folder intake", description: "Discover local media and preserve a verified source fact.", owner: "source-intake", relationship: "Command", delivery: "DOMAIN_VERIFIED" },
    localize: { title: "Serial voice rendering", description: "Translate and render one Edge TTS clip per segment with checkpoints.", owner: "voice-rendering", relationship: "Command", delivery: "DOMAIN_VERIFIED" },
    verify: { title: "Verify voice clips", description: "Check every MP3 hash, size and measured duration.", owner: "voice-rendering", relationship: "Policy", delivery: "DOMAIN_VERIFIED" },
  },
  "url-voice": {
    source: { title: "URL intake", description: "Download one supported social video and preserve a verified source fact.", owner: "source-intake", relationship: "Command", delivery: "DOMAIN_VERIFIED" },
    localize: { title: "Serial voice rendering", description: "Translate and render one Edge TTS clip per segment with checkpoints.", owner: "voice-rendering", relationship: "Command", delivery: "DOMAIN_VERIFIED" },
    verify: { title: "Verify voice clips", description: "Check every MP3 hash, size and measured duration.", owner: "voice-rendering", relationship: "Policy", delivery: "DOMAIN_VERIFIED" },
  },
  "folder-dub": {
    source: { title: "Folder intake", description: "Discover local media and preserve a verified source fact.", owner: "source-intake", relationship: "Command", delivery: "DOMAIN_VERIFIED" },
    localize: { title: "Localized video composition", description: "Compose translated voice, quiet source audio and burned subtitles into H.264/AAC MP4.", owner: "localization", relationship: "Command", delivery: "PLATFORM_INTEGRATED" },
    verify: { title: "Verify localized videos", description: "Require exact language/media coverage and matching derivative fingerprints.", owner: "localization", relationship: "Policy", delivery: "PLATFORM_INTEGRATED" },
  },
  "url-dub": {
    source: { title: "URL intake", description: "Download social media and preserve a verified source fact.", owner: "source-intake", relationship: "Command", delivery: "DOMAIN_VERIFIED" },
    localize: { title: "Localized video composition", description: "Compose translated voice, quiet source audio and burned subtitles into H.264/AAC MP4.", owner: "localization", relationship: "Command", delivery: "PLATFORM_INTEGRATED" },
    verify: { title: "Verify localized videos", description: "Require exact language/media coverage and matching derivative fingerprints.", owner: "localization", relationship: "Policy", delivery: "PLATFORM_INTEGRATED" },
  },
  "creator-profile": {
    source: { title: "Creator profile", description: "Accept one supported creator or channel URL and an optional local authentication file.", owner: "creator-discovery", relationship: "Input", delivery: "PLATFORM_INTEGRATED" },
    localize: { title: "Enumerate profile", description: "Page serially, canonicalize URLs, deduplicate IDs and checkpoint the cursor.", owner: "creator-discovery", relationship: "Command", delivery: "PLATFORM_INTEGRATED" },
    verify: { title: "Verify creator manifest", description: "Require ordered unique URLs and a matching manifest fingerprint.", owner: "creator-discovery", relationship: "Policy", delivery: "PLATFORM_INTEGRATED" },
  },
  "publication-plan": {
    source: { title: "Finished video", description: "Select one local derivative plus editable metadata and target accounts.", owner: "publication", relationship: "Input", delivery: "DOMAIN_VERIFIED" },
    localize: { title: "Build publication plan", description: "Fingerprint inputs and create private/draft target jobs without contacting platforms.", owner: "publication", relationship: "Command", delivery: "DOMAIN_VERIFIED" },
    verify: { title: "Verify publication plan", description: "Check video, metadata, job coverage and immutable plan fingerprint.", owner: "publication", relationship: "Policy", delivery: "DOMAIN_VERIFIED" },
  },
  "publication-execute": {
    source: { title: "Verified plan run", description: "Resolve one completed private YouTube plan from this workspace.", owner: "video-graph-studio", relationship: "Fact", delivery: "DOMAIN_VERIFIED" },
    localize: { title: "Execute guarded publication", description: "Require the exact plan SHA and ask Publication to compose Vault and Platform I/O.", owner: "publication", relationship: "Command", delivery: "DOMAIN_VERIFIED" },
    verify: { title: "Verify platform receipt", description: "Require a fingerprinted manifest and non-empty external publication identity.", owner: "publication", relationship: "Policy", delivery: "DOMAIN_VERIFIED" },
  },
  "youtube-connect": {
    source: { title: "Google desktop client", description: "Select one local Google desktop OAuth client JSON without copying its secret into Studio.", owner: "youtube-oauth-bootstrap", relationship: "Input", delivery: "DOMAIN_VERIFIED" },
    localize: { title: "Connect YouTube", description: "Open the system browser, validate loopback state and PKCE, then store refresh credentials through Vault.", owner: "youtube-oauth-bootstrap", relationship: "Command", delivery: "DOMAIN_VERIFIED" },
    verify: { title: "Verify credential", description: "Ask Credential Vault to confirm one active provider-bound YouTube credential.", owner: "credential-vault", relationship: "Query", delivery: "DOMAIN_VERIFIED" },
  },
};

const state = { currentRun: null, recentRuns: [], pollTimer: null, folder: null, selectedNode: "localize", templateId: "prepared-localization", accessRequired: false, workspaceId: sessionStorage.getItem("videoGraph.workspaceId") || "", contracts: null };
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
  const body = await response.json();
  if (!response.ok) {
    const error = new Error(body.detail || body.resultClass || `HTTP ${response.status}`);
    error.body = body;
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
    state.accessRequired = health.accessRequired === true;
    state.workspaceId = health.workspaceId || sessionStorage.getItem("videoGraph.workspaceId") || "";
    const accessButton = $("#access-button");
    accessButton.hidden = !state.accessRequired;
    $("#access-workspace").value = state.workspaceId;
    const hasAccess = !state.accessRequired || Boolean(sessionStorage.getItem("videoGraph.accessToken")) && sessionStorage.getItem("videoGraph.workspaceId") === state.workspaceId;
    accessButton.classList.toggle("required", !hasAccess);
    accessButton.textContent = hasAccess ? state.workspaceId : "Access required";
    if (!hasAccess) {
      pill.classList.remove("ready");
      pill.lastChild.textContent = " Access required";
      return;
    }
    pill.classList.add("ready");
    const queued = health.queuedRuns ? ` / ${health.queuedRuns} queued` : "";
    pill.lastChild.textContent = health.activeWorkers ? ` 1 worker active${queued}` : health.queuedRuns ? ` ${health.queuedRuns} queued` : " System ready";
    await refreshRunList();
  } catch (error) {
    const denied = error.body?.resultClass === "REJECTED_UNAUTHORIZED" || error.body?.resultClass === "REJECTED_WORKSPACE";
    $("#health-pill").classList.remove("ready");
    $("#health-pill").lastChild.textContent = denied ? " Access denied" : " Offline";
    if (denied) {
      $("#access-button").classList.add("required");
      $("#access-button").textContent = "Access denied";
    }
  }
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

function saveAccess(event) {
  event.preventDefault();
  const workspaceId = $("#access-workspace").value.trim();
  const token = $("#access-token").value.trim();
  if (!workspaceId || !token) return;
  sessionStorage.setItem("videoGraph.workspaceId", workspaceId);
  sessionStorage.setItem("videoGraph.accessToken", token);
  $("#access-token").value = "";
  $("#access-dialog").close();
  checkHealth();
}

function clearAccess() {
  sessionStorage.removeItem("videoGraph.workspaceId");
  sessionStorage.removeItem("videoGraph.accessToken");
  $("#access-token").value = "";
  $("#access-dialog").close();
  checkHealth();
}

function templateForRun(run) {
  return run.graph.graphId === "prepared-folder-edge" ? "prepared-localization" : run.graph.graphId;
}

async function refreshRunList() {
  const [runsResponse, queue] = await Promise.all([api("/api/v1/runs"), api("/api/v1/queue")]);
  state.recentRuns = runsResponse.runs;
  if (state.templateId === "publication-execute") populateLatestPublicationPlan();
  $("#queue-count").textContent = `${queue.queuedRuns} waiting`;
  const list = $("#run-list");
  list.replaceChildren();
  runsResponse.runs.slice(0, 8).forEach((run) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `run-row${state.currentRun?.runId === run.runId ? " selected" : ""}`;
    const title = document.createElement("strong");
    title.textContent = run.graph.graphId;
    const status = document.createElement("b");
    status.className = run.status.toLowerCase();
    status.textContent = run.status;
    const identity = document.createElement("small");
    identity.textContent = run.runId.slice(0, 13);
    button.append(title, status, identity);
    button.addEventListener("click", () => {
      const templateId = templateForRun(run);
      if (TEMPLATE_NODE_COPY[templateId]) selectTemplate(templateId);
      state.currentRun = run;
      renderRun(run);
      if (!TERMINAL_STATES.has(run.status)) pollRun(run.runId);
    });
    list.append(button);
  });
  if (!runsResponse.runs.length) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = "No runs yet.";
    list.append(empty);
  }
}

function populateLatestPublicationPlan() {
  const planRun = state.recentRuns.find((run) => run.status === "COMPLETED" && run.graph?.graphId === "publication-plan" && run.parameters?.targetPlatforms?.length === 1 && run.parameters.targetPlatforms[0] === "youtube" && run.parameters?.credentialIds?.youtube);
  const fact = planRun?.steps?.find((step) => step.nodeId === "plan-publication" && step.status === "COMPLETED")?.result;
  if (!planRun || !fact?.manifestSha256) return;
  if (!$("#publication-plan-run-id").value) $("#publication-plan-run-id").value = planRun.runId;
  if (!$("#publication-confirmation").value) $("#publication-confirmation").value = fact.manifestSha256;
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
  const creatorMode = state.templateId === "creator-profile";
  const publicationMode = state.templateId === "publication-plan";
  const publicationExecuteMode = state.templateId === "publication-execute";
  const youtubeConnectMode = state.templateId === "youtube-connect";
  const urlMode = state.templateId.startsWith("url-") || creatorMode;
  const transcriptionMode = state.templateId.endsWith("-transcription");
  const translationMode = state.templateId.endsWith("-translation");
  const voiceMode = state.templateId.endsWith("-voice");
  const dubMode = state.templateId.endsWith("-dub");
  const needsFolder = !urlMode && !publicationMode && !publicationExecuteMode && !youtubeConnectMode;
  if (!publicationMode && !publicationExecuteMode && !youtubeConnectMode && ((needsFolder && !sourceRoot) || (!needsFolder && !sourceUrl))) {
    toast("Choose a source folder or supported social URL.", true);
    return;
  }
  if (state.templateId === "prepared-localization" && (!languages.length || !platforms.length)) {
    toast("Choose a source, language and target.", true);
    return;
  }
  if ((translationMode || voiceMode || dubMode) && !languages.length) {
    toast("Choose at least one target language.", true);
    return;
  }
  const publicationTargets = $$('input[name="publication-target"]:checked').map((item) => item.value);
  if (publicationMode && (!$("#publication-video").value.trim() || !$("#publication-metadata").value.trim() || !$("#publication-account").value.trim() || !publicationTargets.length)) {
    toast("Choose a finished video, metadata, account and target.", true);
    return;
  }
  if (publicationExecuteMode && (!$("#publication-plan-run-id").value.trim() || !$("#publication-confirmation").value.trim() || !$("#credential-vault-path").value.trim())) {
    toast("Choose a completed plan run, its exact SHA-256 and Credential Vault.", true);
    return;
  }
  if (youtubeConnectMode && (!$("#youtube-client-config").value.trim() || !$("#youtube-vault-path").value.trim() || !$("#youtube-credential-id").value.trim() || !$("#youtube-credential-label").value.trim())) {
    toast("Choose the Google desktop client JSON, Credential Vault, credential ID and label.", true);
    return;
  }
  const correlationId = crypto.randomUUID();
  const button = $("#run-button");
  button.disabled = true;
  setRunControlsBusy(true);
  button.innerHTML = "<span>◌</span> Creating…";
  try {
    const sourcePayload = urlMode ? { sourceUrl, maxHeight: 1080 } : { sourceRoot };
    const asrDevice = $("#asr-device").value;
    const transcriptPayload = {
      templateId: state.templateId,
      ...sourcePayload,
      sourceLanguage: $("#source-language").value,
      asrModel: $("#asr-model").value,
      asrDevice,
      asrComputeType: asrDevice === "cpu" ? "int8" : asrDevice === "cuda" ? "float16" : "default",
    };
    const translationPayload = {
      ...transcriptPayload,
      targetLanguages: languages,
      translationModel: "facebook/nllb-200-distilled-600M",
      translationDevice: $("#translation-device").value,
      translationBatchSize: Number($("#translation-batch-size").value),
    };
    const defaultVoices = { "ru-RU": "ru-RU-DmitryNeural", "en-US": "en-US-GuyNeural", "kk-KZ": "kk-KZ-DauletNeural" };
    const voicePayload = { ...translationPayload, targetVoices: Object.fromEntries(languages.map((language) => [language, defaultVoices[language]])) };
    const youtubeCredentialId = $("#publication-credential-id").value.trim();
    const payload = youtubeConnectMode
      ? { templateId: state.templateId, clientConfigPath: $("#youtube-client-config").value.trim(), credentialVaultPath: $("#youtube-vault-path").value.trim(), credentialId: $("#youtube-credential-id").value.trim(), label: $("#youtube-credential-label").value.trim() }
      : publicationMode
      ? { templateId: state.templateId, videoPath: $("#publication-video").value.trim(), metadataPath: $("#publication-metadata").value.trim(), targetPlatforms: publicationTargets, account: $("#publication-account").value.trim(), credentialIds: youtubeCredentialId && publicationTargets.includes("youtube") ? { youtube: youtubeCredentialId } : {}, public: false }
      : publicationExecuteMode
      ? { templateId: state.templateId, planRunId: $("#publication-plan-run-id").value.trim(), confirmation: $("#publication-confirmation").value.trim(), credentialVaultPath: $("#credential-vault-path").value.trim() }
      : creatorMode
      ? { templateId: state.templateId, sourceUrl, maxItems: Number($("#creator-max-items").value), authenticationFile: $("#authentication-file").value.trim() || undefined }
      : dubMode
      ? { ...voicePayload, sourceVolume: 0.12 }
      : voiceMode
      ? voicePayload
      : translationMode
      ? {
          ...translationPayload,
        }
      : transcriptionMode
      ? transcriptPayload
      : state.templateId.endsWith("-intake")
        ? { templateId: state.templateId, ...sourcePayload }
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
    toast("Graph admitted to the durable serial queue.");
    button.disabled = false;
    setRunControlsBusy(false);
    button.innerHTML = "<span>+</span> Queue another graph";
    await checkHealth();
    pollRun(runId);
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
  $("#run-progress").textContent = state.templateId === "prepared-localization" ? "0 / 3" : state.templateId.endsWith("-dub") ? "0 / 10" : state.templateId.endsWith("-voice") ? "0 / 8" : state.templateId.endsWith("-translation") ? "0 / 6" : state.templateId.endsWith("-transcription") ? "0 / 4" : "0 / 2";
  $("#progress-bar").style.width = "0%";
  $("#run-id").textContent = "No active run";
  $("#activity-summary").textContent = "Waiting for a run";
  $("#log-output").textContent = "Choose a source and run the graph. Durable logs will appear here.";
}

function selectTemplate(templateId) {
  state.templateId = templateId;
  const creatorMode = templateId === "creator-profile";
  const publicationMode = templateId === "publication-plan";
  const publicationExecuteMode = templateId === "publication-execute";
  const youtubeConnectMode = templateId === "youtube-connect";
  const publicationAnyMode = publicationMode || publicationExecuteMode;
  const standaloneMode = publicationAnyMode || youtubeConnectMode;
  const urlMode = templateId.startsWith("url-") || creatorMode;
  const transcriptionMode = templateId.endsWith("-transcription");
  const translationMode = templateId.endsWith("-translation");
  const voiceMode = templateId.endsWith("-voice");
  const dubMode = templateId.endsWith("-dub");
  const needsAsr = transcriptionMode || translationMode || voiceMode || dubMode;
  const sourceRoot = $("#source-root");
  const sourceUrl = $("#source-url");
  $("#url-source-field").hidden = !urlMode;
  sourceRoot.closest(".source-field").hidden = urlMode || standaloneMode;
  sourceRoot.required = !urlMode && !standaloneMode;
  sourceUrl.required = urlMode;
  const preparedMode = templateId === "prepared-localization";
  $$(".prepared-only").forEach((element) => {
    element.hidden = !preparedMode;
    element.classList.toggle("control-muted", !preparedMode);
  });
  $("#target-language-controls").hidden = !(preparedMode || translationMode || voiceMode || dubMode);
  $$('input[name="language"]').forEach((input) => {
    input.disabled = preparedMode && input.value !== "ru-RU";
    input.closest("label").classList.toggle("unavailable", input.disabled);
  });
  $("#asr-controls").hidden = !needsAsr;
  $("#translation-controls").hidden = !(translationMode || voiceMode || dubMode);
  $("#creator-controls").hidden = !creatorMode;
  $("#publication-controls").hidden = !publicationMode;
  $("#publication-execution-controls").hidden = !publicationExecuteMode;
  $("#youtube-connect-controls").hidden = !youtubeConnectMode;
  if (publicationExecuteMode) populateLatestPublicationPlan();
  $$('.template-field .choice').forEach((label) => {
    label.classList.toggle("active", label.querySelector("input").value === templateId);
  });
  const copy = templateId === "youtube-connect"
    ? ["Google desktop client", "Local config · secret stays out of Studio", "Connect YouTube", "System browser · state · PKCE · Vault", "Verify credential", "Provider · ACTIVE · upload scope"]
    : templateId === "publication-execute"
    ? ["Verified plan run", "Same workspace · exact SHA-256", "Execute private YouTube upload", "Credential Vault · Platform I/O", "Verify publication receipt", "External ID · manifest fingerprint"]
    : templateId === "publication-plan"
    ? ["Finished video", "Local derivative · editable metadata", "Build publication plan", "Fingerprint only · no upload", "Verify publication plan", "Private/draft jobs · plan SHA-256"]
    : templateId === "creator-profile"
    ? ["Creator profile", "YouTube · Bilibili · Douyin · TikTok", "Enumerate profile", "Serial pages · deduplicated · resumable", "Verify creator manifest", "Canonical URLs · cursor · fingerprint"]
    : templateId === "prepared-localization"
    ? ["Prepared folder", "Validate batch manifest", "Edge localization", "Voice · mix · hard subtitles", "Verify output", "Inspect files and receipts"]
    : templateId === "folder-intake"
      ? ["Local folder", "Resolve an allowed source", "Discover media", "Build deterministic manifest", "Verify source", "Check files and receipt"]
      : templateId === "url-intake"
        ? ["Social URL", "YouTube · Bilibili · Douyin · TikTok", "Download 1080p", "Anonymous first · cookie optional", "Verify source", "Check files and receipt"]
        : templateId === "folder-transcription"
          ? ["Folder intake", "Discover and verify media", "Serial transcription", "Faster Whisper · checkpointed", "Verify transcripts", "JSON · SRT · fingerprints"]
          : templateId === "url-transcription"
            ? ["URL intake", "Download and verify media", "Serial transcription", "Faster Whisper · checkpointed", "Verify transcripts", "JSON · SRT · fingerprints"]
            : dubMode
              ? [urlMode ? "URL intake" : "Folder intake", "Intake · ASR · translation · voice", "Localized video composition", "FFmpeg · voice mix · burned subtitles", "Verify localized videos", "H.264/AAC MP4 · fingerprints"]
            : voiceMode
              ? [urlMode ? "URL intake" : "Folder intake", "Intake · ASR · translation", "Serial voice rendering", "Edge TTS · per segment · resumable", "Verify voice clips", "MP3 · hashes · durations"]
              : [urlMode ? "URL intake" : "Folder intake", "Intake · ASR · verified facts", "Serial translation", "NLLB · multilingual · checkpointed", "Verify translations", "Editable JSON · SRT · fingerprints"];
  ["source-node-title", "source-node-description", "process-node-title", "process-node-description", "output-node-title", "output-node-description"]
    .forEach((id, index) => { $(`#${id}`).textContent = copy[index]; });
  const outputDetails = templateId === "youtube-connect"
    ? ["Vault credential", "Redacted OAuth receipt"]
    : templateId === "publication-execute"
    ? ["Publication Manifest", "External platform ID"]
    : templateId === "publication-plan"
    ? ["JSON plan", "Plan SHA-256"]
    : templateId === "creator-profile"
    ? ["Canonical URLs", "Creator Manifest"]
    : templateId === "prepared-localization"
    ? ["MP4 · H.264", "Local receipt"]
    : dubMode
      ? ["H.264 · AAC", "Localization Manifest"]
    : voiceMode
      ? ["Segment MP3", "Voice Manifest"]
    : translationMode || transcriptionMode
      ? ["JSON · SRT", translationMode ? "Translation Manifest" : "Transcript Manifest"]
      : ["Source Manifest", "SHA-256 receipt"];
  $("#output-format").textContent = outputDetails[0];
  $("#output-evidence").textContent = outputDetails[1];
  const stepIds = templateId === "youtube-connect"
    ? ["", "connect-youtube", "verify-youtube-credential"]
    : templateId === "publication-execute"
    ? ["", "execute-publication", "verify-publication-execution"]
    : templateId === "publication-plan"
    ? ["", "plan-publication", "verify-publication-plan"]
    : templateId === "creator-profile"
    ? ["", "discover-creator", "verify-creator"]
    : templateId === "prepared-localization"
    ? ["source", "localize", "verify"]
    : dubMode
      ? ["intake", "localize-video", "verify-localization"]
    : voiceMode
      ? ["intake", "render-voice", "verify-voice"]
      : translationMode
      ? ["intake", "translate", "verify-translation"]
      : transcriptionMode
      ? ["intake", "transcribe", "verify-transcript"]
      : ["", "intake", "verify"];
  $$(".graph-node").forEach((node, index) => { node.dataset.stepId = stepIds[index]; });
  const paletteCopy = templateId === "youtube-connect"
    ? ["Desktop OAuth client", "Local input", "Connect YouTube", "System-browser consent", "Verify Vault credential", "Provider/status policy"]
    : templateId === "publication-execute"
    ? ["Verified plan run", "Committed fact", "Execute publication", "Guarded command", "Verify receipt", "External identity policy"]
    : templateId === "publication-plan"
    ? ["Finished video", "Local input", "Build publication plan", "No platform contact", "Verify plan", "Confirmation policy"]
    : templateId === "creator-profile"
    ? ["Creator profile", "Remote input", "Enumerate profile", "Serial page loop", "Verify creator manifest", "Coverage policy"]
    : templateId === "prepared-localization"
    ? ["Prepared folder", "Local query", "Edge localization", "Serial adapter", "Verify outputs", "Receipt policy"]
    : templateId === "folder-intake"
      ? ["Local folder", "Local input", "Discover media", "Serial command", "Verify source", "Manifest policy"]
      : templateId === "url-intake"
        ? ["Social URL", "Remote input", "Download 1080p", "Platform adapter", "Verify source", "Manifest policy"]
        : templateId === "folder-transcription"
          ? ["Folder intake", "Source owner", "Transcribe", "Serial ASR loop", "Verify transcript", "Artifact policy"]
          : templateId === "url-transcription"
            ? ["URL intake", "Source owner", "Transcribe", "Serial ASR loop", "Verify transcript", "Artifact policy"]
            : dubMode
              ? [urlMode ? "URL intake" : "Folder intake", "Source owner", "Compose derivatives", "Serial FFmpeg loop", "Verify localized videos", "Localization policy"]
            : voiceMode
              ? [urlMode ? "URL intake" : "Folder intake", "Source owner", "Render voice", "Serial clip loop", "Verify voice", "Audio policy"]
              : [urlMode ? "URL intake" : "Folder intake", "Source owner", "Translate", "Serial language loop", "Verify translation", "Coverage policy"];
  ["palette-source-title", "palette-source-detail", "palette-process-title", "palette-process-detail", "palette-output-title", "palette-output-detail"]
    .forEach((id, index) => { $(`#${id}`).textContent = paletteCopy[index]; });
  $(".workspace-label").textContent = templateId === "youtube-connect"
    ? "Connect YouTube Account"
    : templateId === "publication-execute"
    ? "Guarded Private YouTube Execution"
    : templateId === "publication-plan"
    ? "Guarded Publication Planning"
    : templateId === "creator-profile"
    ? "Creator Profile Discovery"
    : templateId === "prepared-localization"
    ? "Prepared Folder Localization"
    : templateId === "folder-intake"
      ? "Folder Source Intake"
      : templateId === "url-intake"
        ? "Social URL Intake"
        : templateId === "folder-transcription"
          ? "Folder Intake + Transcription"
          : templateId === "url-transcription"
            ? "URL Intake + Transcription"
            : dubMode
              ? `${urlMode ? "URL" : "Folder"} Intake + ASR + Translation + Voice + Dub`
            : voiceMode
              ? `${urlMode ? "URL" : "Folder"} Intake + ASR + Translation + Voice`
              : `${urlMode ? "URL" : "Folder"} Intake + ASR + Translation`;
  $$(".source-preview").forEach((element) => { element.textContent = (youtubeConnectMode ? $("#youtube-client-config").value : publicationExecuteMode ? $("#publication-plan-run-id").value : publicationMode ? $("#publication-video").value : urlMode ? sourceUrl.value : sourceRoot.value) || "Not selected"; });
  resetRunProjection();
  focusNode(state.selectedNode);
}

async function pollRun(runId) {
  clearTimeout(state.pollTimer);
  try {
    const run = await api(`/api/v1/runs/${runId}`);
    state.currentRun = run;
    renderRun(run);
    await refreshRunList();
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
  $("#access-button").addEventListener("click", () => $("#access-dialog").showModal());
  $("#access-form").addEventListener("submit", saveAccess);
  $("#clear-access").addEventListener("click", clearAccess);
  $$(".graph-node").forEach((node) => node.addEventListener("click", () => focusNode(node.dataset.nodeId)));
  $$('[data-focus-node]').forEach((button) => button.addEventListener("click", () => focusNode(button.dataset.focusNode)));
  $("#source-root").addEventListener("input", (event) => $$(".source-preview").forEach((element) => { element.textContent = event.target.value || "Not selected"; }));
  $("#source-url").addEventListener("input", (event) => $$(".source-preview").forEach((element) => { element.textContent = event.target.value || "Not selected"; }));
  $("#publication-video").addEventListener("input", (event) => $$(".source-preview").forEach((element) => { element.textContent = event.target.value || "Not selected"; }));
  $("#publication-plan-run-id").addEventListener("input", (event) => $$(".source-preview").forEach((element) => { element.textContent = event.target.value || "Not selected"; }));
  $("#youtube-client-config").addEventListener("input", (event) => $$(".source-preview").forEach((element) => { element.textContent = event.target.value || "Not selected"; }));
  $$('input[name="template"]').forEach((input) => input.addEventListener("change", () => selectTemplate(input.value)));
}

async function bootstrap() {
  bootstrapAccess();
  bindEvents();
  focusNode("localize");
  selectTemplate("prepared-localization");
  $("#run-button").disabled = true;
  try {
    await loadContracts();
    $("#run-button").disabled = false;
    await checkHealth();
  } catch (error) {
    $("#run-button").disabled = true;
    $("#health-pill").classList.remove("ready");
    $("#health-pill").lastChild.textContent = " Contract unavailable";
    toast(error.message || "Contract unavailable", true);
  }
}

bootstrap();
