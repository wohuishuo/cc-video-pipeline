# Multi-Workspace Studio Routing Drill

Date: 2026-08-02

Environment: Windows 11, real Workspace Access and Workspace Storage CLIs, one loopback Video Graph Studio process on `127.0.0.1:8775`

Reproduce with:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\drills\multi-workspace-studio.ps1
```

## Boundary under test

The drill provisions `alpha` and `beta` in independent access and storage registries, issues separate short-lived credentials, starts Studio in routed mode and sends the same `CMD-RUN-CREATE` operation identity to each workspace. Authorization happens before runtime resolution. Each runtime obtains source roots from Access and state/artifact roots from Storage.

## Observed results

| Probe | Result |
| --- | --- |
| Initial public health | `workspace-routed`; `initializedWorkspaces=0`; `multiWorkspace=true` |
| Alpha create | run `2dbeea5b-236e-46b6-9864-d3ba213c78f7` |
| Beta create | run `bdfb39be-b474-41bd-bb3a-048aace2be81` |
| Per-workspace projection | alpha list `1`; beta list `1` |
| Alpha credential with beta header | HTTP `403` |
| Final public health | `initializedWorkspaces=2`; active workers `0`; queued runs `0` |
| Alpha SQLite SHA-256 after WAL checkpoint | `a50dbe3d0665070a5bfd4e611789388a6a51366fd058993cd5ce4b7e6d1cd8fe` |
| Beta SQLite SHA-256 after WAL checkpoint | `84da097211e388b3521f1216610cce62e5397fad5562ea37c83e3968126d055d` |
| Credential persistence | both plaintext credentials absent; IDs `e2d9ad3a10d93e51`, `baaff307e98a0663` |
| Browser projection | bootstrap fragment removed; workspace field retained `alpha`; dummy credential displayed `Access denied` |
| Cleanup | process tree stopped; port `8775` closed |

A deterministic two-engine test separately blocked the first workspace adapter while starting the second and measured maximum adapter concurrency `1`. This proves the process-wide gate retained the established serial-execution invariant.

## What this proves

- One local Studio process can host more than one workspace without sharing RunStore, run projection or artifact root.
- A credential issued for one workspace cannot select another workspace runtime.
- Reusing an operation ID across workspaces does not conflict because idempotency state is workspace-scoped.
- Multiple workspace engines do not create parallel child-process execution.

## What this does not prove

This is not a production tenant-isolation claim. Local JSON registries lack multi-process locks, the filesystem lacks an evidenced ACL/encryption policy, quota checks are not hard reservations, cross-workspace scheduling is not globally FIFO, and no hosted identity, remote object store, load test or attack review is present.
