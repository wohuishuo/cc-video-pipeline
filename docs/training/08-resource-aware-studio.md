# Resource-aware Studio tutorial

This tutorial connects two already independent owners: Video Graph Studio owns queue continuation, while Resource Budget owns lease truth.

## 1. Configure policy

```powershell
$budget = "$env:LOCALAPPDATA\VideoGraphStudio\resource-budget.db"
powershell -NoProfile -ExecutionPolicy Bypass -File apps/resource-budget/run.ps1 configure `
  --database $budget --workspace-id local --byte-limit 10737418240 `
  --execution-slots 1 --json
```

For secure or multi-workspace mode, repeat this command for each exact admitted workspace ID. Changed configuration is deliberately rejected; policy migration is a separate operator decision.

## 2. Launch Studio with lease composition

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File apps/video-graph-studio/run.ps1 `
  -ResourceBudgetDatabase $budget `
  -ResourceReservationBytes 1073741824 `
  -ResourceLeaseTtlSeconds 30
```

The byte estimate is fixed operator policy for this Studio generation. The browser cannot change it. Submit multiple Graphs normally: waiting entries stay lease-free, and the serial worker reserves only the claimed run.

## 3. Read lifecycle evidence

- `resource wait: REJECTED_BUDGET` means the same run remains queued; it is not failed.
- `resource lease lost` means renewal failed, active adapter cancellation was requested and the run is fenced to `FAILED`.
- `resource release pending reconciliation` means terminal run truth is retained and the next startup retries cleanup.

Inspect the independent capacity projection:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File apps/resource-budget/run.ps1 snapshot `
  --database $budget --workspace-id local --json
```

## 4. Reproduce the real proof

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/drills/resource-aware-studio.ps1
```

The proof requires a completed Studio run and child marker plus zero active reservations and restored byte/slot availability after terminal release. This validates local composition only; it does not establish distributed enforcement or production load limits.
