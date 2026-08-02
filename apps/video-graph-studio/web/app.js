import {
  buildCampaignPayload,
  campaignCounts,
  campaignReadiness,
  filterCreatorItems,
  selectVisibleIds,
} from "./creator-workspace-model.mjs";

const TERMINAL_STATES = new Set(["COMPLETED", "FAILED", "CANCELLED"]);
const STAGES = ["creator", "videos", "languages", "destinations", "review", "activity"];
const PLATFORM_POLICY = {
  youtube: {label: "YouTube", status: "READY_PRIVATE", copy: "Private upload after confirmation"},
  bilibili: {label: "Bilibili", status: "PLAN_ONLY", copy: "Plan is saved; upload adapter pending"},
  douyin: {label: "Douyin", status: "PLAN_ONLY", copy: "Plan is saved; upload adapter pending"},
  tiktok: {label: "TikTok", status: "PLAN_ONLY", copy: "Plan is saved; upload adapter pending"},
};
const SUBTITLE_COPY = {
  SOURCE_AVAILABLE: "Source subtitles",
  SOURCE_MISSING: "ASR required",
  UNKNOWN_ASR: "Checked after download",
};
const STEP_COPY = {
  "select-creator-videos": ["Select exact videos", "Creator Selection"],
  "verify-selection": ["Verify selection", "Creator Selection"],
  "localize-creator-batch": ["Download · transcribe · translate · voice · compose", "Creator Batch"],
  "verify-creator-batch": ["Verify every localized video", "Creator Batch"],
  "discover-creator": ["Discover creator videos", "Creator Discovery"],
  "verify-creator": ["Verify creator catalog", "Creator Discovery"],
};

const state = {
  stage: "creator", contracts: null, creatorRunId: null, catalog: null,
  selectedVideoIds: [], languages: [], selectedLanguages: [], voices: {}, destinations: {},
  providers: [], translationProvider: null, sourceLanguage: "auto", asrModel: "small",
  asrDevice: "auto", asrComputeType: "default", sourceVolume: 0.12,
  currentRun: null, polling: false, accessRequired: false, workspaceId: "",
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, (character) => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"})[character]);

async function api(path, options = {}) {
  const token = sessionStorage.getItem("videoGraph.accessToken");
  const workspaceId = sessionStorage.getItem("videoGraph.workspaceId");
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? {Authorization: `Bearer ${token}`} : {}),
      ...(workspaceId ? {"X-Workspace-Id": workspaceId} : {}),
      ...(options.headers || {}),
    },
  });
  let body = {};
  try { body = await response.json(); } catch { /* bounded below */ }
  if (!response.ok) {
    const error = new Error(body.detail || body.resultClass || `HTTP ${response.status}`);
    error.body = body; error.status = response.status; throw error;
  }
  return body;
}

function envelope(contractId, correlationId, payload = {}) {
  if (!state.contracts?.commands?.[contractId]) throw new Error(`Unsupported command: ${contractId}`);
  return {contractId, contractVersion: state.contracts.contractVersion, operationId: crypto.randomUUID(), correlationId, payload};
}

function toast(message, error = false) {
  const element = $("#toast"); element.textContent = message;
  element.className = error ? "visible error" : "visible";
  clearTimeout(element._timer); element._timer = setTimeout(() => { element.className = ""; }, 3600);
}

function bootstrapAccess() {
  const fragment = new URLSearchParams(location.hash.slice(1));
  if (fragment.get("access_token") && fragment.get("workspace")) {
    sessionStorage.setItem("videoGraph.accessToken", fragment.get("access_token"));
    sessionStorage.setItem("videoGraph.workspaceId", fragment.get("workspace"));
    history.replaceState(null, "", `${location.pathname}${location.search}`);
  }
}

async function loadContracts() {
  const response = await api("/api/v1/contracts");
  const bundle = response.value?.bundle;
  if (!bundle?.commands?.["CMD-RUN-CREATE"] || !bundle?.commands?.["CMD-RUN-START"]) throw new Error("Contract unavailable");
  state.contracts = bundle;
}

