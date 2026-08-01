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

Choose one of the workflow templates:

- `Folder` or `URL` creates and verifies a Source Manifest.
- `Folder+ASR` or `URL+ASR` continues through a verified Transcript Manifest.
- `Folder+Translate` or `URL+Translate` continues through editable RU/EN/KK translation JSON/SRT.
- `Localize` runs the compatibility prepared-folder Edge workflow.

Exactly one workflow and one child process execute at a time. The six-step translation graph calls Source Intake, Transcription and Translation only through their public launchers.

## Stop

Press `Ctrl+C` in the launcher terminal. The server requests cancellation for its active child, closes the HTTP listener and leaves completed checkpoints intact. Restarting fences an abandoned `RUNNING` step as `INTERRUPTED`; starting the run again resumes from the first missing checkpoint.

## Data root

The default data root is `%LOCALAPPDATA%\VideoGraphStudio`. Override it with `-DataRoot C:\path\to\studio-data`. `studio.db` owns graph run state and logs; localized videos remain in the source folder under `russian\edge-final` and remain owned by the localization MVP.

## Current evidence boundary

- Graph, run, process, HTTP and browser contracts are implemented and contract-tested.
- Source Intake, Transcription and Translation manifest workflows are domain verified; one public YouTube download and one local Faster Whisper run have live evidence.
- Edge localization is a replaceable online adapter and may return retryable service failures.
- Creator-profile discovery and authenticated uploads remain later independent slices.
- No cloud account, billing, remote access or production platform claim is made.
