# Publication Batch capability evidence

## Public contract and owner

`apps/publication-batch/run.ps1 plan` consumes a Localization Manifest, metadata-template JSON, ordered platform/account targets and optional bounded credential IDs. Publication Batch owns `publication-batch-receipt.json`, per-derivative rendered metadata and `publication-batch-plan.json`; Publication remains the only owner of each child `publication-plan.json`.

## RED evidence

- Contract collection failed with `ModuleNotFoundError: publication_batch`.
- Continuation collection failed with `ModuleNotFoundError: publication_batch.operation`.
- Public-child and CLI collection failed for missing `publication_batch.child_planner` and `publication_batch.cli`.
- Studio composition collection failed because `PublicationBatchPlanAdapter` did not exist.
- Browser-shell tests failed because Release templates, controls and asset versions did not exist.

Every RED failure was observed before its production implementation.

## Focused and adjacent evidence

- `python -m pytest --import-mode=importlib tests/publication_batch_mvp -q` passes 23 tests.
- The adjacent test invokes the real `apps/publication/run.ps1` launcher and verifies the committed Planning Receipt and two-target Publication Plan.
- `python -m pytest --import-mode=importlib tests/video_graph_studio -q` passes 97 tests, including twelve-node Graph admission, strict Release policy, public launcher argv, aggregate/child hash verification, runtime registration and browser controls.

## Failure matrix

| Case | Evidence |
| --- | --- |
| Duplicate | a complete receipt with matching derivative, metadata, child plan and aggregate hashes returns `DUPLICATE_COMPLETED` without processor calls |
| Conflict | changed target policy or changed operation identity under one output receipt returns `REJECTED_CONFLICT` without mutating the receipt |
| Stale | a changed child plan triggers only that derivative with the identical stable child operation ID |
| Reentry | completed later items survive an earlier item failure and are reused on retry |
| Partial failure | later derivatives are attempted, the result is `FAILED`, and no aggregate plan is published |
| Cleanup | child processes are synchronous and the operation records maximum active items one; descendant process-tree/power-loss evidence remains missing |

## Contract pressure

The loader rejects changed lineage manifests, changed derivative bytes, duplicate or incomplete language/media coverage, unknown/unbalanced metadata tokens, duplicate platforms, incomplete accounts and credentials without selected targets. Studio independently rechecks every derivative, rendered metadata file, child Publication Plan, target/account/credential-ID projection and aggregate count.

## Non-goals

Planning does not contact YouTube, Bilibili, Douyin or TikTok. These tests do not prove authenticated upload, public visibility, metadata quality, production recovery, representative scale or a mobile/hosted client.
