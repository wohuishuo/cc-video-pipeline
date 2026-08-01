# Video Automation Component Catalog

## 1. Client Presentation

- **Owns:** local selection state, layout, inspector focus and ephemeral notifications.
- **Consumes:** versioned run commands and read-only projections.
- **Forbidden:** editing SQLite, declaring adapter success, retaining platform secrets.

## 2. Graph Definition

- **Owns:** immutable node/edge revision, canonical fingerprint and deterministic order.
- **Provides:** validated graph contract.
- **Forbidden:** executing work or owning run progress.

## 3. Workflow Run and Process

- **Run owns:** operation identity, lifecycle, optimistic version and terminal result.
- **Process owns:** current checkpoint, continuation and the one active child handle.
- **Forbidden:** owning source, transcript, translation, voice, render or publication artifacts.

## 4. Source Intake

- **Owns:** source classification, deterministic discovery, `source-manifest.json` and intake receipt.
- **Consumes:** Platform I/O public download boundary in URL mode.
- **Forbidden:** transcription, translation and creator-profile enumeration disguised as a single download.

## 5. Transcription

- **Owns:** one transcript operation and timestamped transcript artifact for one media identity.
- **Consumes:** replaceable ASR adapter.
- **Forbidden:** translating text or editing Source Intake's manifest.

## 6. Translation

- **Owns:** source/target language pair, exact transcript fingerprint, translated segments and review status.
- **Consumes:** replaceable human, local-model or remote-model adapter.
- **Forbidden:** changing timestamps silently or synthesizing speech.

## 7. Voice Rendering

- **Owns:** target voice selection, per-segment clip checkpoints and synthesis receipt.
- **Consumes:** Edge, cloned-voice or future local TTS adapter.
- **Forbidden:** deciding translation wording or claiming final-video completion.

## 8. Video Composition

- **Owns:** subtitle style, audio-mix plan, media derivative and verification receipt.
- **Consumes:** source media, translation artifact and voice manifest.
- **Forbidden:** changing upstream text or publishing externally.

## 9. Platform I/O

- **Owns:** download/upload adapter execution and platform receipt.
- **Consumes:** credential profile only when anonymous operation is insufficient.
- **Forbidden:** public upload without an explicit execution policy.

## 10. Evidence and Operations

- **Owns:** append-only verification records, promotion level and known gaps.
- **Consumes:** committed receipts and external probes.
- **Forbidden:** turning missing evidence into a success claim.
