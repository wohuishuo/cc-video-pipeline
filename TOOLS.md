# MVP Command Guide

The public interface is the launcher inside each `apps/<name>/` directory. Paths under `tools/` and `.claude/skills/` are compatibility implementation details and may change.

| Goal | MVP | Command |
|---|---|---|
| Download or upload social video | Platform I/O | `apps/platform-io/run.ps1` |
| Upload one private YouTube video through the Data API | YouTube Publisher | `apps/youtube-publisher/run.ps1` |
| Connect a YouTube account into Credential Vault | YouTube OAuth Bootstrap | `apps/youtube-oauth-bootstrap/run.ps1` |
| Localize every video from a Creator Manifest serially | Creator Batch | `apps/creator-batch/run.ps1` |
| Plan every localized derivative for target platforms serially | Publication Batch | `apps/publication-batch/run.ps1` |
| Execute a confirmed private YouTube release batch serially | Publication Batch Execution | `apps/publication-batch-execution/run.ps1` |
| Transcribe media | Transcription | `apps/transcription/run.ps1` |
| Detect cuts or loudness | Signal Analysis | `apps/signal-analysis/run.ps1` |
| Extract frames | Frame Extraction | `apps/frame-extraction/run.ps1` |
| Cut silence or reframe | Video Editing | `apps/video-editing/run.ps1` |
| Translate and dub a video | Localization | `apps/localization/run.ps1` |
| Clone or synthesize a voice | Voice Cloning | `apps/voice-cloning/run.ps1` |
| Research channels and videos | Channel Research | `apps/channel-research/run.ps1` |
| Render coded video templates | Remotion Studio | `apps/remotion-studio/run.ps1` |

Run an application installer once, then use its launcher. Use `powershell -ExecutionPolicy Bypass -File` if local PowerShell policy blocks scripts.

Repository checks:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\doctor.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\test-all.ps1
```
