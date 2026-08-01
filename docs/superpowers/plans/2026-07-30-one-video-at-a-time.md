# One-video-at-a-time Localization Implementation Plan

> **For agentic workers:** Execute inline; subagents are prohibited by the user.

**Goal:** Produce each Russian final video before starting the next video's voice generation.

**Architecture:** Add job selection to the Qwen worker. Change the batch coordinator to invoke one isolated worker per job, then mix and render that job immediately.

**Tech Stack:** Python, Qwen3-TTS, FFmpeg, pytest.

## Global Constraints

- Exactly one Qwen worker process at a time.
- Preserve resumable clips and stage receipts.
- Continue after an individual video fails.

### Task 1: Select one voice job

**Files:** `apps/localization/localizer/qwen_voice_worker.py`, `tests/localization/test_voice.py`

- [ ] Add a failing test proving only the selected job is synthesized.
- [ ] Add `job_ids` API and `--job-id` CLI selection.
- [ ] Run voice tests.

### Task 2: Sequentially finalize videos

**Files:** `apps/localization/localizer/batch.py`, `tests/localization/test_batch.py`

- [ ] Add a failing coordinator-order test.
- [ ] Run voice worker, mix, and render for one job before advancing.
- [ ] Run localization tests and commit.
