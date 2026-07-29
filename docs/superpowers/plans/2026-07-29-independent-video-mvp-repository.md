# Independent Video MVP Repository Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the mixed video-tool repository into an English monorepo of independently installable, runnable, testable, and documented MVP applications.

**Architecture:** Add a manifest-driven repository shell, then migrate capabilities through compatibility wrappers into `apps/<mvp>`. Applications communicate through files and public CLIs; only contracts and process primitives may be shared.

**Tech Stack:** Python 3.12, PowerShell 5.1+, FFmpeg/FFprobe, yt-dlp, Remotion/TypeScript, pytest, JSON manifests.

## Global Constraints

- Preserve all unrelated uncommitted user work.
- Reusable source, documentation, and CLI help are English; user content is not translated.
- Every MVP owns exactly one mutable output boundary.
- Every MVP has `README.md`, `mvp.json`, `run.ps1`, `install.ps1`, tests, and four evidence artifacts.
- No application imports another application's private modules.
- No public upload is performed for verification.

---

### Task 1: Repository contract and validator

**Files:** Create `scripts/validate_mvp_manifests.py`, `tests/repository/test_mvp_manifests.py`, `apps/README.md`, and `packages/contracts/README.md`.

**Interfaces:** Produces `validate_repository(root: Path) -> list[str]` and the `mvp.json` contract consumed by every later task.

- [ ] Write a failing test that creates an incomplete application manifest and asserts exact missing-field errors.
- [ ] Run `python -m pytest tests/repository/test_mvp_manifests.py -q` and observe the missing validator failure.
- [ ] Implement manifest discovery, required-field validation, relative-path existence checks, unique names, and forbidden private imports.
- [ ] Add one valid fixture and verify zero errors.
- [ ] Run the focused test and commit the repository contract.

### Task 2: English repository shell

**Files:** Rewrite `README.md`, `TOOLS.md`, and `docs/PROJECT_MAP.md`; create `scripts/doctor.ps1` and `scripts/test-all.ps1`.

**Interfaces:** Consumes all `mvp.json` files and produces a generated capability table plus repository-wide doctor/test commands.

- [ ] Add tests asserting the root README links every manifest and contains no mojibake replacement sequences.
- [ ] Observe failure against the current root documents.
- [ ] Write concise English onboarding, application selection, installation, and evidence-level documentation.
- [ ] Implement doctor and test aggregation without application-specific logic.
- [ ] Verify document and repository tests, then commit.

### Task 3: Platform I/O MVP integration

**Files:** Incorporate `video_platform/`, `video-platform.ps1`, uploader/downloader installers, tests, and docs from `codex/video-platform-io`; package them under `apps/platform-io/` with compatibility entrypoints.

**Interfaces:** Produces `platform-io download|login|upload|doctor|capabilities` and JSON receipts.

- [ ] Add manifest/launcher contract tests for the application path.
- [ ] Observe failure before adding the application package.
- [ ] Move or wrap the verified implementation without changing platform behavior.
- [ ] Run platform tests and real dependency doctor; record the existing honest platform evidence.
- [ ] Commit the independently runnable application.

### Task 4: Signal analysis and frame extraction MVPs

**Files:** Create `apps/signal-analysis/` and `apps/frame-extraction/`; migrate the relevant FFmpeg scripts from `.claude/skills/ref-analyze/scripts/` behind separate launchers.

**Interfaces:** Signal analysis produces `cuts.json` and `loudness.json`; frame extraction consumes a video plus optional cuts file and produces `frames/manifest.json`.

- [ ] Write contract tests proving signal analysis never creates frames and frame extraction never computes loudness.
- [ ] Observe both failures before migration.
- [ ] Implement English launchers and deterministic output manifests.
- [ ] Verify each focused suite and one adjacent cuts-to-frames integration.
- [ ] Commit each MVP separately.

### Task 5: Transcription MVP

**Files:** Create `apps/transcription/`; migrate `tools/transcribe.py`, `tools/transcribe_funasr.py`, and `tools/transcribe_dispatch.py` behind one engine-adapter CLI.

**Interfaces:** Produces transcript JSON/SRT from one media input; engine selection is a strategy and model cache remains external.

- [ ] Write failing routing, output verification, missing-model, and redaction tests.
- [ ] Implement a stable English CLI and application-local installer.
- [ ] Preserve existing engines as adapters without copying model files.
- [ ] Verify focused tests and one FFmpeg audio-input integration.
- [ ] Commit the MVP.

### Task 6: Video editing MVP

**Files:** Create `apps/video-editing/`; migrate silence cutting, reframing, and vertical conversion scripts.

**Interfaces:** Produces exactly one requested derivative and a receipt; never overwrites the input.

- [ ] Write failing command-construction and input-protection tests.
- [ ] Implement subcommands `silence-cut`, `reframe`, and `vertical` with English help.
- [ ] Add FFprobe output verification and hardware-encoder fallback evidence.
- [ ] Verify focused and adjacent integration tests.
- [ ] Commit the MVP.

### Task 7: Channel research MVP

**Files:** Move `research_mvp/` and relevant Bilibili utilities into `apps/channel-research/`; retain a root compatibility module only if tests require it.

**Interfaces:** Owns research workspace lifecycle and exported channel/video datasets.

- [ ] Extend existing domain tests to the new public application entrypoint and observe failure.
- [ ] Migrate the domain core, adapters, renderer, README, and manifest.
- [ ] Keep platform adapters replaceable and preserve domain evidence classifications.
- [ ] Run the full research suite and manifest validator.
- [ ] Commit the MVP.

### Task 8: Voice cloning and localization MVPs

**Files:** Create `apps/voice-cloning/` from `tools/tts-mvp/`; create `apps/localization/` from alignment and dubbing orchestrators.

**Interfaces:** Voice cloning owns the voice registry and synthesized clips. Localization owns only its manifest and composed derivative, consuming transcript/voice files through public formats.

- [ ] Write tests separating voice ownership from localization continuation state.
- [ ] Migrate engine adapters, English help, installers, and model-cache configuration.
- [ ] Wrap alignment/dubbing scripts behind a manifest-driven localization CLI.
- [ ] Verify focused suites and a substitute-voice adjacent integration.
- [ ] Commit each MVP separately.

### Task 9: Remotion Studio MVP

**Files:** Create `apps/remotion-studio/`; move reusable compositions from `tools/remotion-hello/`; leave concrete assets under `projects/`.

**Interfaces:** Owns a composition registry; `list`, `preview`, and `render` accept project-supplied data and output paths.

- [ ] Add tests that reusable source contains no hard-coded project asset path and every composition has metadata.
- [ ] Separate reusable card/shot templates from game-design and information-gap project data.
- [ ] Add English README, launcher, install, and render smoke test.
- [ ] Run TypeScript/build tests and manifest validation.
- [ ] Commit the MVP.

### Task 10: Artifact hygiene and final integration

**Files:** Update `.gitignore`; create `docs/mvp/<name>/` artifacts; remove tracked generated artifacts only after confirming source equivalents exist.

**Interfaces:** Produces a clean clone contract and final delivery ledger for every application.

- [ ] Add repository tests rejecting models, media, PID files, caches, browser profiles, and generated previews in reusable source paths.
- [ ] Update ignores and relocate only reusable source assets.
- [ ] Complete `vertical-slice-brief`, `capability-dag`, `capability-evidence`, and `delivery-ledger` for every MVP.
- [ ] Run all Python tests, manifest validation, PowerShell doctors, and Remotion checks; run `git diff --check` and inspect status.
- [ ] Commit the verified repository and merge the branch locally to `main` without including unrelated user changes.
