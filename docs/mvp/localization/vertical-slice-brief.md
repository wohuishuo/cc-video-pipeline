# Localization vertical slice brief

## Observable result

One Source Manifest, one Translation Manifest and one Voice Manifest produce one fingerprinted H.264/AAC MP4 for every language/media pair. Each derivative contains the selected voice, the original audio at a declared volume and burned subtitles.

## Owner boundary

Localization owns composition policy, serial continuation, derivative files, its receipt and its manifest. It does not own source discovery, transcription, translation text, voice identity, publication or Graph Studio run state.

## Inputs and outputs

| Direction | Contract |
| --- | --- |
| Input | Source Manifest v1 with verified media |
| Input | Translation Manifest v1 with exact JSON/SRT coverage |
| Input | Voice Manifest v1 with exact segment coverage |
| Policy | `sourceVolume` in the inclusive range `0..1` |
| Output | Localization Manifest v1 and `localization-receipt.json` |
| Output | H.264/AAC MP4 derivatives with hash, size, duration, dimensions and codecs |

## Failure and recovery

The loop processes one language/media pair at a time. Every item is checkpointed. A retry with the same operation and input fingerprints reuses valid derivatives; changed inputs under the same operation return `REJECTED_CONFLICT`. Partial MP4 files are never published.

## Honest limits

Original speech is only attenuated, not separated from ambience. Translation and voice quality remain properties of their upstream owners. No upload or production-scale claim is included.
