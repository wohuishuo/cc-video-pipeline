# Video Automation Component Catalog

## 1. Workspace Access and Admission

- **Workspace Registry owns:** workspace identity, canonical allowed roots and credential lifecycle.
- **Admission consumes:** a redacted authorization decision for the requested workspace and scope.
- **Forbidden:** owning runs, media, platform credentials, billing or trusting a client-provided role.

## 2. Workspace Storage

- **Owns:** canonical storage-root binding, deterministic state/artifact/temp namespaces, path confinement and current-byte capacity decisions.
- **Consumes:** a bounded workspace ID reference; it does not decide whether the caller is authorized.
- **Forbidden:** owning identity, Graph runs, interpreting media artifacts or claiming hard concurrent quota enforcement without reservations.

## 3. Credential Vault

- **Owns:** encrypted local platform-secret custody, credential lifecycle and one-child environment injection.
- **Consumes:** credential ID, provider metadata and secret input by environment variable.
- **Forbidden:** interpreting platform login semantics, owning publication runs, returning plaintext/ciphertext or claiming hosted custody.

## 4. Client Presentation

- **Owns:** local selection state, layout, inspector focus and ephemeral notifications.
- **Consumes:** versioned run commands and read-only projections.
- **Forbidden:** editing SQLite, declaring adapter success, retaining platform secrets.

## 5. Client Contracts

- **Owns:** canonical command envelopes, endpoint/scope descriptions and declared client compatibility.
- **Consumes:** no workflow state; exports a transport-neutral bundle.
- **Provides:** canonical CLI `show` projected by Studio at public `GET /api/v1/contracts` before admission.
- **Forbidden:** reading SQLite, authenticating callers, owning run progress or letting client projections become authoritative.

## 6. Graph Definition

- **Owns:** immutable node/edge revision, canonical fingerprint and deterministic order.
- **Provides:** validated graph contract.
- **Forbidden:** executing work or owning run progress.

## 7. Workflow Run and Process

- **Run owns:** operation identity, lifecycle, optimistic version and terminal result.
- **Queue owns:** durable FIFO start-request order and active claim state.
- **Process owns:** current checkpoint, continuation and the one active child handle.
- **Process consumes:** an optional renewable Resource Budget lease reference before entering active execution.
- **Forbidden:** owning source, transcript, translation, voice, render or publication artifacts.

## 8. Source Intake

- **Owns:** source classification, deterministic discovery, `source-manifest.json` and intake receipt.
- **Consumes:** Platform I/O public download boundary in URL mode.
- **Forbidden:** transcription, translation and creator-profile enumeration disguised as a single download.

## 9. Transcription

- **Owns:** one transcript operation and timestamped transcript artifact for one media identity.
- **Consumes:** replaceable ASR adapter.
- **Forbidden:** translating text or editing Source Intake's manifest.

## 10. Translation

- **Owns:** source/target language pair, exact transcript fingerprint, translated segments and review status.
- **Consumes:** replaceable human, local-model or remote-model adapter.
- **Forbidden:** changing timestamps silently or synthesizing speech.

## 11. Voice Rendering

- **Owns:** target voice selection, per-segment clip checkpoints and synthesis receipt.
- **Consumes:** Edge, cloned-voice or future local TTS adapter.
- **Forbidden:** deciding translation wording or claiming final-video completion.

## 12. Video Composition

- **Owns:** subtitle style, audio-mix plan, media derivative and verification receipt.
- **Consumes:** source media, translation artifact and voice manifest.
- **Forbidden:** changing upstream text or publishing externally.

## 13. Platform I/O

- **Owns:** download/upload adapter execution and platform receipt.
- **Consumes:** credential profile only when anonymous operation is insufficient.
- **Forbidden:** public upload without an explicit execution policy.

## 14. Evidence and Operations

- **Owns:** append-only verification records, promotion level and known gaps.
- **Consumes:** committed receipts and external probes.
- **Forbidden:** turning missing evidence into a success claim.

## 15. Resource Budget

- **Owns:** per-workspace byte/slot limits, durable reservation identity, generation and expiry lifecycle.
- **Consumes:** an optional Workspace Storage capacity fact as configuration policy input; Studio consumes only public reservation lifecycle results.
- **Forbidden:** reading files, owning workflow completion, authenticating callers, billing or claiming distributed enforcement.
