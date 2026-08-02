# Operations Readiness Delivery Ledger

| Field | Record |
| --- | --- |
| Supported completion level | `DOMAIN_VERIFIED` for local lifecycle recovery only |
| Evidence present | typed run/step state; optimistic versions; idempotent startup fence; deterministic restart tests; real server process-tree loss; same-SQLite restart; same-run resume; ordered logs and artifact SHA; clean listener shutdown; digest-only workspace credentials; real secure loopback scope separation and wrong-workspace denial |
| Evidence missing | abrupt machine power loss; filesystem corruption recovery; backup/restore; remote database failover; tenant isolation; credential-vault recovery; resource/load budgets; authenticated upload reconciliation; alerting and service-level objectives |
| Safe substitutes | single local worker; loopback-only listener; local SQLite; explicit private/draft publication policy |
| Decisions unapproved | hosted topology, tenant model, secret store, billing meter, retention policy, operator roles and incident policy |
| Forbidden claims | no production readiness; no high availability; no disaster recovery; no unattended public publishing; no commercial security certification |

## Promotion gates

1. Threat model and attack-oriented admission review beyond the completed local composition test.
2. Tenant-scoped artifact/database access test.
3. Secret custody, rotation and redaction test.
4. Representative CPU/GPU/network workload budget and cancellation test.
5. Backup, restore and corrupt-state quarantine drill.
6. Authenticated private publication plus unknown-outcome reconciliation on each claimed platform.
7. Measured service-level objectives, alerting and an operator recovery runbook.
