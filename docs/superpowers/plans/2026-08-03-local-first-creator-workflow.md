# Local-First Creator Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make complete creator discovery and local folders usable with independently selectable translation, voice, local output, and optional publication policies.

**Architecture:** Preserve Creator Discovery, Creator Selection, Translation, Voice Rendering, Localization, and Publication as independent owners. Extend their public policies only where required, then compose them in Studio. The Studio remains a staged form, not a mutable graph editor.

**Tech Stack:** Python 3.12, stdlib HTTP/JSON, pytest, JavaScript ES modules, Node test runner, PowerShell launchers, Edge TTS, optional Qwen3-TTS runtime, ffmpeg/ffprobe.

## Global Constraints

- Process creator items and voice segments strictly serially.
- A complete local localization is successful with zero publication routes.
- Do not store DeepSeek keys, cookies, or Qwen model data in run payloads.
- Accept filesystem paths only under Studio allowed roots.
- Do not use subagents.

---

### Task 1: Honest source catalogs

**Files:**
- Modify: `tests/video_graph_studio/test_creator_campaign_graph.py`
- Modify: `tests/video_graph_studio/test_api.py`
- Modify: `apps/video-graph-studio/studio/api.py`
- Modify: `apps/video-graph-studio/studio/creator_catalog.py`

**Interfaces:**
- Consumes: verified Creator Manifest facts and an allowed folder path.
- Produces: creator campaign admission that rejects truncated catalogs and `GET /api/v1/folders` rows containing exact local videos.

- [ ] Write a failing API test proving a truncated creator catalog cannot start a creator campaign.
- [ ] Write a failing folder projection test proving exact video names, paths, and byte sizes are returned in deterministic order.
- [ ] Run both focused tests and observe the expected contract failures.
- [ ] Implement the minimal admission and folder projection behavior.
- [ ] Run the focused Studio tests and commit.

### Task 2: Provider-selectable voice rendering

**Files:**
- Modify: `tests/voice_rendering_mvp/test_adapter_cli.py`
- Modify: `tests/voice_rendering_mvp/test_operation.py`
- Modify: `apps/voice-rendering/voice_rendering_app/adapters.py`
- Modify: `apps/voice-rendering/voice_rendering_app/cli.py`
- Modify: `apps/voice-rendering/voice_rendering_app/operation.py`
- Modify: `apps/voice-rendering/run.ps1`
- Modify: `apps/voice-rendering/README.md`
- Modify: `apps/voice-rendering/mvp.json`

**Interfaces:**
- Consumes: `--provider edge|qwen3|original`, exact locale-to-voice policy, and a Translation Manifest.
- Produces: the existing Voice Manifest contract with provider-specific adapter identity and valid audio suffixes.

- [ ] Add failing CLI/adapter tests for explicit provider selection, Qwen preset synthesis, original-audio silence, and provider-specific file suffixes.
- [ ] Run the focused suite and confirm failures are caused by missing providers.
- [ ] Implement `Qwen3TtsAdapter` and `OriginalAudioAdapter`, keeping synthesis serial.
- [ ] Select the Qwen runtime in `run.ps1` without changing global environment state.
- [ ] Run the focused voice suite and commit.

### Task 3: Thread voice policy through creator and folder workflows

**Files:**
- Modify: `tests/creator_batch_mvp/test_contracts.py`
- Modify: `tests/creator_batch_mvp/test_child_pipeline.py`
- Modify: `tests/video_graph_studio/test_creator_campaign_graph.py`
- Modify: `tests/video_graph_studio/test_voice_graph.py`
- Modify: `apps/creator-batch/creator_batch/contracts.py`
- Modify: `apps/creator-batch/creator_batch/cli.py`
- Modify: `apps/creator-batch/creator_batch/child_pipeline.py`
- Modify: `apps/video-graph-studio/studio/api.py`
- Modify: `apps/video-graph-studio/studio/adapters.py`

**Interfaces:**
- Consumes: `voiceProvider`, `targetVoices`, and selected target locales.
- Produces: voice-rendering launcher commands with the same provider policy for creator and folder graphs.

- [ ] Add failing policy and argv tests for `edge`, `qwen3`, and `original`.
- [ ] Add failing Studio admission tests for invalid or unavailable provider/locale combinations.
- [ ] Observe RED failures.
- [ ] Implement the smallest contract and adapter threading changes.
- [ ] Run creator-batch and Studio voice tests and commit.

### Task 4: Local output as the completion boundary

**Files:**
- Modify: `tests/video_graph_studio/creator_workspace_model.test.mjs`
- Modify: `tests/video_graph_studio/test_creator_campaign_graph.py`
- Modify: `tests/video_graph_studio/test_localization_graph.py`
- Modify: `apps/video-graph-studio/web/creator-workspace-model.mjs`
- Modify: `apps/video-graph-studio/studio/api.py`
- Modify: `apps/video-graph-studio/studio/adapters.py`

**Interfaces:**
- Consumes: allowed `localOutputRoot` and optional zero-or-more destination targets per locale.
- Produces: verified local artifacts under `<localOutputRoot>/<runId>` and exact optional route counts.

- [ ] Add failing readiness and payload tests proving zero destinations is valid.
- [ ] Add failing API tests for empty targets and allowed local output roots.
- [ ] Add failing adapter tests proving per-run output is written below the chosen root.
- [ ] Observe RED failures, then implement minimal changes.
- [ ] Run focused model and Studio tests and commit.

### Task 5: Seven-stage local-first workspace

**Files:**
- Modify: `tests/video_graph_studio/test_web_shell.py`
- Modify: `tests/video_graph_studio/creator_workspace_model.test.mjs`
- Modify: `apps/video-graph-studio/web/index.html`
- Modify: `apps/video-graph-studio/web/styles.css`
- Modify: `apps/video-graph-studio/web/app.js`
- Modify: `apps/video-graph-studio/web/creator-workspace-model.mjs`

**Interfaces:**
- Consumes: languages, translation providers, voice providers, creator catalogs, folder catalogs, and run contracts.
- Produces: Source → Videos → Translation → Voice → Output → Review → Activity interaction.

- [ ] Add failing DOM/source-mode/provider visibility tests.
- [ ] Add failing model tests for creator completeness and creator/folder payloads.
- [ ] Observe RED failures.
- [ ] Implement the staged workspace and responsive styles without a free-form canvas.
- [ ] Run Node and web-shell tests and commit.

### Task 6: Documentation and end-to-end evidence

**Files:**
- Modify: `apps/video-graph-studio/README.md`
- Modify: `docs/mvp/video-graph-studio/capability-dag.md`
- Modify: `docs/mvp/video-graph-studio/capability-evidence.md`
- Modify: `docs/mvp/video-graph-studio/delivery-ledger.md`
- Create: `docs/project/evidence/video-graph-studio/local-first-workspace-drill.md`

**Interfaces:**
- Consumes: verified implementation and browser observations.
- Produces: truthful DOMAIN_VERIFIED evidence and explicit platform-upload limits.

- [ ] Update docs with source, translation, voice, output, and optional publication boundaries.
- [ ] Start Studio from the feature worktree.
- [ ] Browser-test complete creator handling and a real local folder, including narrow width and console inspection.
- [ ] Run the full repository suite, Node tests, manifest checks, and `git diff --check`.
- [ ] Record exact evidence and publish the branch.
