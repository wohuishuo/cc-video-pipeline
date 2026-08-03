# Live Progress and Voice Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make local creator campaigns observable, fast enough for Edge/Qwen use, automatically recover transient voice failures, and retry failed work without discarding committed child artifacts.

**Architecture:** Creator videos remain strictly serial. Voice Rendering owns provider-specific segment concurrency and checkpoints, Creator Batch emits durable phase projections at MVP boundaries, Studio owns failed-run retry, and the browser projects detailed progress from immutable run facts and logs.

**Tech Stack:** Python 3.12, `edge-tts`, PyTorch/Qwen3-TTS, SQLite, vanilla ES modules, HTML/CSS, Node test runner, pytest.

## Global Constraints

- Do not parallelize creator videos; `maximumActiveItems` remains exactly `1`.
- Edge may synthesize at most three segments concurrently and retries recognized transient failures at most three times.
- Qwen keeps one resident model and one active synthesis; `auto` resolves to CUDA when available and CPU otherwise.
- Progress is a read-only projection; child receipts remain the delivery authorities.
- Failed-run retry preserves completed steps and child operation IDs, resets only failed steps, and creates at most one durable queue entry.
- Publication remains optional and is not changed by retry.
- No subagents are used for execution, per the operator's instruction.

---

### Task 1: Reliable bounded Edge synthesis

**Files:**
- Modify: `apps/voice-rendering/voice_rendering_app/adapters.py`
- Modify: `apps/voice-rendering/voice_rendering_app/operation.py`
- Modify: `tests/voice_rendering_mvp/test_adapter_cli.py`
- Modify: `tests/voice_rendering_mvp/test_operation.py`

**Interfaces:**
- Consumes: `VoiceAdapter.synthesize(text, language, voice, output, on_log, target_duration=...)`.
- Produces: `adapter.max_workers: int`, `receipt.items[].attempts: int`, `receipt.items[].elapsedSeconds: float`, ordered manifests and reusable completed clips.

- [ ] **Step 1: Write failing adapter tests**

Add tests proving a transient `NoAudioReceived`-shaped failure succeeds on the second attempt, a non-transient error is not retried, and the production direct-save path does not construct `python -m edge_tts` subprocesses.

```python
def test_edge_adapter_retries_transient_no_audio_and_reports_attempts(tmp_path):
    calls = []
    def save(text, voice, output):
        calls.append(text)
        if len(calls) == 1:
            raise RuntimeError("edge_tts.exceptions.NoAudioReceived: No audio was received")
        output.write_bytes(b"audio")
    adapter = EdgeTtsAdapter(save_runner=save, duration_probe=lambda _: 1.25, sleep=lambda _: None)
    assert adapter.synthesize("text", "ru-RU", "ru-RU-DmitryNeural", tmp_path / "x.mp3", lambda _: None) == 1.25
    assert adapter.last_attempts == 2
```

- [ ] **Step 2: Run adapter tests and observe RED**

Run: `tools/.venv/Scripts/python.exe -m pytest --import-mode=importlib tests/voice_rendering_mvp/test_adapter_cli.py -q`

Expected: constructor rejects `save_runner` or `last_attempts` is missing.

- [ ] **Step 3: Implement direct Edge save and bounded retry**

Use `edge_tts.Communicate(text=text, voice=voice, rate=..., volume=...).save(str(output))` through `asyncio.run`. Set `max_workers = 3`; keep adapter identity `edge-tts@1` because transport scheduling does not change artifact semantics. Retry only messages containing `NoAudioReceived`, `TimeoutError`, `ConnectionError`, `Connection reset` or `temporarily unavailable`, with injected sleeps of one and two seconds. Delete the partial output before every attempt.

- [ ] **Step 4: Write failing operation concurrency test**

Use a barrier-based fake Edge adapter with `max_workers=3`. Assert output receipt order matches translation order, `maximumActiveSynthesis == 3`, every item records attempts/elapsed time, and a second execution reuses completed clips.

- [ ] **Step 5: Run operation test and observe RED**

Run: `tools/.venv/Scripts/python.exe -m pytest --import-mode=importlib tests/voice_rendering_mvp/test_operation.py -q`

Expected: maximum activity remains `1` and timing metadata is absent.

- [ ] **Step 6: Implement ordered concurrent rendering**

In `VoiceRenderingLoop`, keep a result slot for every work row, fill reusable slots first, submit missing rows to `ThreadPoolExecutor(max_workers=min(adapter.max_workers, missing_count))`, checkpoint completed futures in canonical work order, and publish a manifest only when every slot completed. Qwen and Original adapters expose `max_workers = 1`.

- [ ] **Step 7: Verify and commit**

Run both Voice Rendering test files. Commit: `fix: recover and accelerate edge voice clips`.

