# Capability Catalog

See the [full video automation capability map](video-automation-capability-map.md) for build order, substitutes and evidence gates.

| Capability | Owns | Public result | Reusable boundary |
| --- | --- | --- | --- |
| Graph Definition | immutable graph revision and fingerprint | validated DAG and deterministic order | JSON contract |
| Workflow Run | operation identity, lifecycle and optimistic version | idempotent run fact | SQLite repository port |
| Workflow Process | required step continuation and checkpoints | terminal run fact | worker adapter port |
| Run Log | ordered append-only run messages | versioned log projection | query contract |
| Filesystem Browser | allowed-root path evidence | directory projection | filesystem adapter |
| Dashboard | read-only graph/run presentation | browser state | HTTP query contracts |
| Prepared Folder | manifest presence evidence | validated source fact | source adapter |
| Edge Localization | online TTS process invocation | localization receipt | localization launcher |
| Output Verification | inspectable output evidence | verified output fact | filesystem policy |

Capabilities may be tested with fixed specifications or fake adapters only when the substitute preserves authority and idempotency boundaries. Fake Edge output never proves Microsoft service availability or production publication.
