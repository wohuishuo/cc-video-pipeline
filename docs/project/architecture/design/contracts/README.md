# Public Contract Catalog

Public files and HTTP envelopes are the reusable seams. Graph Studio may invoke these boundaries but may not import another MVP's private implementation.

| Owner | Command input | Committed output | Current schema location |
| --- | --- | --- | --- |
| Graph Definition | node/edge graph revision | validated graph fingerprint | `apps/video-graph-studio/studio/contracts.py` |
| Workflow Run | `CMD-RUN-CREATE`, `CMD-RUN-START`, `CMD-RUN-CANCEL` | run/step/log projection | `apps/video-graph-studio/studio/api.py` |
| Source Intake | folder or supported URL policy | source manifest + receipt | `apps/source-intake/source_intake/contracts.py` |
| Creator Discovery | creator URL, page bound, optional auth reference | ordered canonical URL manifest + receipt | `apps/creator-discovery/creator_discovery/contracts.py` |
| Transcription | source manifest + ASR policy | transcript manifest + JSON/SRT + receipt | `apps/transcription/transcription/contracts.py` |
| Translation | transcript manifest + language set | translation manifest + JSON/SRT + receipt | `apps/translation/translation/contracts.py` |
| Voice Rendering | translation manifest + voice map | voice manifest + clips + receipt | `apps/voice-rendering/voice_rendering/contracts.py` |
| Localization | source, translation and voice manifests | H.264/AAC derivatives + localization receipt | `apps/localization/localizer/manifest_localizer.py` |
| Publication | media + metadata + target policies | immutable plan, then per-target receipt | `apps/publication/publication/contracts.py` |

## Evolution rules

1. Additive fields stay optional until all readers support them.
2. Breaking semantics require a new `contractVersion` or file `schemaVersion`.
3. Operation identity and canonical input fingerprint travel together.
4. Receipts record paths and hashes, never credential contents.
5. A consumer verifies upstream fingerprints before committing its own output.
6. Mobile and hosted clients use the HTTP boundary; they do not receive direct database access.