### Task 2: Qwen automatic GPU selection

**Files:**
- Modify: `apps/voice-rendering/voice_rendering_app/adapters.py`
- Modify: `apps/voice-rendering/voice_rendering_app/cli.py`
- Modify: `apps/creator-batch/creator_batch/contracts.py`
- Modify: `apps/creator-batch/creator_batch/cli.py`
- Modify: `apps/creator-batch/creator_batch/child_pipeline.py`
- Modify: `apps/video-graph-studio/studio/api.py`
- Modify: `apps/video-graph-studio/web/creator-workspace-model.mjs`
- Modify: `apps/video-graph-studio/web/app.js`
- Modify: `apps/video-graph-studio/web/index.html`
- Test: `tests/voice_rendering_mvp/test_adapter_cli.py`
- Test: `tests/creator_batch_mvp/test_contracts.py`
- Test: `tests/creator_batch_mvp/test_child_pipeline.py`
- Test: `tests/video_graph_studio/creator_workspace_model.test.mjs`
- Test: `tests/video_graph_studio/test_creator_campaign_graph.py`

**Interfaces:**
- Produces: campaign parameter `qwenDevice: "auto" | "cuda" | "cpu"`; `BatchPolicy.qwen_device`; Voice Rendering CLI `--qwen-device auto`.

- [ ] **Step 1: Add failing contract and argv tests**

Assert the default policy serializes `qwenDevice: "auto"`, invalid device values reject, Qwen child argv includes `--qwen-device auto`, and Studio preserves the chosen value.

- [ ] **Step 2: Run focused tests and observe RED**

Run the three Python test files and the workspace Node test. Expected: `qwenDevice` fields and argv are missing.

- [ ] **Step 3: Implement device policy end to end**

Add the field to browser state/payload, Studio validation, Creator Batch contracts/CLI and child Voice Rendering argv. Add an Auto/GPU/CPU selector visible only for Qwen. Do not add the field for Edge or Original payloads.

- [ ] **Step 4: Resolve `auto` inside Qwen engine**

After importing torch, resolve `auto` to `cuda` when `torch.cuda.is_available()` and otherwise `cpu`. Log the resolved device before model load. Keep `max_workers = 1`.

- [ ] **Step 5: Verify and commit**

Run focused Python and Node tests. Commit: `fix: select qwen gpu automatically`.

### Task 3: Durable phase events and pure progress projection

**Files:**
- Modify: `apps/creator-batch/creator_batch/child_pipeline.py`
- Modify: `apps/voice-rendering/voice_rendering_app/operation.py`
- Create: `apps/video-graph-studio/web/activity-progress-model.mjs`
- Create: `tests/video_graph_studio/activity_progress_model.test.mjs`
- Modify: `tests/creator_batch_mvp/test_child_pipeline.py`

**Interfaces:**
- Produces log lines containing compact JSON with `event: "creator_phase"` or `event: "voice_progress"`.
- Produces `projectActivity(run)` returning `{item, phases, failure, rawLogText}`.

- [ ] **Step 1: Add failing Creator Batch event test**

Capture logs and assert each owner emits ordered RUNNING and COMPLETED events with phases `download`, `transcription`, `translation`, `voice`, `composition`, item ordinal/count/id and no artifact contents.

- [ ] **Step 2: Run Creator Batch test and observe RED**

Expected: no `creator_phase` events exist.

- [ ] **Step 3: Emit boundary events**

Wrap each `_invoke` call with compact JSON logs. Emit FAILED with the owner-safe error when a child does not commit a manifest.

- [ ] **Step 4: Add failing progress projection tests**

Cover structured logs and the existing failed run's legacy lines: `Started creator item 1/1`, `transcribing`, `Translated 62/62`, `[61/62] rendering`, `10 clip(s) failed`. Assert five phase states, voice `52/62` completed with 10 failures, and a human failure summary.

- [ ] **Step 5: Run Node test and observe RED**

Run: `node --test tests/video_graph_studio/activity_progress_model.test.mjs`

Expected: module is missing.

- [ ] **Step 6: Implement the pure projector**

Parse compact JSON events first and legacy lines second. Never mutate the run. Derive elapsed durations from log `created_at` timestamps and keep raw logs in sequence order.

- [ ] **Step 7: Verify and commit**

Run focused Creator Batch and Node tests. Commit: `feat: project detailed creator progress`.

### Task 4: Retry failed Studio steps without losing checkpoints