async function loadInitialData() {
  const [health, languageResponse, providerResponse, runResponse] = await Promise.all([
    api("/api/v1/health"), api("/api/v1/languages"), api("/api/v1/translation-providers"), api("/api/v1/runs"),
  ]);
  state.accessRequired = health.accessRequired === true;
  state.workspaceId = health.workspaceId || sessionStorage.getItem("videoGraph.workspaceId") || "";
  state.languages = languageResponse.languages || [];
  state.providers = providerResponse.providers || [];
  state.translationProvider = state.providers.find((provider) => provider.id === "nllb") || state.providers[0] || null;
  for (const language of state.languages) state.voices[language.locale] = language.defaultVoice;
  const recentCreator = (runResponse.runs || []).find((run) => run.status === "COMPLETED" && run.graph?.graphId === "creator-profile");
  if (recentCreator) {
    try {
      state.creatorRunId = recentCreator.runId;
      state.catalog = await api(`/api/v1/runs/${recentCreator.runId}/creator-catalog`);
      state.currentRun = recentCreator;
      $("#project-name").textContent = state.catalog.creator.name || state.catalog.creator.id || "Creator campaign";
      renderCreatorResult();
    } catch { state.creatorRunId = null; state.catalog = null; }
  }
  renderConnection(true); renderProviders(); renderLanguages(); renderAll();
}

function renderConnection(ready, detail = "") {
  const pill = $("#health-pill"); pill.classList.toggle("ready", ready);
  pill.querySelector("span").textContent = ready ? "Studio ready" : detail || "Unavailable";
  const access = $("#access-button"); access.hidden = !state.accessRequired;
  access.textContent = sessionStorage.getItem("videoGraph.accessToken") ? state.workspaceId : "Access required";
}

function renderCreatorResult() {
  if (!state.catalog) return;
  $("#creator-result").className = "empty-card creator-loaded";
  $("#creator-result").innerHTML = `<span class="empty-icon">✓</span><div><strong>${escapeHtml(state.catalog.creator.name || "Creator catalog")}</strong><p>${state.catalog.itemCount} verified video(s) · ${escapeHtml(state.catalog.platform)} · no media downloaded</p></div>`;
}

function showStage(stage) {
  if (!STAGES.includes(stage)) return;
  state.stage = stage;
  $$(".stage-panel").forEach((panel) => { panel.hidden = panel.dataset.stage !== stage; panel.classList.toggle("active", panel.dataset.stage === stage); });
  $$(".stage-link").forEach((button) => button.classList.toggle("active", button.dataset.stage === stage));
  const index = STAGES.indexOf(stage);
  $("#rail-progress").textContent = `${index + 1} of ${STAGES.length}`;
  $("#previous-stage").disabled = index === 0;
  $("#next-stage").textContent = index === STAGES.length - 1 ? "Review again ↑" : "Continue →";
  renderAll(); window.scrollTo({top: 0, behavior: "smooth"});
}

function markStages() {
  const done = {
    creator: Boolean(state.catalog), videos: state.selectedVideoIds.length > 0,
    languages: state.selectedLanguages.length > 0,
    destinations: state.selectedLanguages.length > 0 && state.selectedLanguages.every((locale) => state.destinations[locale]?.length),
    review: Boolean(state.currentRun), activity: state.currentRun && TERMINAL_STATES.has(state.currentRun.status),
  };
  $$(".stage-link").forEach((button) => button.classList.toggle("done", Boolean(done[button.dataset.stage])));
  const hints = {
    creator: state.catalog ? `${state.catalog.itemCount} videos discovered.` : "Discover a creator account to continue.",
    videos: `${state.selectedVideoIds.length} video(s) selected.`, languages: `${state.selectedLanguages.length} language(s) selected.`,
    destinations: "Map every language to at least one platform.", review: "Resolve every preflight item before starting.", activity: "Completed work remains checkpointed.",
  };
  $("#footer-hint").textContent = hints[state.stage];
}

