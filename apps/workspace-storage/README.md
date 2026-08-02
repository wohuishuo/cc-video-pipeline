# Workspace Storage MVP

Workspace Storage independently owns deterministic filesystem namespaces and capacity decisions for each workspace. It is the storage-isolation foundation for a future multi-workspace Studio or mobile API; it does not own identity, authorization, Graph runs or media-domain artifacts.

Delivery level: `DOMAIN_VERIFIED`. Replay, workspace separation, path confinement, quota decisions, atomic persistence and a real two-workspace CLI lifecycle are verified locally. It is not a hard concurrent quota enforcer or production tenant store.

## Provision a workspace

```powershell
$registry = "$env:LOCALAPPDATA\VideoGraphStudio\workspace-storage.json"
$storage = "$env:LOCALAPPDATA\VideoGraphStudio\storage"

powershell -NoProfile -ExecutionPolicy Bypass -File .\apps\workspace-storage\run.ps1 provision `
  --registry $registry `
  --workspace-id local `
  --storage-root $storage `
  --quota-bytes 107374182400 `
  --json
```

The command creates three disjoint roots below `storage\workspaces\local`: `state`, `artifacts` and `temp`. Repeating the exact request returns `DUPLICATE_COMPLETED`; changing its storage root or quota returns a conflict.

## Resolve a confined path

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\apps\workspace-storage\run.ps1 resolve `
  --registry $registry `
  --workspace-id local `
  --kind artifacts `
  --relative-path localized\run-123\video.mp4 `
  --json
```

Callers provide a namespace kind and relative path only. Absolute, drive-relative, traversal and redirected namespace paths are rejected. The command resolves a location; the owning media program still writes and verifies its own artifact.

## Check current capacity

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\apps\workspace-storage\run.ps1 capacity `
  --registry $registry `
  --workspace-id local `
  --required-bytes 104857600 `
  --json
```

The query returns `ALLOWED` or `REJECTED_QUOTA` with current usage and available bytes. This is a serial preflight decision. Hard enforcement across concurrent writers requires a later reservation/lease owner or storage-platform quota.

## Boundary

Workspace Access owns who may act. Workspace Storage owns where one workspace may keep runtime state. Video Graph Studio's optional multi-workspace mode now consumes the public `describe` and `capacity` commands, creates separate state/artifact runtimes and never imports this package or edits its registry directly. Hard reservations, remote storage and production tenant isolation remain later capabilities.
