# Guarded Publication implementation plan

1. Define verified video, metadata, target and visibility contracts.
2. Prove deterministic planning, replay/conflict and secret-free manifests.
3. Prove exact-hash confirmation, serial execution, policy rejection, checkpointing and failure resume with a fake Platform I/O adapter.
4. Add a public launcher with separate `plan` and `execute` commands.
5. Add Graph Studio publication-plan controls; keep execution as an explicit plan-hash operation.
6. Record missing authenticated platform evidence without inflating delivery claims.