async function createAndStart(payload, correlationId) {
  const created = await api("/api/v1/runs", {method: "POST", body: JSON.stringify(envelope("CMD-RUN-CREATE", correlationId, payload))});
  const runId = created.value.runId;
  await api(`/api/v1/runs/${runId}/start`, {method: "POST", body: JSON.stringify(envelope("CMD-RUN-START", correlationId))});
  return runId;
}

async function pollRun(runId, onUpdate) {
  state.polling = true;
  while (state.polling) {
    const run = await api(`/api/v1/runs/${runId}`); onUpdate(run);
    if (TERMINAL_STATES.has(run.status)) return run;
    await new Promise((resolve) => setTimeout(resolve, 800));
  }
  throw new Error("Polling stopped");
}

async function discoverCreator() {
  const sourceUrl = $("#creator-url").value.trim();
  if (!sourceUrl) return toast("Paste a creator account URL first.", true);
  const button = $("#discover-creator"); button.disabled = true; button.textContent = "Discovering…";
  try {
    const payload = {templateId: "creator-profile", sourceUrl, maxItems: Number($("#creator-max-items").value || 0)};
    const authenticationFile = $("#authentication-file").value.trim();
    if (authenticationFile) payload.authenticationFile = authenticationFile;
    const runId = await createAndStart(payload, `creator-${Date.now()}`);
    state.creatorRunId = runId;
    const run = await pollRun(runId, (value) => { state.currentRun = value; renderActivity(); });
    if (run.status !== "COMPLETED") throw new Error(run.steps.find((step) => step.error)?.error || `Discovery ${run.status.toLowerCase()}`);
    state.catalog = await api(`/api/v1/runs/${runId}/creator-catalog`);
    state.selectedVideoIds = [];
    $("#project-name").textContent = state.catalog.creator.name || state.catalog.creator.id || "Creator campaign";
    renderCreatorResult();
    renderCatalog(); markStages(); toast(`Discovered ${state.catalog.itemCount} videos.`); showStage("videos");
  } catch (error) { toast(error.message, true); }
  finally { button.disabled = false; button.textContent = "Discover videos"; }
}

function renderCatalog() {
  const root = $("#video-catalog");
  const items = filterCreatorItems(state.catalog?.items || [], $("#video-search").value);
  $("#catalog-count").textContent = `${items.length} visible / ${state.catalog?.itemCount || 0} total`;
  $("#selected-video-count").textContent = state.selectedVideoIds.length;
  if (!state.catalog) { root.innerHTML = '<div class="empty-card"><span class="empty-icon">□</span><div><strong>Discover a creator first</strong><p>The verified video catalog will appear here.</p></div></div>'; return; }
  if (!items.length) { root.innerHTML = '<div class="empty-card"><span class="empty-icon">⌕</span><div><strong>No matching videos</strong><p>Clear the search to show the full account.</p></div></div>'; return; }
  const selected = new Set(state.selectedVideoIds);
  root.innerHTML = items.map((item) => {
    const subtitle = SUBTITLE_COPY[item.subtitleStatus] || SUBTITLE_COPY.UNKNOWN_ASR;
    const published = item.publishedAt ? new Date(item.publishedAt * 1000).toLocaleDateString() : "Date unavailable";
    return `<label class="video-card ${selected.has(item.id) ? "selected" : ""}"><input type="checkbox" data-video-id="${escapeHtml(item.id)}" ${selected.has(item.id) ? "checked" : ""}><div><strong>${escapeHtml(item.title)}</strong><div class="video-meta"><span>${escapeHtml(published)} · ${escapeHtml(item.id)}</span><span class="subtitle-badge">${escapeHtml(subtitle)}</span></div></div></label>`;
  }).join("");
}

