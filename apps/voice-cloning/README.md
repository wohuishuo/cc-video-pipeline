# Voice Cloning MVP

Registers local reference voices and synthesizes speech with a selected engine. Models and generated audio remain outside Git.

```powershell
.\install.ps1
.\run.ps1 --help
```

## Resumable Russian localization worker

The localization pipeline uses the Qwen3-TTS Base model in its dedicated CUDA
environment. Run it from the repository root so the authorized reference path
is resolved exactly:

```powershell
$reference = "projects/game-design-course/voice/reference-ru.wav"
$referenceText = "Сейчас я покажу, как превратить игровую идею в модель, которую можно рассчитать, объяснить команде и проверить на данных."
tools/qwen3tts-env/Scripts/python.exe -m localizer.qwen_voice_worker `
  --batch-manifest $batchManifest `
  --reference $reference `
  --reference-text $referenceText
```

Set `PYTHONPATH=apps/localization` if the localization package has not been
installed into that environment. The worker accepts only the authorized
reference path and exact transcript, loads one
`Qwen/Qwen3-TTS-12Hz-0.6B-Base` model and clone prompt for the whole batch,
and emits 24 kHz mono WAV files:

```text
russian/jobs/<video-id>/voice/
├── clips/0001.wav
├── clips/0002.wav
└── manifest.json
```

`manifest.json` binds every completed clip to its Russian source text, text and
audio SHA-256 fingerprints, measured duration, and fit status. It is replaced
atomically after every segment. Re-running the same command reuses only clips
whose text, hash, format, and duration still validate; missing, empty, corrupt,
stale, or interrupted segments are synthesized again. CUDA out-of-memory
errors clear the cache and retry only the affected segment at batch size one.
