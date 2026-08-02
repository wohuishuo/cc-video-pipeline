# Creator Workflow Studio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. The user prohibited subagents.

**Goal:** Deliver one browser workspace that discovers a creator account without downloading, lists and selects videos, configures multilingual voice/subtitle variants, and starts an exact selected-video localization campaign.

**Architecture:** Creator Discovery remains the account catalog owner. New read-only Studio projections expose its committed manifest, a new Creator Selection MVP writes the exact selected subset, and a fixed `creator-campaign` Graph composes that fact into the existing strict-serial Creator Batch. The browser becomes a stage-based project workspace rather than an infinite node canvas; guarded publication remains a following independently verified slice.

**Tech Stack:** Python 3.12, PowerShell 5.1, SQLite RunStore, browser-native ES modules, HTML/CSS, Node test runner, pytest.

## Global Constraints

- Maximum active workflow count and child-process count remain one.
- No media download occurs during creator discovery or catalog projection.
- Studio owns continuation/projection only and never edits child-owner manifests.
- Browser input may reference a discovery run and selected IDs, never a trusted raw artifact path.
- Public uploads remain disabled; non-YouTube execution remains `PLAN_ONLY` until separately verified.
- Do not read, edit, stage or commit `apps/localization/localizer/subagent_translation.py`.
- Do not use subagents.

---

### Task 1: Portable Platform I/O Launcher

**Files:**
- Modify: `video-platform.ps1`
- Create: `tests/video_platform/test_public_launcher.py`

**Interfaces:**
- Consumes: any caller working directory.
- Produces: the repository `video_platform` CLI executed with the shared repository Python runtime.

- [x] Write a real subprocess test that invokes `video-platform.ps1 --help` from `tmp_path` and requires exit zero plus `download`/`upload` commands.
- [x] Observe RED: system Python reports `No module named video_platform`.
- [x] Resolve the git common root, select `tools/.venv`, set repository `PYTHONPATH`, push into the repository for module execution, and restore caller environment/location in `finally`.
- [x] Run the focused and adjacent Platform I/O, Source Intake and Studio Intake suites: 65 passed.
- [x] Commit `fix: make the platform launcher portable`.

### Task 2: Creator Catalog Projection

**Files:**
- Create: `apps/video-graph-studio/studio/creator_catalog.py`
- Modify: `apps/video-graph-studio/studio/api.py`
- Create: `tests/video_graph_studio/test_creator_catalog_projection.py`

**Interfaces:**
- Consumes: `RunStore.get_run(run_id)` for a terminal `creator-profile` run and its committed `discover-creator` result.
- Produces: `project_creator_catalog(run: dict) -> dict` and `GET /api/v1/runs/{runId}/creator-catalog`.

- [ ] Write a focused test with a real Creator Manifest whose SHA is stored in a completed discovery step. Assert exact ordered item projection and `subtitleStatus == "UNKNOWN_ASR"`.
- [ ] Add wrong-graph, non-terminal, missing-file and fingerprint-conflict tests; each must return a bounded contract error and no item data.
- [ ] Observe RED because the route returns `REJECTED_NOT_FOUND`.
- [ ] Implement strict schema/fingerprint projection without changing the manifest.
- [ ] Expose the nested GET route before generic run action routing.
- [ ] Run catalog, API, access and run-store suites; commit `feat: expose verified creator catalogs`.

### Task 3: Expanded Language Catalog

**Files:**
- Create: `apps/video-graph-studio/studio/language_catalog.py`
- Modify: `apps/video-graph-studio/studio/api.py`
- Modify: `apps/translation/translation_app/contracts.py`
- Modify: `apps/translation/translation_app/adapters.py`
- Modify: `apps/creator-batch/creator_batch/contracts.py`
- Create: `tests/video_graph_studio/test_language_catalog.py`
- Modify: `tests/translation_mvp/test_contracts.py`
- Modify: `tests/translation_mvp/test_adapter.py`

**Interfaces:**
- Produces: immutable rows `{locale,name,nllbCode,defaultVoice}` and `GET /api/v1/languages`.
- Admits these locales consistently: `ru-RU`, `en-US`, `kk-KZ`, `zh-CN`, `es-ES`, `fr-FR`, `de-DE`, `it-IT`, `pt-BR`, `ja-JP`, `ko-KR`, `ar-SA`, `hi-IN`, `tr-TR`, `uk-UA`, `pl-PL`, `nl-NL`, `id-ID`, `vi-VN`, `th-TH`.

- [ ] Write table tests requiring all 20 locales to normalize, map to exact NLLB codes and expose a non-empty default voice.
- [ ] Observe RED for `es-ES` and the absent API route.
- [ ] Add literal aliases/source/target maps and the immutable Studio projection.
- [ ] Replace Creator Batch's three-locale guard with the same 20-locale contract and add a drift test comparing exact sets.
- [ ] Run Translation, Creator Batch and Studio API suites; commit `feat: expand the localization language catalog`.

### Task 4: Independent Creator Selection MVP

**Files:**
- Create: `apps/creator-selection/mvp.json`
- Create: `apps/creator-selection/README.md`
- Create: `apps/creator-selection/install.ps1`
- Create: `apps/creator-selection/run.ps1`
- Create: `apps/creator-selection/creator_selection/__init__.py`
- Create: `apps/creator-selection/creator_selection/contracts.py`
- Create: `apps/creator-selection/creator_selection/operation.py`
- Create: `apps/creator-selection/creator_selection/cli.py`
- Create: `tests/creator_selection_mvp/test_selection.py`
- Create: `tests/creator_selection_mvp/test_public_cli.py`