function renderProviders() {
  const select = $("#translation-provider");
  select.innerHTML = state.providers.map((provider) => `<option value="${provider.id}">${escapeHtml(provider.name)}${provider.ready ? "" : " · setup required"}</option>`).join("");
  if (state.translationProvider) select.value = state.translationProvider.id;
  const provider = state.translationProvider;
  if (!provider) return;
  $("#provider-detail").innerHTML = `<strong class="${provider.ready ? "provider-ready" : "provider-missing"}">${provider.ready ? "Ready" : "Setup required"} · ${escapeHtml(provider.defaultModel)}</strong><p>${provider.id === "nllb" ? "Runs locally and offline after the model is installed." : "Quality-first cloud translation. Set DEEPSEEK_API_KEY before launching Studio; the key is never stored in a run."}</p>`;
}

function renderLanguages() {
  const query = $("#language-search").value.trim().toLocaleLowerCase();
  const rows = state.languages.filter((row) => !query || `${row.name} ${row.locale}`.toLocaleLowerCase().includes(query));
  const selected = new Set(state.selectedLanguages);
  $("#selected-language-count").textContent = state.selectedLanguages.length;
  $("#language-list").innerHTML = rows.map((row) => `<article class="language-card ${selected.has(row.locale) ? "selected" : ""}"><label class="language-head"><input type="checkbox" data-language="${row.locale}" ${selected.has(row.locale) ? "checked" : ""}><strong>${escapeHtml(row.name)}</strong><code>${row.locale}</code></label><div class="voice-row"><label>Edge voice</label><input data-voice="${row.locale}" value="${escapeHtml(state.voices[row.locale] || row.defaultVoice)}" ${selected.has(row.locale) ? "" : "disabled"}></div></article>`).join("");
}

function renderDestinations() {
  const root = $("#destination-matrix");
  if (!state.selectedLanguages.length) { root.innerHTML = '<div class="empty-card"><span class="empty-icon">↗</span><div><strong>Select languages first</strong><p>One destination row will be created for each selected language.</p></div></div>'; return; }
  const languageMap = Object.fromEntries(state.languages.map((row) => [row.locale, row]));
  root.innerHTML = state.selectedLanguages.map((locale) => {
    const existing = Object.fromEntries((state.destinations[locale] || []).map((row) => [row.platform, row]));
    const platforms = Object.entries(PLATFORM_POLICY).map(([id, policy]) => {
      const target = existing[id];
      return `<div class="platform-card ${target ? "selected" : ""}"><header><input type="checkbox" data-destination-platform="${id}" data-locale="${locale}" ${target ? "checked" : ""}><strong>${policy.label}</strong><small class="${policy.status === "READY_PRIVATE" ? "ready" : ""}">${policy.status}</small></header><input type="text" data-destination-account="${id}" data-locale="${locale}" value="${escapeHtml(target?.account || "")}" placeholder="Account label"><p>${policy.copy}</p></div>`;
    }).join("");
    return `<section class="destination-row"><header><h3>${escapeHtml(languageMap[locale]?.name || locale)} <code>${locale}</code></h3><span>${(state.destinations[locale] || []).length} route(s)</span></header><div class="platform-options">${platforms}</div></section>`;
  }).join("");
}

