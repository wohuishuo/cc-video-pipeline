# Resource-aware Studio design

## Promise

Video Graph Studio may optionally compose the independent Resource Budget CLI so that a claimed workflow reserves one workspace execution slot and an operator-configured byte estimate before entering `RUNNING`. It renews that lease while the workflow is active and releases it after completion, failure or cancellation.

## State owners

- Resource Budget exclusively owns limits, reservations, generations, expiry and release facts.
- Durable Start Queue exclusively owns FIFO request and claim state.
- Workflow Run exclusively owns lifecycle and step checkpoints.
- Workflow Engine coordinates the three owners through public results; it does not copy budget state into Studio SQLite.

## Lifecycle

1. `CMD-RUN-START` durably enqueues without reserving resources.
2. The serial worker claims the oldest runnable item.
3. Before `RUNNING`, it reserves `studio-<run-id>` through `apps/resource-budget/run.ps1`.
4. Budget denial returns the claim to `QUEUED`, yields the process-wide execution gate and retries after a bounded delay.
5. An acquired lease is renewed on a background heartbeat.
6. Completion, failure and cancellation stop renewal and release the current generation.
7. Startup reconciliation releases active leases belonging to terminal runs. Interrupted queued work reacquires the same stable reservation.

## Failure semantics

- Budget denial is waiting, not workflow failure.
- Malformed/unconfigured/unavailable budget is also retained in the durable queue and made visible in run logs; operators may repair it without recreating the run.
- Heartbeat loss fences useful work: the active adapter receives cancellation and the run becomes `FAILED`, never `COMPLETED` without an active lease.
- Release errors are logged and later startup reconciliation retries them.
- An expired reservation with the same fingerprint may be reactivated with a higher generation; a changed fingerprint remains a conflict.

## Configuration

Resource composition is opt-in and requires a budget database plus a positive per-run byte estimate. TTL is explicit with a safe bounded default. Multi-workspace routing uses the admitted workspace ID; fixed mode uses its configured workspace; anonymous local mode uses `local`.

## Verification boundary

Deterministic tests cover acquire-before-running, denial/requeue, heartbeat fencing, all terminal releases and startup reconciliation. A real launcher drill composes Studio with a real Resource Budget SQLite database. This does not claim load-tested scheduling, distributed leases, cloud tenancy or production capacity policy.
