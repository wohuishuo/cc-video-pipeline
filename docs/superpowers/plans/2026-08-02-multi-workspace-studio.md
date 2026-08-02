# Multi-Workspace Studio Composition Plan

## Goal

Compose Workspace Access, Workspace Storage and Video Graph Studio through public CLI boundaries so one loopback process can route authenticated requests into isolated per-workspace state and artifact roots.

## Contract

- Existing anonymous and fixed single-workspace secure launches remain compatible.
- Multi-workspace mode requires both access and storage registries.
- Every protected request is authorized for its requested workspace before runtime resolution.
- Workspace source roots come from Workspace Access; state/artifact roots come from Workspace Storage.
- Each workspace receives its own lazily created SQLite RunStore and process manager.
- Runtime caches and shutdown operate per workspace; no request can select another workspace's application without that workspace's credential.
- Public health reports routed mode without exposing registry contents.

## Implementation order

1. Add failing transport tests for two-workspace routing and cross-workspace denial.
2. Add failing runtime-router tests for root ownership, caching and shutdown.
3. Implement public CLI adapters and routing composition.
4. Add launcher mode validation and browser projection updates.
5. Run a real two-workspace HTTP drill with separate databases and run projections.
6. Update architecture, tutorials, roadmap and delivery evidence.

## Non-goals

No LAN binding, hosted identity provider, mobile UI, remote object storage, hard quota reservation, registry locking, billing or production tenant-isolation claim is made in this slice.
