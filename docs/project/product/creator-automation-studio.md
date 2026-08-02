# Creator Automation Studio

## Product promise

A creator can open a local browser, choose a folder or supported social-video URL, select one or more target languages, voices and publication targets, then observe a recoverable workflow that completes one item at a time on the computer.

The product is not a magic monolith. It is a visual control plane over independently runnable programs. Every green node means a named program committed an inspectable artifact or receipt.

## Primary journeys

1. **Acquire:** choose a folder or URL and receive a verified source manifest.
2. **Understand:** transcribe each media item and review timestamped source text.
3. **Localize:** create target-language translation, subtitles and speech using selectable adapters.
4. **Compose:** mix speech with retained ambience, burn or attach subtitles and verify the derivative.
5. **Publish:** prepare platform-specific upload plans, then require an explicit execution policy for external publication.

## Product invariants

- A workflow never marks success from a process exit code alone.
- One media item completes or fails before the next item begins by default.
- Switching the browser template never reuses another workflow's projected status.
- Credential Vault owns encrypted local secret custody; platform adapters receive one selected value only in their child environment and redact receipts.
- A translation can be replaced without rewriting source intake, transcription or platform code.
- Desktop browser, future hosted API and future mobile app consume the same versioned command/query contracts.
- Client Contracts exports that transport-neutral contract and rejects incompatible command envelopes without reading workflow state. Studio publishes the exact bundle at public HTTP discovery; the desktop browser consumes its version before enabling mutations.
- Queued work does not consume an execution lease; claimed work must hold and renew a Resource Budget lease before it may complete.

## Current accepted slice

Folder and single-video URL intake, source transcription, multilingual translation, Edge voice rendering, localized-video composition, creator-profile discovery, durable creator-profile batch localization, YouTube desktop account connection, guarded publication planning and separately confirmed private YouTube execution are browser-operable. Creator Batch consumes the ordered Discovery fact and runs the five content owners for exactly one URL at a time; failed items remain resumable while later items are attempted. Multiple Graphs can wait in durable serial queues. Anonymous YouTube intake and authenticated Douyin creator enumeration have named real-platform evidence. A killed local Studio process can fence and resume the same durable run after restart. Optional secure modes compose Workspace Access through its public launcher. Multi-workspace mode also composes Workspace Storage, routes an authorized workspace to separate state/artifact roots and retains one process-wide execution slot. Optional Resource Budget composition reserves bytes and one execution slot before `RUNNING`, renews during work, requeues bounded denial and releases every terminal path. YouTube OAuth Bootstrap obtains explicit system-browser consent and writes refresh credentials through Credential Vault without transferring secret ownership to Studio. Credential references then compose from Guarded Publication through Vault release into Platform I/O and the independent resumable API publisher. The creator loop and publication routes are domain verified; a live multi-item localization batch and real authenticated upload proof remain pending.

## Explicit non-goals for the current slice

Automatic public posting, commercial tenancy, production tenant isolation, remote identity or credential custody, billing, distributed quota enforcement, power-loss or hosted recovery, translation-quality certification and every-platform live proof are not yet claimed.
