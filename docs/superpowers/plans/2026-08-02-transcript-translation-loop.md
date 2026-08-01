# Transcript Translation Loop Implementation Plan

**Goal:** Publish editable multilingual translation artifacts from a Transcript Manifest, one work item at a time, then compose the public boundary into Graph Studio.

**Tech stack:** Python 3.12, standard-library contracts/storage, optional Transformers + PyTorch NLLB adapter, PowerShell launcher, pytest, existing SQLite Graph Studio.

## Task 1: Contract owner

- Add `apps/translation/translation_app/contracts.py`.
- Test transcript-manifest loading, language normalization, translation document invariants and exact manifest coverage.
- Commit after focused GREEN.

## Task 2: Serial translation loop

- Add adapter protocol and deterministic fake in tests.
- Implement language-major/media-minor serial order, atomic per-item JSON/SRT, durable receipt, replay and input conflict.
- Prove at most one adapter call is active and failures cannot publish a complete manifest.

## Task 3: Production adapter and public app

- Add local NLLB adapter, CLI, portable `run.ps1`, installer, README and `mvp.json`.
- Support repeated `--target-language` values and model/device/batch policy.
- Do not require the network in domain or repository tests.

## Task 4: Graph composition

- Add folder/url translation templates after intake and transcription verification.
- Invoke Translation through its PowerShell launcher and verify every output fingerprint.
- Preserve one workflow worker and stable child operation IDs.

## Task 5: Browser projection

- Expose translation templates and multi-language controls.
- Render six graph steps without implying voice, subtitle burn-in or publication completion.

## Task 6: Evidence and publication

- Run focused, adjacent and repository suites.
- Run one real local NLLB smoke using the existing model cache.
- Update capability maps, evidence ledger, README diagrams and delivery labels.
- Commit, push, open a PR and merge only after verification.
