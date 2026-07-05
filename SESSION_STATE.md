# Session State - 2026-07-05

Repo: `https://github.com/wohuishuo/cc-video-pipeline`

Branch: `codex/information-gap-xiaolin-rebuild`

Latest pushed before this handoff note:

- `2ea044d fix(video): audit full timeline audio and layouts`
- This handoff update should be pushed as a newer commit on the same branch.

## Current Focus

Project: `projects/information-gap-business`

Goal: make a Xiaolin-style information-gap business explainer using the user's two pasted source documents as the main source material. The Remotion implementation is still a rough visual system, not a final Xiaolin-level edit.

## What Is Done

- Nahida so-vits local voice path exists under `nahida/`.
- Main narration exists locally:
  - `projects/information-gap-business/audio/information-gap-nahida-sovits.wav`
  - `projects/information-gap-business/audio/information-gap-nahida-sovits-mix.wav`
- Remotion composition exists:
  - `tools/remotion-hello/src/informationGap.tsx`
  - composition id: `information-gap-audio`
- Audio bug fixed:
  - removed added scene-boundary hard pauses from `tools/audio_xiaolin_mix.py`
  - mixed duration equals voice duration: `1358.568s`
  - added audible music bed generation through `tools/music_bed.py`
- Timing bug fixed:
  - Remotion narration duration is `1358.568s`
  - opening visual/caption timing uses scaled script time, not a separate hardcoded real-time clock
- Validation hook added:
  - `.githooks/pre-commit`
  - `tools/audit_information_gap.py`
  - checks music delta, hard silences, Remotion duration, and scaled opening timing
- Full-scene visual contact sheet generated locally:
  - `projects/information-gap-business/full-audit-contact-sheet.jpg`

## Validation Already Run

Commands that passed:

```powershell
& .\tools\.venv\Scripts\python.exe .\tools\audit_information_gap.py `
  --voice .\projects\information-gap-business\audio\information-gap-nahida-sovits.wav `
  --mixed .\projects\information-gap-business\audio\information-gap-nahida-sovits-mix.wav `
  --remotion .\tools\remotion-hello\src\informationGap.tsx
```

Result:

```text
voice_duration: 1358.568
mixed_duration: 1358.568
mixed_hard_silences: []
remotion passes: true
```

Rendered preview clips were also checked:

- `tools/remotion-hello/audio-preview-open-fullfix.mp4`
- `tools/remotion-hello/audio-preview-mid-fullfix.mp4`
- `tools/remotion-hello/audio-preview-end-fullfix.mp4`

Each rendered clip passed `video_hard_silences: []`.

## Local Files Not In Git

Large generated files are intentionally not committed:

- Nahida model/checkpoint files under `nahida/`
- Remotion rendered preview mp4 files under `tools/remotion-hello/`
- generated narration/mix wav/mp3 files under `projects/**/audio/`
- Wangluo/guzhenren/cos generated media under `projects/`
- `tools/jianying-mcp/` local clone/venv/material sandbox

These are local machine assets. On a new computer, reinstall/regenerate them from scripts or copy them manually if exact local outputs are needed.

## What Still Needs Work

The user is not happy with the current video quality. Current state is a runnable Remotion skeleton with corrected audio/timing, but not a final Xiaolin-quality video.

Next work should be:

1. Replace generic evidence-card backgrounds with more varied reconstructed pages and real B-roll-like assets.
2. Build section-level shot plans for all 38 scenes, not only the first minute.
3. Add real transcript captions beyond the opening instead of scene-title captions.
4. Add music arrangement sections, not just a continuous generated bed.
5. Render and inspect full-video or multiple section previews before claiming progress.
6. Keep using `tools/audit_information_gap.py` and the full contact sheet before committing.

## Useful Commands

```powershell
cd C:\Users\艾莉\Videos\cc视频剪辑
git switch codex/information-gap-xiaolin-rebuild
git pull
git config core.hooksPath .githooks
.\tools\setup.ps1
```

Render current audio composition preview:

```powershell
cd C:\Users\艾莉\Videos\cc视频剪辑\tools\remotion-hello
$env:npm_config_cache='C:\Users\艾莉\.npm-cache'
npx remotion render src/root.tsx information-gap-audio audio-preview-open-fullfix.mp4 --frames=0-2699 --codec=h264
```
