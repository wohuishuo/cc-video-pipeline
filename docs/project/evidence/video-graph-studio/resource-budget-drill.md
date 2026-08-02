# Resource-aware Studio drill

On 2026-08-02, `scripts/drills/resource-aware-studio.ps1` configured a real Resource Budget SQLite database for workspace `alpha`, created a durable Studio run and executed one real Python child only after reserving `4096` bytes and one execution slot through `apps/resource-budget/run.ps1`.

| Fact | Result |
| --- | --- |
| Run ID | `78dc6710-8217-4cd8-9d99-95c5ccc58fb7` |
| Run / step | `COMPLETED` / `COMPLETED` |
| Child marker | `completed` |
| Active reservations after terminal | `0` |
| Available bytes / slots after terminal | `4096` / `1` |
| Budget database SHA-256 | `60e5444cf01dd3d41bb319d750d13bff7f27c266397e229c6991dba99a1dd277` |

Deterministic tests additionally prove denial returns the same claimed run to its durable FIFO position, heartbeat failure prevents false completion, failures release, terminal startup reconciliation releases stranded active leases, and expired stable IDs reactivate only for the original fingerprint.

This supports local `DOMAIN_VERIFIED` composition. It is not a load test, power-loss proof, distributed lease, billing system, automatic disk estimator or production scheduling claim.
