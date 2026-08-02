# Resource Budget Delivery Ledger

Resource Budget is `DOMAIN_VERIFIED` for durable local byte/slot leases and cross-process no-oversubscription. On 2026-08-02, Workspace Storage reported `200` bytes used and `800` available; the budget accepted `600` bytes/one slot, rejected an additional `300` bytes with exit `3`, released the first lease and accepted a replacement `800` bytes/one slot. Final active reservations: `1`; database SHA-256: `233a7181e8ca946bb3fed58ee4db9626d23ea783457b47c7015ee697cea43b32`.

An expired stable reservation can now reactivate with the same fingerprint at a higher generation, which supports coordinator recovery without weakening changed-input conflicts. Video Graph Studio composes the public CLI before active execution; the separate Studio drill is recorded in [resource-aware Studio evidence](../video-graph-studio/resource-budget-drill.md).

Power-loss, distributed storage, external-writer enforcement, representative load and production security evidence remain absent.