**Interfaces:**
- Command: `select CREATOR_MANIFEST --video-id ID... --output-dir DIR --operation-id ID --json`.
- Fact: schema-v1 `creator-selection-manifest.json` containing source path/SHA, platform/creator, ordered selected items and selected IDs.

- [ ] Write RED contracts for ordered subset selection, unknown/duplicate IDs, same-operation duplicate replay and same-operation input conflict.
- [ ] Implement immutable schema parsing and canonical fingerprinting.
- [ ] Implement atomic receipt/manifest writes; preserve source order regardless of browser selection order.
- [ ] Add public launcher and manifest declaration; run focused plus repository manifest validation.
- [ ] Commit `feat: add the creator selection MVP`.

### Task 5: Selected Creator Campaign Graph

**Files:**
- Modify: `apps/video-graph-studio/studio/api.py`
- Modify: `apps/video-graph-studio/studio/adapters.py`
- Modify: `apps/video-graph-studio/studio/server.py`
- Modify: `apps/video-graph-studio/studio/workflow_catalog.py`
- Create: `tests/video_graph_studio/test_creator_campaign_graph.py`

**Interfaces:**
- Template: `creator-campaign`.
- Input: `creatorRunId`, `selectedVideoIds`, `targetLanguages`, `targetVoices`, ASR/translation/source-volume policies and optional cookies.
- Graph: `select-creator-videos -> verify-selection -> localize-creator-batch -> verify-creator-batch` using Fact edges.

- [ ] Write a RED API test proving the browser cannot submit artifact paths and that a completed creator run plus exact selected IDs creates four ordered steps.
- [ ] Write adapter RED tests proving the Selection public CLI receives the committed source manifest and that Creator Batch consumes only the Selection fact.
- [ ] Resolve and fingerprint the creator run during admission; reject wrong workspace/run/status/graph and unknown IDs before creation.
- [ ] Implement Selection command and verification adapters, then retarget Creator Batch and aggregate verification to the selected manifest.
- [ ] Prove with real Discovery → Selection adjacency that unselected URLs never enter the batch manifest.
- [ ] Run Studio, Creator Selection and Creator Batch suites; commit `feat: compose selected creator campaigns`.

### Task 6: Stage-based Creator Workspace UI

**Files:**
- Replace: `apps/video-graph-studio/web/index.html`
- Replace: `apps/video-graph-studio/web/styles.css`
- Replace: `apps/video-graph-studio/web/app.js`
- Create: `apps/video-graph-studio/web/creator-workspace-model.mjs`
- Create: `tests/video_graph_studio/creator_workspace_model.test.mjs`
- Modify: `tests/video_graph_studio/test_web_shell.py`

**Interfaces:**
- Stages: Creator, Videos, Languages, Destinations, Review, Activity.
- Pure model: `campaignCounts(selection, variants)`, `campaignReadiness(state)`, `filterCreatorItems(items, query)`, `buildCampaignPayload(state)`.

- [ ] Write Node RED tests for video filtering/select-all, 20-locale searchable selection, exact source × language × destination counts and omission of unselected IDs.
- [ ] Write shell RED assertions requiring stage navigation, catalog grid, subtitle status, language search/rows, destination matrix and no graph viewport/zoom/ports.
- [ ] Implement Creator stage discovery through the existing versioned run commands, poll completion, then fetch the verified creator catalog.
- [ ] Implement Videos stage with search, Select all/Clear, compact rows and truthful subtitle badges.
- [ ] Implement Languages and Destinations stages using backend catalog rows, voice fields and per-language platform/account matrix.
- [ ] Implement Review counts and start `creator-campaign`; keep publication status explicit as YouTube private-ready or plan-only.
- [ ] Implement Activity timeline from exact run steps without drag/pan/zoom.
- [ ] Run Node and Studio web suites; commit `feat: build the creator campaign workspace`.

### Task 7: Live Browser and Delivery Evidence

**Files:**
- Modify: `apps/video-graph-studio/README.md`
- Modify: `docs/mvp/video-graph-studio/capability-dag.md`
- Modify: `docs/mvp/video-graph-studio/capability-evidence.md`
- Modify: `docs/mvp/video-graph-studio/delivery-ledger.md`
- Create: `docs/project/evidence/video-graph-studio/creator-workspace-drill.md`

**Interfaces:**
- Public launcher at `127.0.0.1:8765`; real browser interaction; no external publication.

- [ ] Stop only verified inactive Studio listeners, start one current listener and verify contracts/catalog/languages routes.
- [ ] Use the browser to load one creator catalog, filter/select videos, choose at least two languages and two destination plans, and verify exact Review counts.
- [ ] Start a bounded selected campaign only if its input media/download is safe and record run/step facts; otherwise record the exact external blocker without claiming execution.
- [ ] Record viewport overflow, catalog item count, selected IDs, language rows, campaign payload and platform effect boundaries.
- [ ] Run `scripts/test-all.ps1`, Node tests, `git diff --check` and MVP manifest validation.
- [ ] Commit, push, open a ready PR, merge to remote `main` and confirm the merge SHA while preserving unrelated user files.
