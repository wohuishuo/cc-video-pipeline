# Resource budget lease tutorial

Workspace Storage answers “how many bytes exist now?” Resource Budget answers “how many bytes and execution slots have active workflows already promised?” Keep those facts under separate owners.

## 1. Configure from a Storage capacity fact

```powershell
$storage = .\apps\workspace-storage\run.ps1 capacity `
  --registry $storageRegistry --workspace-id local --required-bytes 0 --json |
  ConvertFrom-Json

.\apps\resource-budget\run.ps1 configure `
  --database $budgetDatabase --workspace-id local `
  --byte-limit $storage.value.availableBytes --execution-slots 1 --json
```

## 2. Reserve before starting work

```powershell
.\apps\resource-budget\run.ps1 reserve `
  --database $budgetDatabase --workspace-id local --reservation-id $runId `
  --bytes 1073741824 --slots 1 --ttl-seconds 300 --json
```

Only `COMPLETED` or `DUPLICATE_COMPLETED` grants a lease. `REJECTED_BUDGET` means no workflow process may start.

## 3. Fence renew and release by generation

Renew with the current generation while the run remains active. Release the same generation on completion, failure or cancellation. If a process dies, TTL eventually returns capacity; a future Studio recovery adapter must reconcile its durable run state with the lease before resuming.

## 4. Reproduce the adjacent integration

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\drills\resource-budget.ps1
```

This proves local transactions and Workspace Storage policy composition. It does not prove distributed enforcement or that unrelated filesystem writers obey the reservation ledger.
