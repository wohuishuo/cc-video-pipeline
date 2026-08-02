# Video Graph Studio Delivery Ledger

| Field | Record |
| --- | --- |
| Supported completion level | `DOMAIN_VERIFIED` |
| Evidence present | graph/run/process contracts; SQLite idempotency; durable FIFO start queue; queued cancellation isolation; real child-process ordering and cleanup; process-wide execution gate; optional Resource Budget reserve/renew/requeue/release/reconcile composition; real loopback HTTP and Client Contracts discovery; browser-to-API health and allowed-folder projection; secure fixed and multi-workspace admission; isolated per-workspace state/artifact roots; browser-admitted folder intake; successful anonymous YouTube download; real four-step transcription, six-step RU+KK translation and ten-step Source-to-Localization runs; real Douyin creator discovery; real two-step four-target publication planning; confirmed private YouTube execution Graph through Publication and Vault with a fake platform boundary; live process-tree crash, startup fence and same-run recovery |
| Evidence missing | power-loss/filesystem durability; representative resource/load limits; authenticated publication adapters; hosted identity and production tenant isolation; cross-workspace scheduling contract; attack-oriented security operations |
| Substitutes | fixed graph templates; local filesystem roots; deterministic fake adapters for domain verification |
| Decisions unapproved | commercial tenancy, billing, remote authentication, paid fallback and automatic publication policy |
| Forbidden claims | no production verification; fake-platform execution is not social upload completion; no claim that the quiet source mix removes original speech |

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

## Durable queue evidence

Loopback HTTP runs `cfa0115e-2da3-44a3-9425-a4ea26efa256` and `c859bf34-65ee-46cb-833e-650fdb8a2542` were both accepted with HTTP `202`. The second remained durably queued while the first was blocked, then all six adapter calls completed in run order with maximum concurrency one. See [the complete drill](durable-queue-drill.md).

## Secure admission evidence

The real Workspace Access CLI admitted scoped read/write requests, rejected missing credentials, the wrong workspace and insufficient scopes, constrained folder browsing to the configured roots, and kept both plaintext credentials out of the persisted registry. See [the complete drill](secure-admission-drill.md).

## Multi-workspace routing evidence

One real loopback process authorized and initialized `alpha` and `beta`, committed the same operation identity into two separate SQLite stores, returned one isolated run per workspace, rejected a cross-workspace credential with HTTP `403` and closed its listener after the drill. See [the complete drill](multi-workspace-routing-drill.md).

## Resource-aware lifecycle evidence

A real Resource Budget launcher reserved capacity for Studio run `78dc6710-8217-4cd8-9d99-95c5ccc58fb7` before its real child process completed, then exposed zero active reservations and full byte/slot availability after the terminal path. See [the complete drill](resource-budget-drill.md).

## Guarded publication execution evidence

Plan run `7917ce20-0467-467a-8bcc-c8ce403db2c9` and execution run `1c10c5a1-b47c-46d6-ab16-0a9e836c5d35` both completed through Studio. Publication required the plan SHA, Credential Vault injected one provider-bound value into a fake platform child, and the verified manifest recorded external ID `fake-youtube-private-001`; plaintext persistence was false. See [the complete drill](guarded-publication-execution-drill.md).