function renderReview() {
  const counts = campaignCounts(state.selectedVideoIds, state.selectedLanguages, state.destinations);
  $("#review-videos").textContent = counts.videos; $("#review-localized").textContent = counts.localizedVideos; $("#review-publications").textContent = counts.publicationJobs;
  const provider = state.translationProvider?.name || "Not selected";
  $("#review-summary").innerHTML = `<div class="summary-section"><span>Creator</span><strong>${escapeHtml(state.catalog?.creator?.name || "Not discovered")}</strong><p>${state.catalog?.itemCount || 0} catalog videos · ${state.selectedVideoIds.length} selected</p></div><div class="summary-section"><span>Processing</span><strong>${escapeHtml(provider)}</strong><p>${escapeHtml(state.sourceLanguage)} speech · ${escapeHtml(state.asrModel)} ASR · source audio ${Math.round(state.sourceVolume * 100)}%</p></div><div class="summary-section"><span>Languages</span><strong>${state.selectedLanguages.map(escapeHtml).join(" · ") || "None"}</strong><p>One Edge voice and subtitle track per language</p></div><div class="summary-section"><span>Execution boundary</span><strong>Localization runs now; publication routes remain explicit</strong><p>YouTube private-ready; other platforms plan-only until adapters are verified.</p></div>`;
  const readiness = campaignReadiness(state);
  $("#readiness-list").innerHTML = readiness.ready ? '<li class="ready">All required campaign facts are ready</li>' : readiness.missing.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
  $("#start-campaign").disabled = !readiness.ready || Boolean(state.currentRun && !TERMINAL_STATES.has(state.currentRun.status));
}

function renderActivity() {
  const run = state.currentRun;
  $("#active-run-title").textContent = run ? (run.graph.graphId === "creator-profile" ? "Creator discovery" : "Creator localization campaign") : "No active campaign";
  $("#active-run-id").textContent = run?.runId || "—"; $("#run-status").textContent = run?.status || "NOT STARTED";
  if (!run) { $("#activity-timeline").innerHTML = '<div class="empty-card"><span class="empty-icon">○</span><div><strong>No run yet</strong><p>Campaign steps will appear here.</p></div></div>'; return; }
  $("#activity-timeline").innerHTML = run.steps.map((step, index) => {
    const [title, owner] = STEP_COPY[step.nodeId] || [step.nodeId, "Capability owner"];
    return `<div class="timeline-step ${step.status.toLocaleLowerCase()}"><i>${step.status === "COMPLETED" ? "✓" : index + 1}</i><div><strong>${escapeHtml(title)}</strong><small>${escapeHtml(owner)}${step.error ? ` · ${escapeHtml(step.error)}` : ""}</small></div><b>${step.status}</b></div>`;
  }).join("");
  $("#log-output").textContent = run.logs?.length ? run.logs.map((row) => `${String(row.sequence).padStart(3,"0")}  ${row.message}`).join("\n") : "Waiting for the first committed log entry…";
  $("#save-state").textContent = `Run ${run.status.toLocaleLowerCase()} · ${run.steps.filter((step) => step.status === "COMPLETED").length}/${run.steps.length} steps`;
}

function renderAll() { renderCatalog(); renderLanguages(); renderDestinations(); renderReview(); renderActivity(); markStages(); }

async function startCampaign() {
  const readiness = campaignReadiness(state); if (!readiness.ready) return toast(readiness.missing[0], true);
  const button = $("#start-campaign"); button.disabled = true; button.textContent = "Starting…";
  try {
    const runId = await createAndStart(buildCampaignPayload(state), `campaign-${Date.now()}`);
    showStage("activity");
    const run = await pollRun(runId, (value) => { state.currentRun = value; renderActivity(); markStages(); });
    state.currentRun = run; renderAll();
    toast(run.status === "COMPLETED" ? "Campaign completed." : `Campaign ${run.status.toLocaleLowerCase()}.`, run.status !== "COMPLETED");
  } catch (error) { toast(error.message, true); }
  finally { button.textContent = "Start campaign"; renderReview(); }
}

