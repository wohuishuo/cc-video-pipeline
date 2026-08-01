# Edge-TTS Video Localizer Design

## vertical-slice-brief

- **Observable result:** One command processes videos strictly one at a time and publishes each completed Russian-dubbed, hard-subtitled MP4 into `russian/edge-final`.
- **Use cases:** resume a batch; synthesize Russian segments; assemble timeline audio; generate ASS; mix narration over the existing background bed; render MP4; skip verified outputs.
- **State owners:** each job directory owns its Edge-TTS clips and `edge-receipt.json`; `edge-final` owns published MP4 files.
- **Protected invariants:** one active video; one active segment synthesis; immutable `id/start/end`; atomic clips and final publication; translation-hash idempotency; partial jobs remain resumable.
- **Decision gates:** none. Voice defaults to `ru-RU-DmitryNeural` and remains a CLI option.
- **Non-goals:** translation, Qwen, uploads, parallel execution, production SLA.

## capability-dag

1. `translation-reader` — owner: job translation artifact; status: verified existing; hard dependency: valid `translation.ru.json`.
2. `edge-voice` — owner: Edge clip store; status: unproven; hard dependency: Edge-TTS adapter; output: one WAV per segment.
3. `timeline-mix` — owner: audio receipt; status: verified existing; hard dependencies: all clips and background bed.
4. `subtitle-render` — owner: final publisher; status: verified existing; hard dependencies: mix and ASS.
5. `serial-batch` — owner: batch coordinator; status: unproven; hard dependencies: nodes 1–4; policy: exactly one job and one segment at a time.

Edges: translation **Fact** → Edge voice; Edge clips **Fact** → timeline mix; translation **Fact** → ASS projection; mix + ASS **Command** → render; job order **Policy** → serial batch.

## capability-evidence

- Public contract: `run_edge_batch(manifest, voice, output_root)`.
- RED assertion: the coordinator must finish synthesize→mix→render for job A before starting job B.
- Focused tests: CLI contract, serial event order, resumable clip reuse, failure continuation.
- Adjacent integration: existing ASS, audio mix and FFmpeg renderer.
- Failure matrix: duplicate output skips; translation conflict invalidates receipt; partial clips resume; synthesis retries; repeated execution is idempotent.
- Non-goals: Edge service uptime and production-scale verification.

## delivery-ledger

- **Level:** DESIGNED
- **Evidence present:** existing translation/audio/subtitle/render contracts.
- **Evidence missing:** Edge adapter tests, serial coordinator tests, one real rendered video.
- **Substitutes:** fake Edge adapter in focused tests.
- **Unapproved decisions:** none.
- **Forbidden claims:** production verified, offline TTS, guaranteed Edge availability.

