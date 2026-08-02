# Durable Run Queue Implementation Plan

## Goal

Allow several browser-admitted graphs to wait durably while one Graph Engineering worker executes them strictly in order. Restart must requeue an abandoned queue claim and preserve each run's existing checkpoints.

## Ownership

- Workflow Run continues to own run lifecycle and node checkpoints.
- Durable Run Queue owns only start-request order and claim lifecycle.
- Workflow Engine owns the single active worker and cancellation handle.
- Browser projects queue/run state; it does not hold the queue.

## Contract

`CMD-RUN-START` becomes an idempotent durable enqueue command. It returns immediately. A queue entry moves `QUEUED -> RUNNING -> COMPLETED`; server startup changes abandoned queue `RUNNING` entries back to `QUEUED`. Terminal or cancelled runs cannot be re-executed.

## Implementation order

1. Add failing store tests for FIFO ordering, idempotent enqueue and restart requeue.
2. Add failing engine test for two submissions during one active run and strict maximum concurrency of one.
3. Implement the SQLite queue owner and serial worker drain.
4. Expose queue counts in health and a read-only queue projection.
5. Let the browser submit another graph immediately while monitoring the most recently selected run.
6. Verify restart, API, full regression, manifests and a real loopback queue run.

## Non-goals

No parallel execution, remote workers, priorities, billing, tenant scheduling or public upload policy changes in this slice.