**Files:**
- Modify: `apps/client-contracts/client_contracts/contracts.py`
- Modify: `apps/video-graph-studio/studio/client_contracts.py`
- Modify: `apps/video-graph-studio/studio/store.py`
- Modify: `apps/video-graph-studio/studio/engine.py`
- Modify: `apps/video-graph-studio/studio/api.py`
- Modify: `tests/client_contracts_mvp/test_contracts.py`
- Modify: `tests/video_graph_studio/test_run_store.py`
- Modify: `tests/video_graph_studio/test_engine.py`
- Modify: `tests/video_graph_studio/test_api.py`

**Interfaces:**
- Produces command `CMD-RUN-RETRY` at `POST /api/v1/runs/{runId}/retry`.
- Produces `RunStore.retry_failed(run_id) -> CommandResult` and `WorkflowEngine.retry(run_id) -> CommandResult`.

- [ ] **Step 1: Add failing Store lifecycle tests**

Create a run with one completed step, one failed step and a pending successor. Assert retry keeps the completed step/result unchanged, resets the failed step to PENDING with the same child operation ID, clears the terminal result, moves the run to INTERRUPTED and rejects retry for COMPLETED/RUNNING runs.

- [ ] **Step 2: Run Store test and observe RED**

Expected: `retry_failed` is missing.

- [ ] **Step 3: Implement atomic failed-run reset**

Under `BEGIN IMMEDIATE`, validate run status FAILED, update only FAILED steps to PENDING, clear their result/error, increment step versions, set run status INTERRUPTED, increment run version, clear terminal result, append a durable retry log and commit once.

- [ ] **Step 4: Add failing Engine/API/contract tests**

Assert retry enqueues once, duplicate retry is idempotent, versioned command validation accepts `CMD-RUN-RETRY`, and the endpoint returns 202 only for a newly queued retry.

- [ ] **Step 5: Implement command composition**

Add the contract and endpoint, call Store reset then the existing durable start queue, and start the serial drain worker. Do not create a new run or child operation IDs.

- [ ] **Step 6: Verify and commit**

Run Client Contracts and Studio lifecycle/API tests. Commit: `feat: retry failed studio steps`.

### Task 5: Detailed activity UI and copy-safe logs

**Files:**
- Modify: `apps/video-graph-studio/web/index.html`
- Modify: `apps/video-graph-studio/web/app.js`
- Modify: `apps/video-graph-studio/web/styles.css`
- Modify: `tests/video_graph_studio/test_web_shell.py`
- Modify: `tests/video_graph_studio/activity_progress_model.test.mjs`

**Interfaces:**
- Consumes: `projectActivity(run)` and `CMD-RUN-RETRY`.
- Produces: five phase rows, per-phase progress bars, current item summary, failure recovery card, Copy Logs and Retry Failed Step actions.

- [ ] **Step 1: Add failing shell assertions**

Assert IDs `campaign-progress`, `current-item-progress`, `phase-progress`, `copy-log`, `retry-run`, and accessible `role="progressbar"` rendering hooks exist. Bump local assets to version 14.

- [ ] **Step 2: Run shell tests and observe RED**

Run the focused shell test. Expected: the new controls are missing.

- [ ] **Step 3: Implement semantic activity markup and styling**

Use compact phase rows rather than one shared bar. Status must be readable without color. Preserve the raw system-step timeline below the operator progress. Set `.log-panel pre { user-select: text; }` and provide visible keyboard focus.

- [ ] **Step 4: Bind projection, retry and clipboard behavior**

Render only when the projected HTML/text changed. `copy-log` copies `rawLogText`, uses `navigator.clipboard.writeText` first and a temporary textarea fallback, then announces success through the existing toast. `retry-run` sends the versioned retry command, switches to RUNNING state and resumes polling.

- [ ] **Step 5: Run focused tests and browser drill**

Load the existing failed run and verify five distinct phases, `52/62`, 10 failed clips, copy button behavior, no console errors and no horizontal overflow. Retry the failed run only after Tasks 1–4 are live; confirm prior 52 clips log as reused and only 10 are synthesized.

- [ ] **Step 6: Run full verification and document evidence**

Run `scripts/test-all.ps1`, all Node Studio tests, `node --check apps/video-graph-studio/web/app.js` and `git diff --check`. Update the Studio evidence ledger with measured before/after timings and explicit external-service limits.

- [ ] **Step 7: Commit, publish and merge**

Commit: `feat: show live phase progress and recovery`. Push `codex/studio-live-progress`, create a ready PR, merge to `main` after fresh verification, and keep the live server on the verified tree.

## Plan self-review

- Spec coverage: voice retry/concurrency, Qwen GPU choice, durable phase events, legacy projection, failed-run retry, copy behavior, browser evidence and main integration each have a task.
- Placeholder scan: no deferred implementation markers remain.
- Type consistency: `qwenDevice`, `creator_phase`, `voice_progress`, `projectActivity`, `CMD-RUN-RETRY`, `retry_failed` and `retry` are named consistently across producers and consumers.
