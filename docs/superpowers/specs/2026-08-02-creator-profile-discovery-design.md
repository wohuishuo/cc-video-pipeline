# Creator Profile Discovery design

## Goal

Turn one supported creator/channel URL into a durable, reusable manifest of canonical video URLs without downloading media or owning downstream processing.

## Boundary

Creator Discovery owns profile enumeration, pagination continuation, deterministic deduplication, operation idempotency and the Creator Manifest. Platform I/O owns media download/upload. Source Intake owns downloaded media manifests. Graph Studio owns only workflow continuation.

## Contract

Input: HTTPS profile URL, inferred platform, maximum item count (`0` means all), optional Netscape cookie file fingerprint, operation ID and output directory.

Output: `creator-manifest.json` with platform, requested URL, creator identity when available, ordered canonical video entries, truncation/completion state and adapter identity; `discovery-receipt.json` with cursor checkpoints and manifest hash.

## Adapters

- YouTube, Bilibili and TikTok: `yt-dlp --flat-playlist --dump-single-json`.
- Douyin: pinned F2 runtime, using its profile pagination API through a narrow JSON-lines helper.

Cookie material is passed only to the selected adapter. It is never emitted to logs, manifests or receipts.

## Recovery

Every page updates the receipt atomically. A retry with the same operation and input fingerprint continues from the last cursor when supported and deduplicates already committed IDs. Changed inputs conflict. An empty or failed discovery never publishes a manifest.

## Non-goals

Media download, creator monitoring, scheduling, translation, voice, composition, upload, account login and cloud tenancy are independent later compositions.
