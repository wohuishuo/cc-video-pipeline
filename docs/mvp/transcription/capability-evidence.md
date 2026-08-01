# Transcription capability evidence

Domain tests prove source-manifest order and media validation, segment invariants, exact coverage, atomic output, serial execution, item failure isolation, retry checkpoint reuse, completed replay, changed-input conflict, lazy Faster Whisper loading, public CLI injection and portable launcher contracts.

Live evidence on 2026-08-02 used the public PowerShell launcher with Faster Whisper Tiny on CPU/int8. It transcribed a 19.014-second YouTube-derived MP4 into two English segments, JSON, SRT, manifest and SHA-256-backed receipt. A second live run completed the four-step browser graph `Intake -> Verify Source -> Transcribe -> Verify Transcript` as run `a21e90cc-c563-4f8f-98ba-b92cf27a8e24`.

Tiny misrecognized one word (`trunks` as `prompts`); executable completion is not a content-quality certification.
