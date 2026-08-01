# Source Manifest Transcription Implementation Plan

**Goal:** Publish reusable transcript artifacts from a Source Intake manifest, one media item at a time, then compose the public boundary into Graph Studio.

**Tech stack:** Python 3.12, standard-library contracts/storage, optional Faster Whisper adapter, PowerShell launcher, pytest, existing SQLite Graph Studio.

## Task 1: Contract owner

- Add `apps/transcription/transcription_app/contracts.py`.
- Test source-manifest loading, segment invariants, canonical fingerprints and transcript manifest validation.
- Commit after focused GREEN.

## Task 2: Serial transcript loop

- Add adapter protocol and deterministic fake in tests.
- Implement atomic per-item transcript/SRT publication, checkpoint receipt, replay and input conflict.
- Prove one-at-a-time order and failure isolation.

## Task 3: Production adapter and public app

- Add Faster Whisper adapter, CLI, portable `run.ps1`, installer, README and updated `mvp.json`.
- Public CLI must select adapter/model/device without importing Source Intake internals.

## Task 4: Graph composition

- Add folder/url transcription graph templates.
- Invoke Source Intake, verify the committed source, invoke Transcription and verify the transcript manifest.
- Preserve one worker/one child invariant and stable child operation IDs.

## Task 5: Browser projection

- Add transcribe workflow controls and accurate node/inspector/status projections.
- Verify folder-to-transcript in the real browser.

## Task 6: Evidence

- Run focused, adjacent and repository suites.
- Run a real installed Faster Whisper smoke on one short media file.
- Update capability evidence and delivery ledger without overstating translation/localization readiness.
