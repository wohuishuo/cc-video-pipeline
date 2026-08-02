# Video Graph Studio Delivery Ledger

| Field | Record |
| --- | --- |
| Supported completion level | `DOMAIN_VERIFIED` |
| Evidence present | graph/run/process contracts; SQLite idempotency; real child-process ordering and cleanup; real loopback HTTP; browser-to-API health and allowed-folder projection; browser-admitted folder intake; successful anonymous YouTube download; real four-step transcription, six-step RU+KK translation and ten-step Source-to-Localization runs; real Douyin creator discovery; real two-step four-target publication planning; live process-tree crash, startup fence and same-run recovery |
| Evidence missing | power-loss/filesystem durability; authenticated publication adapters; hosted multi-tenant recovery; load/security operations |
| Substitutes | fixed graph templates; local filesystem roots; deterministic fake adapters for domain verification |
| Decisions unapproved | commercial tenancy, billing, remote authentication, paid fallback and automatic publication policy |
| Forbidden claims | no production verification; no social upload completion claim; no claim that the quiet source mix removes original speech |

## Translation graph live evidence

Browser run `7e50a83f-2f81-4c97-9d3b-505161c51aa8` completed all six owner steps on 2026-08-02: Source Intake, source verification, Faster Whisper Tiny CPU/int8, transcript verification, NLLB CPU translation to `ru-RU` and `kk-KZ`, and translation verification. It recorded 31 durable log rows and published Translation Manifest SHA-256 `829c7f1508ac2fb5b0fbab4ca6b15d0c0014b0bf3acb724d4c8bb1b4f2145e5e` with two `MACHINE` artifacts.

## Localization graph live evidence

Browser run `578fc2a5-0363-42cc-b475-c6183b976579` completed all ten owner steps on 2026-08-02. It recorded 55 durable log rows, rendered four Edge voice clips serially, composed two subtitle-burned RU/KK MP4 files serially and verified exact derivative coverage. Localization Manifest SHA-256: `2ba09deb1ddb73d3c876732bb4a6fa551dbdf0f0e384825e17dec0ae03110899`.

## Creator discovery graph live evidence

Browser run `63a3a21d-7d7f-42b2-a15e-27152ee39122` completed both Creator Discovery owner steps on 2026-08-02. It used a local authentication-file reference, enumerated the supplied Douyin profile to three canonical URLs, verified the manifest and recorded six durable log rows. Authentication content was absent from the capability receipt.

## Publication planning graph live evidence

Browser run `7141072c-396a-43de-ba31-460e5c130223` completed both Publication owner steps on 2026-08-02. It fingerprinted one local MP4 and metadata JSON, generated four private/draft target jobs, verified coverage and recorded six durable log rows. No platform was contacted.

## Lifecycle recovery evidence

Run `1f1e77ff-b557-4d20-89d0-e3dedb8af34d` was killed while the first creator-discovery node was durably `RUNNING`. Restarting the server against the same SQLite data root fenced the run and node to `INTERRUPTED`; resubmitting start for the same run ID recovered to `COMPLETED`, verified 75 canonical Douyin URLs and committed manifest SHA-256 `7056625a4b0229738c0687764edca0afd26f72954fda1dec3df260fe5bb3dac7`. See [the complete drill](recovery-drill.md).
