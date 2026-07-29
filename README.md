# Video Production MVPs

This repository is a Windows-first monorepo of small, independent video-production programs. Choose one result, install only that application, and run it without learning the rest of the repository.

## Applications

| Program | Result | Documentation |
|---|---|---|
| Platform I/O | Download or prepare uploads for YouTube, Bilibili, Douyin, and TikTok | [Open](apps/platform-io/README.md) |
| Transcription | Produce JSON and SRT transcripts | [Open](apps/transcription/README.md) |
| Signal Analysis | Detect cuts and measure loudness | [Open](apps/signal-analysis/README.md) |
| Frame Extraction | Produce interval or cut-aligned frame sets | [Open](apps/frame-extraction/README.md) |
| Video Editing | Remove silence, reframe, or make vertical derivatives | [Open](apps/video-editing/README.md) |
| Localization | Compose translation, dubbing, timing, and subtitles | [Open](apps/localization/README.md) |
| Voice Cloning | Register voices and synthesize speech locally | [Open](apps/voice-cloning/README.md) |
| Channel Research | Build reproducible channel and video datasets | [Open](apps/channel-research/README.md) |
| Remotion Studio | Preview and render reusable video compositions | [Open](apps/remotion-studio/README.md) |

## Start here

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install pytest
powershell -ExecutionPolicy Bypass -File .\scripts\doctor.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\test-all.ps1
```

Each application contains its own `README.md`, `install.ps1`, `run.ps1`, `mvp.json`, tests, and delivery evidence. Generated media belongs in an explicit output directory and is not source code.

## Repository rules

- Applications communicate through public CLIs and versioned files.
- An application may not import another application's private implementation.
- Cookies, browser profiles, models, downloaded media, and renders are never committed.
- A zero process exit code is not success unless the declared output is verified.
- Delivery levels are evidence labels, not marketing labels.

The repository architecture and migration plan are documented in `docs/superpowers/specs/2026-07-29-independent-video-mvp-repository-design.md`.
