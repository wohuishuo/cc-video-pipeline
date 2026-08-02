# Resource Budget MVP

Resource Budget independently owns durable byte and execution-slot reservation leases per workspace. SQLite `BEGIN IMMEDIATE` makes the capacity check and reservation one transaction, so competing local processes cannot both consume the same remaining budget.

Delivery level: `DOMAIN_VERIFIED`. Configuration replay/conflict, hard byte/slot denial, cross-process competition, generation fencing, renew/release replay, TTL reclamation and real Workspace Storage composition are verified locally. This is not distributed quota enforcement or billing.

```powershell
$database = "$env:LOCALAPPDATA\VideoGraphStudio\resource-budget.db"
.\apps\resource-budget\run.ps1 configure --database $database --workspace-id local --byte-limit 10737418240 --execution-slots 1 --json
.\apps\resource-budget\run.ps1 reserve --database $database --workspace-id local --reservation-id run-001 --bytes 1073741824 --slots 1 --ttl-seconds 300 --json
.\apps\resource-budget\run.ps1 renew --database $database --workspace-id local --reservation-id run-001 --expected-generation 1 --ttl-seconds 300 --json
.\apps\resource-budget\run.ps1 release --database $database --workspace-id local --reservation-id run-001 --expected-generation 2 --json
```

Use a new reservation ID for a new run. The same active ID and canonical reserve input replays; an expired stable ID with the same fingerprint reactivates at a higher generation so a crashed coordinator can recover. Changed input conflicts. Renew increments generation, while an exact lost-response retry replays. Release requires the current generation and is idempotent. Expired capacity is reclaimed inside the next transaction.

Workspace Storage remains the owner of actual filesystem usage. A caller may configure Resource Budget from its public capacity fact, but external writers can still consume disk outside these leases. Video Graph Studio optionally composes these leases before an admitted workflow enters `RUNNING`; Resource Budget still owns every reservation fact.
