# Localized Video Composition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development to implement this plan task-by-task. Subagents are forbidden by the user's standing instruction.

**Goal:** Rebuild the public Localization MVP so verified Source, Translation and Voice manifests produce resumable subtitle-burned, dubbed MP4 derivatives.

**Architecture:** A new `localization_app` owns manifest validation and the serial derivative loop. It calls an injected composition adapter; production uses one argv-only FFmpeg process plus FFprobe. Graph Studio composes only the public PowerShell launcher and committed manifest.

**Tech Stack:** Python 3.12 standard library, FFmpeg/FFprobe, PowerShell, pytest, existing Graph Studio SQLite process owner.

## Global Constraints

- Do not import `apps/localization/localizer` or another application's private package.
- Execute one derivative and one child process at a time.
- Preserve exact manifest lineage and atomically publish only probe-verified MP4 files.
- Mix source audio at `0.12`; do not claim source-vocal separation.
- Preserve the untracked user file `apps/localization/localizer/subagent_translation.py`.

---

### Task 1: Composition input owner

**Files:**
- Create: `apps/localization/localization_app/contracts.py`
- Test: `tests/localization_mvp/test_contracts.py`

**Interfaces:**
- Produces: `load_composition_inputs(source_manifest, translation_manifest, voice_manifest) -> CompositionInput`.
- Guarantees exact language/media/segment coverage and verified referenced files.

- [ ] Write contract fixtures and failing assertions for valid lineage, changed source/SRT/clip fingerprints and missing segment coverage.
- [ ] Run focused tests and observe import/contract failure.
- [ ] Implement frozen input/job dataclasses and validation.
- [ ] Run focused GREEN and commit.

### Task 2: FFmpeg plan and adapter

**Files:**
- Create: `apps/localization/localization_app/ffmpeg.py`
- Test: `tests/localization_mvp/test_ffmpeg.py`

**Interfaces:**
- Produces: `build_ffmpeg_argv(job, output) -> list[str]` and `FfmpegCompositionAdapter.compose(job, output, on_log) -> ProbeResult`.

- [ ] Write failing literal assertions for delayed clips, overlong-clip `atempo`, source-bed volume, subtitle escaping and output codec arguments.
- [ ] Implement the pure argv builder, subprocess runner and FFprobe validation.
- [ ] Run focused GREEN and commit.

### Task 3: Serial localization loop and public CLI

**Files:**
- Create: `apps/localization/localization_app/operation.py`, `cli.py`, `__init__.py`
- Replace: `apps/localization/run.ps1`, `README.md`, `mvp.json`
- Test: `tests/localization_mvp/test_operation.py`, `test_cli.py`

**Interfaces:**
- Produces: `LocalizationLoop.execute(...) -> LocalizationResult` and schema-v1 manifest/receipt.

- [ ] Write failing tests for language-major order, maximum active adapter 1, atomic publication, failed-item resume, completed replay and conflict.
- [ ] Implement minimal loop/checkpoint owner and public launcher.
- [ ] Run focused GREEN and commit.

### Task 4: Real adjacent/platform evidence

**Files:**
- Update: `docs/mvp/localization/*`, `docs/project/evidence/localization/delivery-ledger.md`

- [ ] Run the public launcher using the real Source, Translation and Voice manifests from runs `7e50a83f-...` and `real-edge-ru-kk-1`.
- [ ] Verify output with FFprobe and render one PNG frame for visual inspection.
- [ ] Record exact command, receipt, hashes, codecs, duration, missing evidence and forbidden claims.

### Task 5: Graph Studio composition

**Files:**
- Modify: `apps/video-graph-studio/studio/api.py`, `adapters.py`, `server.py`
- Modify: `apps/video-graph-studio/web/index.html`, `app.js`
- Test: `tests/video_graph_studio/test_localization_graph.py`, `test_web_shell.py`

- [ ] Write failing tests for ten ordered owner steps, policy admission, public adapter invocation and output-manifest verification.
- [ ] Add `Folder+Dub` and `URL+Dub` templates and browser projection.
- [ ] Run one real browser-admitted ten-step workflow and record its run ID.

### Task 6: Repository verification and publication

- [ ] Run the full relevant test matrix, manifest validator and `git diff --check`.
- [ ] Audit every design invariant against executable evidence.
- [ ] Commit, push, create PR and merge only after fresh verification.
