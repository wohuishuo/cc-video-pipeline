# Edge Voice Rendering Loop Implementation Plan

**Goal:** Convert a Translation Manifest into durable per-segment voice clips, then compose the public capability into Graph Studio.

## Task 1: Contract and serial loop

- Add independent `apps/voice-rendering` contracts, operation and tests.
- Prove exact coverage, one active adapter, checkpoint reuse, failure isolation and conflict semantics.

## Task 2: Edge adapter and public boundary

- Add Edge TTS + FFprobe adapter, CLI, PowerShell launcher, installer, manifest and README.
- Accept repeatable `--voice <language>=<voice-id>` policies.

## Task 3: Graph/browser composition

- Continue translation graphs with `render-voice` and `verify-voice` nodes.
- Expose voice choice without moving clip state into Graph Studio.

## Task 4: Evidence

- Run focused/full suites and one real short Edge TTS clip.
- Record exact receipts and honest service/quality limitations before merging.
