# Publication Batch Execution capability evidence

## Public contract and owner

`apps/publication-batch-execution/run.ps1 execute` consumes a Publication Batch Plan, its exact SHA-256 confirmation, a Credential Vault path, an output directory and an operation ID. The program owns `publication-batch-execution-receipt.json` and, only after complete success, `publication-batch-execution-manifest.json`. Publication continues to own each child receipt and manifest.

## RED evidence

- Contract and operation test collection first failed because `publication_batch_execution.contracts` and `publication_batch_execution.operation` did not exist.
- Child-boundary tests first failed because `publication_batch_execution.child_executor` did not exist.
- CLI tests first failed because the public launcher and command parser did not exist.
- Two malformed receipt boundaries initially raised untyped `TypeError` instead of a stable contract rejection.
- Studio tests first failed because the Release Execute template, adapters, verifier, controls and runtime registration did not exist.
- The 1280-pixel browser-shell regression test first failed because the nineteenth workflow widened the whole document instead of scrolling its selector.

Every RED failure was observed before its corresponding production change.

## Focused and adjacent evidence

- `python -m pytest --import-mode=importlib tests/publication_batch_execution_mvp -q` verifies contracts, preflight, strict serialization, continuation, unknown fencing, public child boundaries and CLI behavior.
- The adjacent integration invokes the real Publication and Credential Vault public launchers while substituting only the final platform boundary. It verifies two different external IDs and absence of persisted secret material.
- `python -m pytest --import-mode=importlib tests/video_graph_studio -q` verifies same-workspace Release admission, exact SHA confirmation, launcher argv, independent child and aggregate verification, runtime registration and browser controls.
- A real loopback browser drill at 1280 x 720 admitted a two-node `publication-batch-execute` Graph from completed Release run `5a9643d9-60ce-4e28-84f4-6ce03f512269` and batch SHA `9450c2cc7e5842d1494e16bb87338f57d8da4247c4fdb77867704b9fbc5049a5`. The run was intentionally not started.

## Failure matrix

| Case | Evidence |
| --- | --- |
| Duplicate | a complete matching receipt and manifest returns `DUPLICATE_COMPLETED` without invoking children |
| Conflict | changed plan bytes, confirmation or operation identity is rejected before platform contact |
| Stale | a completed child is reused only while its plan, media, metadata, receipt and manifest hashes still match |
| Reentry | ordinary failed children retry under the same stable child operation ID while later completed children remain reusable |
| Partial failure | the result is `FAILED` and no aggregate manifest is published |
| Uncertain outcome | `UNKNOWN` is persisted, replay returns `REJECTED_UNKNOWN`, and the child is never retried automatically |
| Cleanup | children run synchronously with measured maximum activity one; power-loss and descendant process-tree evidence remain missing |

## Contract pressure

Preflight rejects a batch-plan SHA mismatch, malformed or reordered items, missing child plans, unsupported platforms, non-private visibility, missing credential IDs and Vault paths outside the current user's home. Studio independently rechecks the aggregate, every batch item, derivative and metadata fingerprint, every child plan and result manifest, every external ID, stable operation identity and exact item order/count.

## Non-goals

The fake final platform boundary does not prove a YouTube account, network acceptance, rate-limit recovery or real publication. The browser drill proves admission and rendering only because starting it would contact a platform. Production power-loss, representative scale, additional platforms and hosted/mobile operation remain unverified.
