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
| 8 | Guarded multi-platform publication | prepared plan, exact-hash execute, private/draft evidence | Domain complete; authenticated platform evidence pending |
| 9 | Local lifecycle recovery | startup fence, same-run resume, retained checkpoints, real process-loss drill | Complete for local process loss; power-loss evidence pending |
| 10 | Durable multi-run admission | FIFO start requests, serial drain, cancellation isolation, restart requeue | Complete for local control plane |
| 11 | Hosted/mobile foundation | auth, tenancy, remote storage, resource budgets, security evidence | Pending |

No later slice may move upstream ownership into Graph Studio for convenience.
