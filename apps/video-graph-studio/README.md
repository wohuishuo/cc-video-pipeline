# Video Graph Studio

Video Graph Studio is a local browser control plane for reusable video MVPs. It provides a ComfyUI-style workflow canvas while keeping workflow continuation, localization media and platform receipts under separate owners.

## Start

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File apps/video-graph-studio/run.ps1
```

The launcher opens `http://127.0.0.1:8765`. It never binds to the LAN. To run without opening a browser:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File apps/video-graph-studio/run.ps1 -NoBrowser -Port 8765
```

Choose a folder that already contains `russian/batch-manifest.json`, choose an Edge voice, and run the graph. Exactly one workflow and one child process execute at a time.

## Stop

Press `Ctrl+C` in the launcher terminal. The server requests cancellation for its active child, closes the HTTP listener and leaves completed checkpoints intact. Restarting fences an abandoned `RUNNING` step as `INTERRUPTED`; starting the run again resumes from the first missing checkpoint.

## Data root

The default data root is `%LOCALAPPDATA%\VideoGraphStudio`. Override it with `-DataRoot C:\path\to\studio-data`. `studio.db` owns graph run state and logs; localized videos remain in the source folder under `russian\edge-final` and remain owned by the localization MVP.

## Current evidence boundary

- Graph, run, process, HTTP and browser contracts are implemented and contract-tested.
- Edge localization is a replaceable online adapter and may return retryable service failures.
- YouTube, Bilibili, Douyin and TikTok download/upload controls remain later independent slices.
- No cloud account, billing, remote access or production platform claim is made.

