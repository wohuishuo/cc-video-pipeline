# Handoff 2026-07-05 - Switch Computer

## Repository

- GitHub: `https://github.com/wohuishuo/cc-video-pipeline`
- Branch: `codex/information-gap-xiaolin-rebuild`
- Main project: `projects/information-gap-business`

## Current Status

The video project is runnable but not final.

What is solid now:

- Script and planning documents exist.
- Remotion composition exists and compiles.
- Nahida so-vits narration has been generated locally.
- Mixed audio now has no extra hard pauses inserted by our script.
- Music bed is generated and mixed into the audio file.
- Timing is driven by one scaled clock, so visual beats should follow the narration duration.
- A pre-commit audit checks hard silences, music delta, and Remotion audio duration.

What is still weak:

- The current video still uses too many generic evidence cards.
- Many middle and late scenes need actual reconstructed screens, more shot families, and richer transitions.
- Captions are only real timed captions in the opening; the rest still needs transcript-based captions.
- Music is a generated bed, not a hand-arranged Xiaolin-level score.

## Important Files

Remotion:

- `tools/remotion-hello/src/informationGap.tsx`
- `tools/remotion-hello/src/root.tsx`

Audio:

- `tools/audio_xiaolin_mix.py`
- `tools/music_bed.py`
- `tools/audit_information_gap.py`

Project docs:

- `projects/information-gap-business/script.md`
- `projects/information-gap-business/storyboard.md`
- `projects/information-gap-business/visual-system.md`
- `projects/information-gap-business/xiaolin-style-rebuild.md`
- `docs/workflows/information-gap-30min-video-sop.md`
- `SESSION_STATE.md`

Reference:

- `reference/小Lin-日本财团/analysis.md`

## Local Generated Files

These exist on the old computer but are intentionally not committed because they are large:

- `projects/information-gap-business/audio/information-gap-nahida-sovits.wav`
- `projects/information-gap-business/audio/information-gap-nahida-sovits-mix.wav`
- `tools/remotion-hello/audio-preview-open-fullfix.mp4`
- `tools/remotion-hello/audio-preview-mid-fullfix.mp4`
- `tools/remotion-hello/audio-preview-end-fullfix.mp4`
- `nahida/**/*.pth`, `nahida/**/*.pt`, `nahida/**/*.wav`, `nahida/**/*.zip`

Small visual proof committed or intended to commit:

- `projects/information-gap-business/full-audit-contact-sheet.jpg`

## Restore On New Computer

```powershell
git clone https://github.com/wohuishuo/cc-video-pipeline.git
cd cc-video-pipeline
git switch codex/information-gap-xiaolin-rebuild
git config core.hooksPath .githooks
.\tools\setup.ps1
```

Install Remotion dependencies if missing:

```powershell
cd tools\remotion-hello
$env:npm_config_cache='C:\Users\艾莉\.npm-cache'
npm install
npx remotion compositions src/root.tsx
```

If exact local audio/model outputs are needed, copy them manually from the old computer. They are not in Git.

## Next Recommended Work

1. Create a scene-by-scene visual plan for all 38 scenes before touching Remotion again.
2. Replace repeated evidence cards with scene-specific reconstructed pages:
   - 9.9 course page
   - chicken registration sheet
   - franchise cost sheet
   - recruiting chat and training contract
   - success-case wall with missing denominator boxes
   - delivery mismatch board
3. Generate transcript captions for the full narration.
4. Split music into section stems or at least section-level intensity changes.
5. Render at least three section previews and the full contact sheet before committing.
