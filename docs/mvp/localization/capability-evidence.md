# Localization capability evidence

## Automated evidence

- Manifest tests reject source, transcript, translation, subtitle and voice fingerprint conflicts.
- Loop tests prove language-major/media-minor ordering, strictly serial execution, item checkpointing, replay, conflict rejection, failure cleanup and resume.
- FFmpeg tests prove explicit filter planning and probe-gated publication.
- Graph Studio tests prove the ten-node DAG, `sourceVolume` admission policy, exact derivative coverage and runtime registration.

## Real platform evidence — 2026-08-02

Browser-admitted Graph Studio run `578fc2a5-0363-42cc-b475-c6183b976579` completed all 10 nodes using one local video, Faster Whisper Tiny CPU/int8, NLLB CPU, Edge voices `ru-RU-DmitryNeural` and `kk-KZ-DauletNeural`, and local FFmpeg.

| Fact | Result |
| --- | --- |
| Durable log rows | 55 |
| Composition concurrency | 1 |
| Coverage | 2 languages × 1 media = 2 derivatives |
| Russian derivative | 18.933 s, 320×240, H.264/AAC, 1,177,544 bytes |
| Kazakh derivative | 18.933 s, 320×240, H.264/AAC, 1,169,516 bytes |
| Localization Manifest SHA-256 | `2ba09deb1ddb73d3c876732bb4a6fa551dbdf0f0e384825e17dec0ae03110899` |

An earlier direct public-launcher run also produced and visually inspected RU/KK frames with legible burned Cyrillic subtitles. Replaying that operation returned `DUPLICATE_COMPLETED` in 581 ms.

## Missing evidence

Long-form and multi-file quality sampling, crash/power-loss during FFmpeg, vocal separation, GPU performance, production load and authenticated publication remain unverified.
