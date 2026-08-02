# Studio guarded-publication execution drill

On 2026-08-02, `scripts/drills/studio-guarded-publication.ps1` exercised two real Studio Graphs and three independent public boundaries without contacting a social platform.

1. Publish Plan created one private YouTube job with credential reference `youtube-main`.
2. Publish Execute named that completed plan run and supplied its exact committed SHA-256.
3. Publication asked Credential Vault to verify provider `youtube` and inject the recovered value into one fake Platform I/O child.
4. Execution and verification accepted only the committed manifest with non-empty external ID.

| Fact | Result |
| --- | --- |
| Plan run | `d816f0f1-caee-47d6-8d45-50ceed0f8dae` / `COMPLETED` |
| Execute run | `80cd5681-cd9f-4c27-b1a5-a4cca35294f2` / `COMPLETED` |
| External ID | `fake-youtube-private-001` |
| Visibility | `private-or-draft` |
| Credential plaintext persisted | `false` |

The deterministic suite also rejects wrong confirmations, nonterminal/foreign plan provenance, unsafe plan policy, missing credential references, changed manifest bytes and adapter success without an external ID.

This is `DOMAIN_VERIFIED` process composition. The platform child is deliberately fake, so this is not authenticated YouTube evidence and does not close unknown-outcome reconciliation, renewal, rate-limit or production operations gates.
