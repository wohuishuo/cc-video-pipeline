# Translation delivery ledger

| Field | Evidence |
| --- | --- |
| Owner | Translation MVP |
| Delivery level | `DOMAIN_VERIFIED` |
| Observable result | Transcript Manifest plus ordered languages becomes exact editable translation JSON/SRT coverage, Translation Manifest and receipt |
| Evidence present | contract validation; deterministic serial order; one active adapter call; atomic publication; item checkpoint reuse; replay/conflict; public CLI; NLLB adapter seam; six-step Graph Studio admission and artifact verification; real offline NLLB CPU completion for RU and KK; 0.56-second duplicate replay |
| Substitutes | deterministic fake translator in domain/adjacent tests; proves semantics, not linguistic quality |
| Evidence missing | representative source and RU/EN/KK quality sampling; reviewed-text republish; GPU; clean-machine install; long/noisy media; crash recovery; commercial load/security |
| Forbidden claims | no human-quality translation claim; no dubbed-video claim; no subtitle burn-in claim; no cloud/mobile/production verification |

## Verification commands

```powershell
python -m pytest --import-mode=importlib tests/translation_mvp tests/video_graph_studio/test_translation_graph.py -q
python scripts/validate_mvp_manifests.py .
```

## Live runs

| Operation | Input | Result | Evidence |
| --- | --- | --- | --- |
| `real-nllb-en-multi-1` | one two-segment English Transcript Manifest; targets RU + KK; NLLB 600M CPU/batch 8 | `COMPLETED` in 97.7 seconds | Translation Manifest SHA-256 `42f5252e5b07e1ce4c0e505dd88aaa277c145375cfd024758ee400712a0ca05a`; two JSON/SRT artifact pairs; receipt exact coverage |
| identical replay | same operation and input fingerprint | `DUPLICATE_COMPLETED` in 0.56 seconds | no model load or translation calls |
| Graph run `7e50a83f-2f81-4c97-9d3b-505161c51aa8` | local folder; Faster Whisper Tiny CPU/int8; RU + KK; NLLB CPU | six of six steps `COMPLETED` | 31 durable logs; Translation Manifest SHA-256 `829c7f1508ac2fb5b0fbab4ca6b15d0c0014b0bf3acb724d4c8bb1b4f2145e5e` |

The input ASR error (`trunks` recorded as `prompts`) propagated into translations. The evidence proves execution and provenance, not content accuracy.
