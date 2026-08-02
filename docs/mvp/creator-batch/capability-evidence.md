# Creator Batch capability evidence

## Public contract and owner

`apps/creator-batch/run.ps1 localize` consumes a Creator Manifest plus non-secret processing policy. Creator Batch owns only `creator-batch-receipt.json` and `creator-batch-manifest.json`; child artifacts remain under their public MVP owners.

## RED evidence

- Contract suite initially failed with `ModuleNotFoundError: creator_batch`.
- Continuation suite initially failed with `ModuleNotFoundError: creator_batch.operation`.
- Public-adapter suite initially failed with `ModuleNotFoundError: creator_batch.child_pipeline`.
- Studio composition initially rejected `creator-batch-dub` and the browser-shell tests could not find the workflow.

## Focused and adjacent evidence

- `python -m pytest --import-mode=importlib tests/creator_batch_mvp -q` passes 17 tests.
- The real Creator Discovery operation commits a two-item Creator Manifest; the real Creator Batch operation consumes its exact hash and commits ordered coverage. Only the remote enumerator and media processor are deterministic substitutes.
- `python -m pytest --import-mode=importlib tests/video_graph_studio -q` passes 92 tests, including Graph admission, public launcher argv, hash verification, runtime registration, and browser controls.

## Failure matrix

| Case | Evidence |
| --- | --- |
| Duplicate | complete receipt + matching aggregate and child hashes returns `DUPLICATE_COMPLETED` without processor calls |
| Conflict | same operation ID with a changed language/voice policy returns `REJECTED_CONFLICT` before processor calls |
| Stale | changed Localization Manifest bytes cause only that creator item to re-enter the loop |
| Reentry | a failed receipt retains completed rows and retries incomplete rows under the same stable child prefix |
| Partial failure | later items are attempted; result remains `FAILED`; aggregate manifest is absent |
| Cleanup | each external process is synchronous and exactly one item is active; production descendant fencing remains missing evidence |

## Non-goals

No live multi-video platform download, online ASR/TTS, publication, power-loss durability, or production-scale claim is made by these deterministic tests.
