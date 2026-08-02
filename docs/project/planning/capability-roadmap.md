# Capability Roadmap

Work-in-progress is limited to the lowest unproven dependency needed by the creator journey.

| Order | Vertical slice | Exit evidence | Status |
| --- | --- | --- | --- |
| 1 | Durable graph control plane | contracts, SQLite replay/conflict, serial real process, browser smoke | Complete |
| 2 | Folder and single-video URL intake | manifest/receipt, browser folder run, live YouTube run | Complete |
| 3 | Source manifest to transcript artifacts | one-media owner, fake-adapter tests, real ASR smoke, graph checkpoint | Complete |
| 4 | Transcript to editable translations | adapter-neutral schema, exact timing, editable machine output, real NLLB receipt | Complete |
| 5 | Translation to voice clips | serial segment receipts, selectable voices, failure resume, real Edge receipt | Complete |
| 6 | Assets to localized video | audio policy, subtitle render, FFprobe verification | Complete; live ten-step browser run |
| 7 | Creator-profile batch discovery | profile enumeration manifest, bounded pagination, dedup/replay | Complete; real bounded Douyin profile run |
| 8 | Creator Manifest to localized batch | strict item order, stable child IDs, partial continuation, stale repair, complete derivative coverage | Domain complete; live multi-item browser evidence pending |
| 9 | Localization Manifest to publication batch | stable derivative IDs, rendered metadata, private/draft child plans, exact coverage | Domain complete; live started Release Graph pending |
| 10 | Guarded multi-platform publication | prepared plan, exact-hash execute, private/draft evidence | Domain complete; authenticated platform evidence pending |
| 11 | Local lifecycle recovery | startup fence, same-run resume, retained checkpoints, real process-loss drill | Complete for local process loss; power-loss evidence pending |
| 12 | Durable multi-run admission | FIFO start requests, serial drain, cancellation isolation, restart requeue | Complete for local control plane |
| 13 | Workspace access owner | workspace identity, roots, hashed short-lived scopes, expiry and revocation | Domain complete; secure local Studio composition complete |
| 14 | Workspace storage owner | deterministic tenant namespaces, path confinement, capacity decision, atomic registry | Domain complete; multi-workspace Studio composition complete |
| 15 | Local multi-workspace routing | authorize before route, isolated SQLite/artifacts, shared global execution gate, cross-workspace denial | Domain complete; production tenant isolation not claimed |
| 16 | Local credential custody | env-only input, CurrentUser protection, redaction, rotation/revocation, child injection | Domain complete; guarded-publication composition complete |
| 17 | Credential-aware guarded publication | credential reference, provider match, exact confirmation, redacted serial child receipt | Domain complete; separate Studio plan/execute Graph composition complete; real authenticated platform proof pending |
| 18 | Authenticated real-platform adapters | accepted private/draft upload, external ID reconciliation, renewal and rate-limit evidence | YouTube desktop OAuth bootstrap and private resumable adapter domain-complete; authenticated channel evidence pending |
| 19 | Transport-neutral client contracts | canonical bundle, strict command envelopes, scoped endpoints, semantic compatibility | Domain complete; Studio HTTP discovery and browser consumption complete |
| 20 | Durable local resource budget | byte/slot leases, cross-process no-oversubscription, generation/TTL lifecycle, Storage capacity composition | Domain complete; Studio composition complete |
| 21 | Resource-aware Studio admission | reserve before start, renew during run, release on every terminal path, recovery reconciliation | Domain complete; production load and power-loss evidence pending |
| 22 | Publication Batch Plan execution | exact batch confirmation, whole-batch preflight, strict-serial children, resumable known failure, uncertain-outcome fence, aggregate verification | Domain complete; Studio browser composition complete; authenticated batch and power-loss evidence pending |
| 23 | Hosted/mobile admission | remote identity, HTTP contract discovery, remote secret custody, distributed budgets, attack review and security evidence | Pending |

No later slice may move upstream ownership into Graph Studio for convenience.
