# Edge-TTS Video Localizer Implementation Plan

> **For agentic workers:** Execute inline with test-driven development. No subagents are required.

**Goal:** Provide a one-command, strictly serial Edge-TTS Russian dubbing and hard-subtitle workflow.

**Architecture:** A new independent coordinator owns Edge clip receipts and final publication while reusing the existing timeline mixer, ASS generator, and FFmpeg renderer. It processes exactly one job and one segment at a time and resumes from verified artifacts.

**Tech Stack:** Python 3.12, edge-tts, FFmpeg, pytest, PowerShell.

## Global Constraints

- No parallel video or segment processing.
- Do not invoke Qwen.
- Preserve translation IDs and timestamps.
- Publish a final video only after all preceding stages succeed.

### Task 1: Edge voice capability

**Files:** create `apps/localization/localizer/edge_video_localizer.py`; create `tests/localization/test_edge_video_localizer.py`.

- [ ] Write a failing test for sequential clip synthesis and reuse.
- [ ] Implement the Edge adapter and atomic WAV conversion.
- [ ] Verify focused tests.

### Task 2: Serial vertical slice

**Files:** modify the same files; create `apps/localization/edge-russian.ps1`.

- [ ] Write a failing test proving complete job order and failure continuation.
- [ ] Compose existing mix, ASS, and render capabilities.
- [ ] Add CLI and PowerShell launcher.
- [ ] Run localization tests and one real video smoke test.

