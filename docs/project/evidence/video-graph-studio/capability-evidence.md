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
| Complete creator catalog | a truncated or incomplete Creator Manifest cannot admit a campaign; the browser exposes a blocking warning and reload-all action |
| Local folder source | exact supported filenames, paths and sizes; existing OneDrive media roots; local source requires no upload |
| Translation policy | separately visible NLLB and DeepSeek choices with readiness projection and 20-locale catalog |
| Voice policy | explicit Edge, Qwen3 and original-audio providers; provider-specific voices; locale compatibility admission |
| Local delivery | allowed local output root is required; an empty destination matrix remains a valid completed workflow contract |
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

Live browser evidence on 2026-08-03 loaded the local-first seven-stage workspace, rejected a restored three-item truncated catalog, read four real videos from OneDrive Desktop, exposed NLLB/DeepSeek and Edge/Qwen3/original choices, and enabled an eight-local-output campaign with zero publication routes. Earlier drills completed folder/URL acquisition and ten-step RU+KK localization, enumerated a bounded Douyin profile and prepared a four-target private/draft publication plan.

## Non-goals

The suite does not prove translation quality, authenticated platform upload, cloud durability, remote security, representative scale or commercial readiness.
