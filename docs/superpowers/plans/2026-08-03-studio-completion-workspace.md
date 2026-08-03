# Studio Completion Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. The user has prohibited subagents, so execution is inline.

**Goal:** Make voice throughput measurable and make every completed campaign immediately usable through verified metrics, browser preview, file location and Chinese/English/Russian UI.

**Architecture:** Voice and Translation continue to own their receipts. A new pure Studio result projector consumes completed run facts and verified manifests without mutating them. The HTTP server exposes that projection plus a byte-range media adapter restricted to projected result files. The browser renders completion facts and stores only the selected display locale.

**Tech Stack:** Python 3.12 standard library, native HTML/CSS/ES modules, Node test runner, pytest, Edge TTS, JSON manifests.

## Global Constraints

- Local output succeeds with zero publication routes.
- Missing provider usage is displayed as not reported, never as zero.
- Preview serves only hash-verified localized video files under allowed roots.
- UI locales are exactly `zh-CN`, `en-US` and `ru-RU`.
- Keep the existing seven-stage URLs, DOM stage IDs and dark product-workspace design.
- Use bounded Edge concurrency of 6, based on the measured throughput plateau.
- No subagents.

---

### Task 1: Edge throughput and provider usage facts

**Files:**
- Modify: `apps/voice-rendering/voice_rendering_app/adapters.py`
- Modify: `apps/translation/translation_app/adapters.py`
- Modify: `apps/translation/translation_app/operation.py`
- Test: `tests/voice_rendering_mvp/test_adapter_cli.py`
- Test: `tests/translation_mvp/test_adapters.py`
- Test: `tests/translation_mvp/test_operation.py`

**Interfaces:**
- Produces: `EdgeTtsAdapter.max_workers == 6`.
- Produces: `DeepSeekAdapter.last_usage -> {promptTokens, completionTokens, totalTokens} | None`.
- Produces: optional `usage` on each completed Translation receipt item.

- [ ] Write a failing Edge test asserting six bounded workers.
- [ ] Run the focused test and observe the old value `3`.
- [ ] Change the bounded default to `6` and run Voice Rendering tests.
- [ ] Write a failing DeepSeek adapter test whose requester returns `usage` and assert normalized token facts.
- [ ] Add `last_usage`, resetting it before every request and accepting only non-negative integer provider values.
- [ ] Write a failing Translation Loop test asserting that a completed item commits the adapter's usage and a local adapter omits it.
- [ ] Persist usage in the item receipt without changing Translation Manifest identity.
- [ ] Run Translation and Voice Rendering suites.

### Task 2: Result projection

**Files:**
- Create: `apps/video-graph-studio/studio/result_projection.py`
- Modify: `apps/video-graph-studio/studio/api.py`
- Test: `tests/video_graph_studio/test_result_projection.py`

**Interfaces:**
- Produces: `project_run_results(run: dict) -> dict` with `status`, `elapsedSeconds`, `outputRoot`, `totalBytes`, `reportedUsage`, `videos` and `phaseDurations`.
- Produces: `GET /api/v1/runs/{run_id}/results`.

- [ ] Write a failing fixture test with one Creator Batch Manifest, one Localization Manifest and one Translation receipt.
- [ ] Assert exact path, language, bytes, duration, dimensions, codec, total bytes, elapsed time and token totals.
- [ ] Implement strict JSON readers and hash/size validation at the committed fact boundary.
- [ ] Return unavailable rows for stale child facts instead of throwing away the entire projection.
- [ ] Write and run an API route test against a real `RunStore` fixture.
- [ ] Run focused Studio Python tests.

### Task 3: Verified local media preview

**Files:**
- Modify: `apps/video-graph-studio/studio/server.py`
- Modify: `apps/video-graph-studio/studio/api.py`
- Test: `tests/video_graph_studio/test_media_preview.py`

**Interfaces:**
- Produces: `GET /api/v1/runs/{run_id}/media/{video_id}` with `video/mp4`, `Accept-Ranges: bytes`, bounded `Content-Range`, and `206` support.
- Consumes: only file paths returned by `project_run_results` for that run.

- [ ] Write a failing HTTP test for full-file and `Range: bytes=2-5` responses.
- [ ] Write a failing traversal/unverified-ID test expecting 404.
- [ ] Add server routing that resolves media by opaque projection ID rather than accepting a filesystem path.
- [ ] Stream bounded chunks and implement 416 for invalid ranges.
- [ ] Run the HTTP integration tests.

### Task 4: Completion UI and three display languages

**Files:**
- Create: `apps/video-graph-studio/web/i18n.mjs`
- Create: `apps/video-graph-studio/web/result-model.mjs`
- Modify: `apps/video-graph-studio/web/index.html`
- Modify: `apps/video-graph-studio/web/app.js`
- Modify: `apps/video-graph-studio/web/styles.css`
- Test: `tests/video_graph_studio/result_model.test.mjs`
- Test: `tests/video_graph_studio/test_web_shell.py`

**Interfaces:**
- Produces: locale selector persisted as `videoGraph.uiLocale`.
- Produces: completed-run summary with elapsed time, total size, reported tokens, output folder and one preview row per localized derivative.

- [ ] Write failing model tests for byte/time/token formatting and missing usage.
- [ ] Implement pure result formatting with no DOM dependency.
- [ ] Write failing shell tests for locale selector, result summary and video preview container.
- [ ] Add a completion section inside Activity with a real `<video controls preload="metadata">` for the selected result.
- [ ] Add Open/Download links that use the verified media endpoint and display the real filesystem path as copyable text.
- [ ] Add complete static and dynamic dictionaries for Chinese, English and Russian, including errors and empty/loading states.
- [ ] Preserve selection while polling by only replacing changed result DOM.
- [ ] Test desktop and narrow layouts plus keyboard focus and text selection.

### Task 5: One-click startup and evidence

**Files:**
- Create: `start-studio.cmd`
- Create: `start-studio.ps1`
- Modify: `README.md`
- Modify: `apps/video-graph-studio/README.md`
- Modify: `docs/mvp/video-graph-studio/capability-evidence.md`
- Modify: `docs/mvp/video-graph-studio/delivery-ledger.md`
- Test: `tests/video_graph_studio/test_public_app.py`

**Interfaces:**
- Produces: double-clickable root launcher that installs missing Studio dependencies only when needed, starts loopback port 8765 and opens the browser.

- [ ] Write a failing launcher verification test using `-VerifyOnly`.
- [ ] Implement PowerShell startup and a CMD shim with quoted paths.
- [ ] Run the launcher verification and local HTTP smoke test.
- [ ] Capture real source, progress and completion screenshots from the running application.
- [ ] Add the workflow Mermaid diagram, one-click instructions, capability truth table and screenshots to the README.
- [ ] Record the Edge 1/3/6/8 benchmark and completed-result projection evidence.
- [ ] Run focused and adjacent suites, inspect both viewport sizes, commit and push main.
