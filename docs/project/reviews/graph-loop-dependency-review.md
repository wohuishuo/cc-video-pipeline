# Graph and Loop Dependency Review

## Accepted conclusions

- Source Intake is the only writer of source manifests.
- Transcription must consume the source manifest and publish its own artifact; it must not append transcript state into the source receipt.
- Translation is a separate owner because wording may be edited or regenerated while timing/source identity remains stable.
- Voice rendering checkpoints each segment so a network failure does not repeat completed clips.
- Graph Studio stores continuation and projections, not media-domain artifacts.
- Workspace Storage owns deterministic state/artifact/temp namespaces and capacity projection; it does not authorize callers or interpret stored artifacts.
- The supplied Douyin link is a creator profile; enumeration is a separate capability before download, not an exception hidden in Platform I/O.

## Risks requiring evidence

| Risk | Required proof |
| --- | --- |
| ASR model/runtime mismatch | real one-file public launcher run and transcript schema validation |
| Poor translation quality | human-editable artifact, terminology policy and sampled review evidence |
| Edge service instability | bounded retry, per-segment checkpoint and failure receipt |
| CPU/GPU overload | resource-budget owner before any parallel mode |
| Duplicate publication | idempotent platform operation and post-upload reconciliation |
| Mobile/hosted expansion | replace local identity/registry adapters, prove client contract compatibility, then run production cross-tenant attack tests |

## Rejected shortcut

One giant “localize everything” command remains usable only as a compatibility adapter. It is not the target ownership model and may not become the graph's private implementation dependency.
