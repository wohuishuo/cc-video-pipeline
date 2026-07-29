# Transcription MVP

Converts one media file into transcript JSON and SRT. The dispatcher selects FunASR for Chinese and faster-whisper for other languages.

```powershell
.\install.ps1
.\run.ps1 input.wav --lang auto
```

Model downloads are cached outside Git.

## Localization CUDA adapter

The Russian-localization pipeline uses one resident `faster-whisper` `large-v3`
model on `cuda` with `float16`, Chinese language lock, VAD, and word timestamps.
For each job it writes `transcript.zh.json` and `transcript.zh.srt` under the
job directory; a failed transcription leaves the `transcription` receipt
retryable rather than completed.
