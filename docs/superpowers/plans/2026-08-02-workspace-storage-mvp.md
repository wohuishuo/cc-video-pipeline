# Workspace Storage MVP Plan

## Goal

Create an independently runnable owner for deterministic per-workspace state, artifact and temporary namespaces. This is the lowest unproven dependency for a future multi-workspace or mobile-facing Studio; it must not own identity, authorization, Graph runs or media-domain truth.

## Contract

- Provision one namespace below one canonical storage root from a bounded workspace ID.
- Repeating the same provision request replays; changed root or quota conflicts.
- State, artifact and temporary roots are disjoint and deterministic.
- Public path resolution accepts only a namespace kind plus a confined relative path.
- Capacity queries report current bytes and a bounded allow/deny decision.
- Registry changes use same-directory atomic replacement.

## Implementation order

1. Add failing domain tests for replay, isolation, confinement and capacity.
2. Add a failing CLI round-trip test.
3. Implement the standard-library registry and public launcher.
4. Add the independent MVP manifest, README and four evidence artifacts.
5. Run a real two-workspace CLI drill and record exact evidence.
6. Update repository, project architecture and roadmap indexes.

## Non-goals

No identity provider, access decision, cross-process lock, object storage, encryption, backup, hard concurrent reservation or Graph Studio routing is implemented in this slice.
