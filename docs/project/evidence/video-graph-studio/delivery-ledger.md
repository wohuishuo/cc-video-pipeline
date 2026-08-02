# Video Graph Studio Delivery Ledger

| Field | Record |
| --- | --- |
| Supported completion level | `DOMAIN_VERIFIED` |
| Evidence present | graph/run/process contracts; SQLite idempotency; real child-process ordering and cleanup; real loopback HTTP; browser-to-API health and allowed-folder projection; browser-admitted folder intake; successful anonymous YouTube download through Source Intake and Platform I/O; failed inputs isolated with durable receipts; real four-step folder intake/transcription run; real six-step RU+KK translation run; real ten-step Source→ASR→Translation→Voice→Localization browser run with two FFprobe-verified MP4 derivatives |
| Evidence missing | crash/power-loss SQLite recovery drill; authenticated platform adapters; live Douyin creator-profile enumeration; load/security operations |
| Substitutes | fixed prepared-folder graph; local filesystem roots; test success adapters for API composition |
| Decisions unapproved | commercial tenancy, billing, remote authentication, paid fallback and automatic publication policy |
| Forbidden claims | no production verification; no social upload completion claim; no claim that the quiet source mix removes original speech |

## Translation graph live evidence

Browser run `7e50a83f-2f81-4c97-9d3b-505161c51aa8` completed all six owner steps on 2026-08-02: Source Intake, source verification, Faster Whisper Tiny CPU/int8, transcript verification, NLLB CPU translation to `ru-RU` and `kk-KZ`, and translation verification. It recorded 31 durable log rows and published Translation Manifest SHA-256 `829c7f1508ac2fb5b0fbab4ca6b15d0c0014b0bf3acb724d4c8bb1b4f2145e5e` with two `MACHINE` artifacts.

## Localization graph live evidence

Browser run `578fc2a5-0363-42cc-b475-c6183b976579` completed all ten owner steps on 2026-08-02. It recorded 55 durable log rows, rendered four Edge voice clips serially, composed two subtitle-burned RU/KK MP4 files serially and verified exact derivative coverage. Localization Manifest SHA-256: `2ba09deb1ddb73d3c876732bb4a6fa551dbdf0f0e384825e17dec0ae03110899`.