function bindEvents() {
  $$(".stage-link").forEach((button) => button.addEventListener("click", () => showStage(button.dataset.stage)));
  $("#previous-stage").addEventListener("click", () => showStage(STAGES[Math.max(0, STAGES.indexOf(state.stage) - 1)]));
  $("#next-stage").addEventListener("click", () => showStage(STAGES[(STAGES.indexOf(state.stage) + 1) % STAGES.length]));
  $("#discover-creator").addEventListener("click", discoverCreator);
  $("#video-search").addEventListener("input", renderCatalog);
  $("#select-all-videos").addEventListener("click", () => { state.selectedVideoIds = selectVisibleIds(state.selectedVideoIds, filterCreatorItems(state.catalog?.items || [], $("#video-search").value)); renderAll(); });
  $("#clear-videos").addEventListener("click", () => { state.selectedVideoIds = []; renderAll(); });
  $("#video-catalog").addEventListener("change", (event) => {
    const id = event.target.dataset.videoId; if (!id) return;
    const selected = new Set(state.selectedVideoIds); event.target.checked ? selected.add(id) : selected.delete(id);
    state.selectedVideoIds = [...selected]; renderAll();
  });
  $("#language-search").addEventListener("input", renderLanguages);
  $("#select-common-languages").addEventListener("click", () => { state.selectedLanguages = state.languages.filter((row) => ["ru-RU","en-US"].includes(row.locale)).map((row) => row.locale); renderAll(); });
  $("#clear-languages").addEventListener("click", () => { state.selectedLanguages = []; state.destinations = {}; renderAll(); });
  $("#translation-provider").addEventListener("change", (event) => { state.translationProvider = state.providers.find((provider) => provider.id === event.target.value); renderProviders(); renderReview(); });
  $("#language-list").addEventListener("change", (event) => {
    if (event.target.dataset.language) {
      const locale = event.target.dataset.language; const selected = new Set(state.selectedLanguages);
      event.target.checked ? selected.add(locale) : selected.delete(locale); state.selectedLanguages = state.languages.map((row) => row.locale).filter((value) => selected.has(value));
      if (!event.target.checked) delete state.destinations[locale]; renderAll();
    } else if (event.target.dataset.voice) { state.voices[event.target.dataset.voice] = event.target.value; renderReview(); }
  });
  $("#destination-matrix").addEventListener("change", (event) => {
    const locale = event.target.dataset.locale; const platform = event.target.dataset.destinationPlatform || event.target.dataset.destinationAccount; if (!locale || !platform) return;
    const targets = [...(state.destinations[locale] || [])]; const index = targets.findIndex((row) => row.platform === platform);
    if (event.target.dataset.destinationPlatform) {
      if (event.target.checked && index < 0) targets.push({platform, account: ""}); else if (!event.target.checked && index >= 0) targets.splice(index, 1);
    } else if (index >= 0) targets[index] = {...targets[index], account: event.target.value};
    state.destinations[locale] = targets; renderAll();
  });
  $("#destination-matrix").addEventListener("input", (event) => {
    const locale = event.target.dataset.locale; const platform = event.target.dataset.destinationAccount;
    if (!locale || !platform) return;
    const targets = [...(state.destinations[locale] || [])]; const index = targets.findIndex((row) => row.platform === platform);
    if (index >= 0) targets[index] = {...targets[index], account: event.target.value};
    state.destinations[locale] = targets; renderReview(); markStages();
  });
  $("#source-language").addEventListener("change", (event) => { state.sourceLanguage = event.target.value; renderReview(); });
  $("#asr-model").addEventListener("change", (event) => { state.asrModel = event.target.value; renderReview(); });
  $("#start-campaign").addEventListener("click", startCampaign);
  $("#clear-log").addEventListener("click", () => { $("#log-output").textContent = "View cleared. Durable logs remain attached to the run."; });
  $("#access-button").addEventListener("click", () => $("#access-dialog").showModal());
  $("#access-form").addEventListener("submit", () => { sessionStorage.setItem("videoGraph.workspaceId", $("#access-workspace").value.trim()); sessionStorage.setItem("videoGraph.accessToken", $("#access-token").value); location.reload(); });
  $("#clear-access").addEventListener("click", () => { sessionStorage.removeItem("videoGraph.workspaceId"); sessionStorage.removeItem("videoGraph.accessToken"); location.reload(); });
}

async function bootstrap() {
  bootstrapAccess(); bindEvents(); renderAll();
  try { await loadContracts(); await loadInitialData(); }
  catch (error) { renderConnection(false, error.message); toast(error.message, true); }
}

bootstrap();
