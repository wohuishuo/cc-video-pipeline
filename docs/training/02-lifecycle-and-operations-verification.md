# Lifecycle and Operations Verification

This tutorial shows how to turn a green feature test into honest operational evidence for a Graph Engineering system.

## 1. Start with typed state

A process manager needs distinguishable `PENDING`, `RUNNING`, `INTERRUPTED`, `FAILED`, `CANCELLED` and `COMPLETED` states. A generic success boolean cannot express safe restart or unknown external outcome.

## 2. Fence the previous process generation

On startup, the new server generation claims abandoned active work by changing it to `INTERRUPTED`. The fence must be idempotent and must not alter terminal runs. Never let the UI guess whether an old worker survived.

## 3. Preserve committed checkpoints

Resume must verify and retain every completed predecessor, then execute only the first missing or interrupted node. A loop uses the same rule for files, transcript segments, voice clips, creator pages and publication targets.

## 4. Exercise the real boundary

A useful recovery drill kills the actual service process tree while a durable node is active. Stopping only a shell wrapper is not evidence because its child can continue. Confirm the listener disappears and inspect durable state before restart.

## 5. Record provenance

Capture the run ID, correlation ID, adapter version, state versions, artifact count, receipt hash and cleanup result. Redact secrets. The evidence must say exactly which local or external boundary was exercised.

## 6. Separate levels of proof

- A deterministic test proves transition rules.
- A real process-loss drill proves the named local recovery path.
- A real platform operation proves only that adapter/platform combination.
- Representative service-level objectives, security checks, load tests, remote recovery and authenticated operations are needed for production verification.

See the [recorded Studio recovery drill](../project/evidence/video-graph-studio/recovery-drill.md) and the [engineering review checklist](../project/engineering/rules/review-checklist.md).
