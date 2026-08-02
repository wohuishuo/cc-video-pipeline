# Video Graph Studio Capability Evidence

## Public contracts and owners

Graph Definition owns graph revision/fingerprint. Workflow Run owns lifecycle/version. Workflow Process owns checkpoints. Local Worker owns the child handle. Run Log owns ordered messages. Dashboard is read-only.

## RED evidence

- Graph tests first failed because `studio` did not exist.
- Run tests first failed because `studio.store` did not exist.
- Engine tests first failed because `studio.adapters` did not exist.
- HTTP tests first failed because `studio.api` did not exist.
- Browser-shell tests first failed because web artifacts did not exist.
- Public-app tests first failed because launcher, manifest, README and CLI did not exist.

## Focused and adjacent evidence

| Boundary | Executable evidence |
| --- | --- |
| Graph | deterministic order; duplicate, endpoint and cycle rejection |
| Run owner | duplicate replay; fingerprint conflict; stale version; terminal replay; ordered logs |
| Process + real child | strict process order; max active process = 1; failure checkpoint; successor suppression; cancellation cleanup |
| HTTP + owners | real loopback requests for health, safe folders, create/replay/conflict/start and terminal projection |
| Browser | semantic regions, local assets, versioned commands and terminal polling contract |
| Source Intake composition | real public PowerShell child process; per-run output root; stable child operation ID; manifest fingerprint and media validation |
| Resource Budget composition | reserve before execution; generation renewal; bounded denial requeue; heartbeat fencing; terminal release; startup reconciliation; real public launcher and child |

## Failure matrix

| Case | Evidence/result |
| --- | --- |
| Duplicate | create and terminal replay return the original fact |
| Conflict | changed canonical input and stale expected version are rejected |
| Stale | optimistic version prevents overwrite |
| Reentry | terminal replay is idempotent |
| Partial failure | completed checkpoint remains; failed node terminates; successor stays pending |
| Cleanup | cancellation terminates the owned process and repeated cancel is safe |

## Current command

```powershell
tools\.venv\Scripts\python.exe -m pytest tests/video_graph_studio -q
```

Live browser evidence on 2026-08-02 loaded the loopback server and observed `System ready`; completed folder/URL acquisition and ten-step RU+KK localization; enumerated a bounded Douyin creator profile; and prepared a four-target private/draft publication plan. A separate real launcher drill reserved Resource Budget capacity before one Studio child and restored all capacity on terminal completion.

## Non-goals

The suite does not prove translation quality, authenticated platform upload, cloud durability, remote security, representative scale or commercial readiness.
