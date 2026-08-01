# Voice Rendering delivery ledger

| Field | Evidence |
| --- | --- |
| Owner | Voice Rendering MVP |
| Delivery level | `DOMAIN_VERIFIED` |
| Observable result | Translation Manifest plus exact voice policy becomes per-segment MP3 clips, Voice Manifest and receipt |
| Evidence present | 7 domain tests; serial ordering; one active synthesis call; clip hash/duration; failure isolation; retry reuse; replay/conflict; real Edge RU+KK service completion; tested eight-step Graph Studio composition and browser controls |
| Evidence missing | live eight-step browser completion; subjective voice review; rate-limit policy; long-form load; offline substitute; clean-machine install; production recovery/security |
| Forbidden claims | no voice cloning claim; no final-video/dubbing claim; no guaranteed Microsoft service availability; no production verification |

## Live operation

Operation `real-edge-ru-kk-1` first failed one of four clips after committing three. The identical retry rendered only the missing Russian clip and reused the three committed facts. Final durations were 8.736s, 3.456s, 8.856s and 2.184s; receipt maximum active synthesis was 1; manifest SHA-256 was `ccbfd566073f1b548fe02a9eb01fedda6be5f6a77af37575f1e786b5db802d56`.
