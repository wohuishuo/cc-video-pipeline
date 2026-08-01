# Transcription Delivery Ledger

| Field | Record |
| --- | --- |
| Supported completion level | `DOMAIN_VERIFIED` |
| Evidence present | source-manifest contract validation; timestamp/coverage invariants; strictly serial media loop; atomic item publication; failed-item isolation; retry reuse; operation replay/conflict; replaceable Faster Whisper adapter; portable public launcher; real Tiny CPU/int8 transcript; real Graph Studio four-step completion |
| Evidence missing | representative Chinese, Russian, noisy, multi-speaker and long-form quality; word timestamps and diarization; CUDA runtime evidence; clean-machine installer drill; interruption during model inference; load/resource budgets; production operations |
| Substitutes | deterministic fake ASR adapter for domain and failure tests; one short public English clip for live evidence |
| Decisions unapproved | default production model/device; GPU scheduling; model distribution; remote ASR provider; retention/privacy policy; human review threshold |
| Forbidden claims | no word-perfect or translation-quality claim; no GPU/platform integration claim; no production verification; no claim that Tiny is suitable for final creator output |

## Live evidence (2026-08-02)

| Run | Boundary | Result |
| --- | --- | --- |
| `real-youtube-tiny-1` | public Transcription PowerShell launcher | `COMPLETED`; two English segments, JSON, SRT, transcript manifest and receipt |
| `a21e90cc-c563-4f8f-98ba-b92cf27a8e24` | browser Graph Studio -> Source Intake -> Transcription | `COMPLETED`; 4/4 backend steps and 15 ordered log entries |

The live source was 19.014 seconds, 320x240 AV1 + Opus. Tiny/CPU execution included a model download on first use and took about 95 seconds for the standalone run. The content contained a known recognition error, so quality remains a separate evidence gate.
