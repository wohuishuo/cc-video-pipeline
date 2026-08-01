# Source Manifest Transcription Design

## Observable result

Given one committed Source Intake manifest, Transcription processes its media in stable order and publishes one `transcript-manifest.json`, one `transcription-receipt.json`, and one timestamped transcript JSON/SRT pair per completed media item.

## Ownership

Transcription owns transcript operations, item checkpoints, transcript text/timing artifacts and the transcript manifest. It reads but never edits the source manifest. Graph Studio owns continuation only. Translation, TTS, subtitle styling, mixing and publication are excluded.

## Contracts

- Input: Source Intake `source-manifest.json` schema v1 plus exact SHA-256.
- Command identity: `operationId`, source-manifest SHA-256, language policy, model and adapter identity.
- Item identity: the stable source media ID from Source Intake.
- Transcript: schema v1, source media identity/path, detected language, ordered positive-duration segments.
- Transcript manifest: source manifest path/hash and one verified artifact row per media item.
- Receipt: terminal class, input fingerprint, item outcomes, manifest path/hash and redacted error text.

## Loop behavior

The media set is immutable and sorted by source-manifest order. Each item writes into an identity-named directory. Partial files are unpublished. A checkpoint commits only after JSON and SRT validate. Same operation/input replays completed facts; changed input conflicts. Failed items remain explicit and never become transcript rows.

## Adapters

`FasterWhisperAdapter` is the first production adapter with selectable model/device/compute type. Domain tests use a deterministic fake preserving the same transcript contract. A future FunASR or cloud adapter replaces this port without changing the owner.

## Evidence gates

- Domain: contract validation, deterministic order, replay/conflict, item failure isolation, atomic output and public CLI tests.
- Adjacent: real child process invoked from Graph Studio and verified manifest checkpoint.
- Platform: one real media file transcribed with the installed Faster Whisper runtime.

## Non-goals

Translation quality, speaker diarization, word-perfect editing, parallel ASR, GPU resource scheduling and production model hosting are later capabilities.
