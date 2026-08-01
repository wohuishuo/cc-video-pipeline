# Douyin Russian Localization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and run a resumable pipeline that turns the 74 verified `百年工业` source videos into Russian-dubbed, Russian-captioned derivatives while retaining a separated non-dialogue sound bed.

**Architecture:** `apps/localization` owns job orchestration and immutable stage receipts. Focused adapters own transcription, translation, Qwen voice synthesis, two-stem separation, audio alignment/mixing, caption replacement, rendering, and verification; adapters communicate only through versioned JSON/audio/video artifacts in each job directory. GPU-heavy stages run serially and keep their model resident across all pending jobs.

**Tech Stack:** Windows PowerShell 5.1, Python 3.12 orchestration venv, Python 3.11 CUDA worker venvs, faster-whisper/CTranslate2, Ollama `qwen3.5:9b`, Qwen3-TTS 0.6B Base, `audio-separator==0.44.5`, `MDX23C-8KFFT-InstVoc_HQ.ckpt`, FFmpeg 8.1/libass, NVIDIA NVENC, pytest.

## Global Constraints

- Never overwrite a source MP4; all outputs live under `downloads/douyin/creator-1338558235019738-full/russian`.
- The corrected source manifest contains exactly 74 target-account IDs.
- Preserve immutable segment IDs and timestamps; translation models never generate timestamps.
- Use the authorized Russian reference `projects/game-design-course/voice/reference-ru.wav` with exact text `Сейчас я покажу, как превратить игровую идею в модель, которую можно рассчитать, объяснить команде и проверить на данных.`
- Translate with Ollama `qwen3.5:9b`, `think=false`, temperature `0`, context `4096`, and JSON-schema output.
- Synthesize with Qwen3-TTS Base on the single RTX 4070 worker; never run competing GPU model workers.
- Separate with `audio-separator==0.44.5` and `MDX23C-8KFFT-InstVoc_HQ.ckpt`; retain the instrumental stem.
- Replace the full-width `y=580–720` band at 1280×720 and scale proportionally for 1270×720.
- Preserve each source's geometry and frame rate; output H.264/AAC using NVENC.
- Final audio target is approximately `-16 LUFS` with true peak no higher than `-1.5 dBTP`.
- A narration-only diagnostic is not an accepted final substitute for a failed separation stage.
- Keep existing unrelated dirty worktree changes untouched.

---

## File map

| File | Responsibility |
|---|---|
| `apps/localization/localizer/contracts.py` | Typed artifact/job records, fingerprints, atomic JSON I/O |
| `apps/localization/localizer/inventory.py` | Resolve the corrected 74-ID manifest to immutable source files |
| `apps/localization/localizer/asr.py` | Resident faster-whisper CUDA transcription stage |
| `apps/localization/localizer/translation.py` | Ollama structured translation and duration-fit rewrites |
| `apps/localization/localizer/voice.py` | Orchestrator-side Qwen worker invocation and clip validation |
| `apps/localization/localizer/qwen_voice_worker.py` | Resident Qwen3-TTS CUDA worker |
| `apps/localization/localizer/separation.py` | Orchestrator-side separator invocation and stem validation |
| `apps/localization/localizer/separator_worker.py` | Resident audio-separator GPU worker |
| `apps/localization/localizer/audio.py` | Clip alignment, sound-bed ducking, mix normalization |
| `apps/localization/localizer/subtitles.py` | Russian SRT/ASS creation and safe wrapping |
| `apps/localization/localizer/render.py` | Caption-band replacement, ASS burn-in, NVENC encode |
| `apps/localization/localizer/verify.py` | Media, duration, loudness, artifact, and ID verification |
| `apps/localization/localizer/cli.py` | `init`, stage commands, `pilot`, `run`, `status`, `verify` |
| `apps/localization/run.ps1` | Stable public launcher using `tools/.venv` |
| `apps/localization/install.ps1` | Idempotent Ollama/separator/runtime setup |
| `tests/localization/` | Focused unit, contract, recovery, and fixture integration tests |

### Task 1: Job contracts, inventory, and atomic recovery ledger

**Files:**
- Create: `apps/localization/localizer/__init__.py`
- Create: `apps/localization/localizer/contracts.py`
- Create: `apps/localization/localizer/inventory.py`
- Create: `tests/localization/test_contracts.py`
- Create: `tests/localization/test_inventory.py`

**Interfaces:**
- Consumes: corrected `video-urls.txt` and source MP4 filenames beginning with `[{id}]`.
- Produces: `Segment`, `StageRecord`, `JobRecord`, `BatchManifest`, `sha256_file()`, `atomic_write_json()`, `discover_jobs()`.

- [ ] **Step 1: Write failing contract and inventory tests**

```python
def test_stage_is_reusable_only_when_fingerprints_and_outputs_match(tmp_path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source-v1")
    output = tmp_path / "artifact.json"
    output.write_text("{}", encoding="utf-8")
    stage = StageRecord.completed(
        adapter="fixture@1",
        inputs={"source": sha256_file(source)},
        outputs={"artifact": str(output)},
    )
    assert stage.is_reusable({"source": sha256_file(source)})
    source.write_bytes(b"source-v2")
    assert not stage.is_reusable({"source": sha256_file(source)})

def test_discover_jobs_requires_exact_manifest_coverage(tmp_path):
    (tmp_path / "video-urls.txt").write_text(
        "https://www.douyin.com/video/111\nhttps://www.douyin.com/video/222\n",
        encoding="utf-8",
    )
    (tmp_path / "videos").mkdir()
    (tmp_path / "videos" / "[111] first.mp4").write_bytes(b"a")
    with pytest.raises(InventoryError, match="missing.*222"):
        discover_jobs(tmp_path / "video-urls.txt", tmp_path / "videos")
```

- [ ] **Step 2: Run tests and confirm RED**

Run: `tools/.venv/Scripts/python.exe -m pytest tests/localization/test_contracts.py tests/localization/test_inventory.py -q`

Expected: collection fails because `localizer.contracts` and `localizer.inventory` do not exist.

- [ ] **Step 3: Implement typed records, ISO timestamps, SHA-256 fingerprints, atomic temp-file replacement, and exact ID discovery**

```python
@dataclass
class StageRecord:
    status: Literal["pending", "running", "completed", "failed"]
    adapter: str
    inputs: dict[str, str]
    outputs: dict[str, str]
    started_at: str | None = None
    completed_at: str | None = None
    error: dict[str, str] | None = None

    def is_reusable(self, current_inputs: dict[str, str]) -> bool:
        return (
            self.status == "completed"
            and self.inputs == current_inputs
            and all(Path(path).is_file() and Path(path).stat().st_size > 0
                    for path in self.outputs.values())
        )
```

- [ ] **Step 4: Run focused tests and repository manifest tests**

Run: `tools/.venv/Scripts/python.exe -m pytest tests/localization/test_contracts.py tests/localization/test_inventory.py tests/repository -q`

Expected: all pass.

- [ ] **Step 5: Commit the independent ledger capability**

```powershell
git add apps/localization/localizer/__init__.py apps/localization/localizer/contracts.py apps/localization/localizer/inventory.py tests/localization/test_contracts.py tests/localization/test_inventory.py
git commit -m "feat(localization): add resumable job contracts"
```

### Task 2: Resident CUDA transcription adapter

**Files:**
- Create: `apps/localization/localizer/asr.py`
- Create: `tests/localization/test_asr.py`
- Modify: `apps/transcription/README.md`

**Interfaces:**
- Consumes: `list[JobRecord]`, source MP4, `model_name="large-v3"`, `device="cuda"`, `compute_type="float16"`.
- Produces: `transcript.zh.json` with immutable `Segment(id, start, end, text, words)` and `transcript.zh.srt`; updates only the `transcription` stage.

- [ ] **Step 1: Write a failing fake-model test**

```python
def test_transcribe_job_preserves_word_timestamps(tmp_path):
    fake = FakeWhisperModel([
        FakeSegment(0.5, 2.0, "工业机器人", [FakeWord(0.5, 1.0, "工业"), FakeWord(1.0, 2.0, "机器人")])
    ])
    result = transcribe_job(fake, make_job(tmp_path))
    assert result["segments"][0] == {
        "id": 1, "start": 0.5, "end": 2.0, "text": "工业机器人",
        "words": [{"start": 0.5, "end": 1.0, "word": "工业"},
                  {"start": 1.0, "end": 2.0, "word": "机器人"}],
    }
```

- [ ] **Step 2: Run RED**

Run: `tools/.venv/Scripts/python.exe -m pytest tests/localization/test_asr.py -q`

Expected: import failure for `localizer.asr`.

- [ ] **Step 3: Implement one-model batch loading, VAD, Chinese lock, word timestamps, SRT writing, transcript sanity checks, and per-job receipt updates**

```python
model = WhisperModel(model_name, device=device, compute_type=compute_type)
segments, info = model.transcribe(
    str(source), language="zh", word_timestamps=True,
    vad_filter=True, condition_on_previous_text=True,
)
```

- [ ] **Step 4: Pass focused tests**

Run: `tools/.venv/Scripts/python.exe -m pytest tests/localization/test_asr.py -q`

Expected: all pass without downloading a model because the test injects `FakeWhisperModel`.

- [ ] **Step 5: Commit**

```powershell
git add apps/localization/localizer/asr.py apps/transcription/README.md tests/localization/test_asr.py
git commit -m "feat(transcription): add resident CUDA batch adapter"
```

### Task 3: Structured Chinese-to-Russian translation adapter

**Files:**
- Create: `apps/localization/localizer/translation.py`
- Create: `tests/localization/test_translation.py`

**Interfaces:**
- Consumes: `transcript.zh.json`; Ollama base URL and model.
- Produces: `translation.ru.json` and `subtitles.ru.srt`, keyed by the unchanged segment IDs/timestamps.
- Public functions: `build_translation_request()`, `validate_translations()`, `translate_job()`, `rewrite_overflow_segments()`.

- [ ] **Step 1: Write failing tests for immutable timestamps, schema mismatch, Chinese residue, and numeral preservation**

```python
def test_merge_translation_keeps_timestamps_and_rejects_missing_ids():
    source = [Segment(1, 0.2, 2.4, "2026年增长10%", []), Segment(2, 2.5, 4.0, "工业机器人", [])]
    with pytest.raises(TranslationError, match="missing ids: 2"):
        merge_translations(source, [{"id": 1, "text_ru": "Рост на 10% в 2026 году"}])
    merged = merge_translations(source, [
        {"id": 1, "text_ru": "Рост на 10% в 2026 году"},
        {"id": 2, "text_ru": "Промышленные роботы"},
    ])
    assert (merged[0].start, merged[0].end) == (0.2, 2.4)
    assert "2026" in merged[0].text and "10%" in merged[0].text
```

- [ ] **Step 2: Run RED**

Run: `tools/.venv/Scripts/python.exe -m pytest tests/localization/test_translation.py -q`

Expected: import failure for `localizer.translation`.

- [ ] **Step 3: Implement the Ollama `/api/chat` client with JSON Schema, deterministic options, chunking, retry-by-chunk, ID merge, Cyrillic/numeral validation, and exact SRT timing**

```python
payload = {
    "model": "qwen3.5:9b",
    "stream": False,
    "think": False,
    "format": TRANSLATION_SCHEMA,
    "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                 {"role": "user", "content": json.dumps(rows, ensure_ascii=False)}],
    "options": {"temperature": 0, "num_ctx": 4096},
}
```

- [ ] **Step 4: Run tests with an in-process fake HTTP server**

Run: `tools/.venv/Scripts/python.exe -m pytest tests/localization/test_translation.py -q`

Expected: all pass without Ollama installed.

- [ ] **Step 5: Commit**

```powershell
git add apps/localization/localizer/translation.py tests/localization/test_translation.py
git commit -m "feat(localization): add structured Russian translation"
```

### Task 4: Resumable Qwen3-TTS voice worker

**Files:**
- Create: `apps/localization/localizer/voice.py`
- Create: `apps/localization/localizer/qwen_voice_worker.py`
- Create: `tests/localization/test_voice.py`
- Modify: `apps/voice-cloning/README.md`

**Interfaces:**
- Consumes: translated segments, Qwen model ID, Russian reference WAV/text.
- Produces: one 24 kHz mono WAV per segment plus `voice/manifest.json` containing source text, duration, SHA-256, and synthesis status.
- Worker command: `tools/qwen3tts-env/Scripts/python.exe -m localizer.qwen_voice_worker --batch-manifest $batchManifest --reference $referenceWav --reference-text $referenceText`.

- [ ] **Step 1: Write failing tests for clip reuse, missing clip retry, and over-duration classification**

```python
def test_voice_plan_reuses_only_matching_nonempty_clip(tmp_path):
    clip = tmp_path / "0001.wav"
    write_sine_wave(clip, seconds=1.0)
    plan = plan_voice_segments([ru_segment(1, 0.0, 1.2, "Тест")], tmp_path, prior_manifest={})
    assert [x.id for x in plan.pending] == [1]
    manifest = manifest_for(clip, text="Тест")
    plan = plan_voice_segments([ru_segment(1, 0.0, 1.2, "Тест")], tmp_path, manifest)
    assert plan.pending == []
```

- [ ] **Step 2: Run RED**

Run: `tools/.venv/Scripts/python.exe -m pytest tests/localization/test_voice.py -q`

Expected: import failure for `localizer.voice`.

- [ ] **Step 3: Implement the pure planning/validation adapter and CUDA worker**

```python
model = Qwen3TTSModel.from_pretrained(
    "Qwen/Qwen3-TTS-12Hz-0.6B-Base",
    device_map="cuda:0", dtype=torch.bfloat16, attn_implementation="sdpa",
)
prompt = model.create_voice_clone_prompt(
    ref_audio=str(reference), ref_text=reference_text, x_vector_only_mode=False,
)
```

The worker loads once, writes each clip through a temporary path, records completion immediately, catches CUDA OOM, clears cache, and retries that segment at batch size one.

- [ ] **Step 4: Run focused tests with a fake synthesizer**

Run: `tools/.venv/Scripts/python.exe -m pytest tests/localization/test_voice.py -q`

Expected: all pass without importing `qwen_tts` in the orchestration venv.

- [ ] **Step 5: Commit**

```powershell
git add apps/localization/localizer/voice.py apps/localization/localizer/qwen_voice_worker.py apps/voice-cloning/README.md tests/localization/test_voice.py
git commit -m "feat(voice-cloning): add resumable Qwen batch worker"
```

### Task 5: Resident two-stem separation worker

**Files:**
- Create: `apps/localization/localizer/separation.py`
- Create: `apps/localization/localizer/separator_worker.py`
- Create: `tests/localization/test_separation.py`
- Modify: `apps/localization/install.ps1`

**Interfaces:**
- Consumes: source MP4 audio and `MDX23C-8KFFT-InstVoc_HQ.ckpt`.
- Produces: `audio/vocals.wav`, `audio/no_vocals.wav`, and `audio/separation.json`; both stems are retained for QA and only `no_vocals.wav` is used as the Russian mix bed.
- Worker command: `tools/audio-separator-env/Scripts/python.exe -m localizer.separator_worker --batch-manifest $batchManifest --model-dir $separatorModelDir`.

- [ ] **Step 1: Write failing adapter tests**

```python
def test_separation_rejects_missing_or_too_short_instrumental(tmp_path):
    source_duration = 10.0
    with pytest.raises(SeparationError, match="missing instrumental"):
        validate_instrumental(tmp_path / "missing.wav", source_duration)
    stem = tmp_path / "stem.wav"
    write_sine_wave(stem, seconds=2.0)
    with pytest.raises(SeparationError, match="duration"):
        validate_instrumental(stem, source_duration)
```

- [ ] **Step 2: Run RED**

Run: `tools/.venv/Scripts/python.exe -m pytest tests/localization/test_separation.py -q`

Expected: import failure for `localizer.separation`.

- [ ] **Step 3: Implement idempotent setup and the resident `audio_separator.separator.Separator` worker**

```python
separator = Separator(
    model_file_dir=str(model_dir), output_dir=str(stem_dir),
    output_format="WAV", use_autocast=True,
)
separator.load_model("MDX23C-8KFFT-InstVoc_HQ.ckpt")
output_files = separator.separate(str(source))
```

`install.ps1` creates `tools/audio-separator-env` with Python 3.11, installs `audio-separator[gpu]==0.44.5`, downloads the model through the official CLI, and fails unless `--env_info` reports CUDA and CUDAExecutionProvider.

- [ ] **Step 4: Run focused tests**

Run: `tools/.venv/Scripts/python.exe -m pytest tests/localization/test_separation.py -q`

Expected: all pass without loading the real separator model.

- [ ] **Step 5: Commit**

```powershell
git add apps/localization/localizer/separation.py apps/localization/localizer/separator_worker.py apps/localization/install.ps1 tests/localization/test_separation.py
git commit -m "feat(localization): add instrumental separation adapter"
```

### Task 6: Timeline alignment and normalized audio mix

**Files:**
- Create: `apps/localization/localizer/audio.py`
- Create: `tests/localization/test_audio.py`

**Interfaces:**
- Consumes: Russian segment timings, Qwen WAV clips, `no_vocals.wav`, source duration.
- Produces: `audio/narration.wav`, `audio/mix.wav`, `audio/mix.json`; returns overflow segment IDs for concise rewrite.

- [ ] **Step 1: Write failing filter and fixture integration tests**

```python
def test_alignment_flags_more_than_35_percent_compression():
    assert classify_fit(tts_seconds=4.1, slot_seconds=3.0) == "rewrite"
    assert classify_fit(tts_seconds=3.9, slot_seconds=3.0) == "compress"

def test_mix_matches_source_duration_and_has_stereo_audio(tmp_path):
    fixture = build_audio_fixture(tmp_path, duration=3.0)
    result = build_mix(fixture)
    probe = ffprobe_json(result.mix_path)
    assert abs(float(probe["format"]["duration"]) - 3.0) < 0.05
    assert probe["streams"][0]["channels"] == 2
```

- [ ] **Step 2: Run RED**

Run: `tools/.venv/Scripts/python.exe -m pytest tests/localization/test_audio.py -q`

Expected: import failure for `localizer.audio`.

- [ ] **Step 3: Implement bounded `atempo`, silence padding, narration assembly, bed ducking, `amix`, and EBU R128 normalization**

```text
[bed]volume=-6dB[bedq];
[voice]loudnorm=I=-16:TP=-1.5:LRA=7[voicen];
[bedq][voicen]sidechaincompress=threshold=0.04:ratio=6:attack=15:release=350[ducked];
[ducked][voicen]amix=inputs=2:duration=longest:normalize=0,
loudnorm=I=-16:TP=-1.5:LRA=9[mix]
```

- [ ] **Step 4: Run focused and real-FFmpeg fixture tests**

Run: `tools/.venv/Scripts/python.exe -m pytest tests/localization/test_audio.py -q`

Expected: all pass; fixture output duration is within 50 ms.

- [ ] **Step 5: Commit**

```powershell
git add apps/localization/localizer/audio.py tests/localization/test_audio.py
git commit -m "feat(localization): align and mix localized narration"
```

### Task 7: Russian ASS creation and caption-band replacement renderer

**Files:**
- Create: `apps/localization/localizer/subtitles.py`
- Create: `apps/localization/localizer/render.py`
- Create: `tests/localization/test_subtitles.py`
- Create: `tests/localization/test_render.py`

**Interfaces:**
- Consumes: Russian segments, source dimensions/frame rate, final mix WAV.
- Produces: `subtitles.ru.ass`, temporary render, atomically finalized Russian MP4, `render.json`.

- [ ] **Step 1: Write failing wrapping, geometry, and filtergraph tests**

```python
def test_ass_wraps_to_two_lines_without_changing_timecodes():
    seg = Segment(1, 1.25, 5.5, "Очень длинное русское предложение для технического ролика", [])
    event = ass_event(seg, play_res=(1280, 720))
    assert event.start == 1.25 and event.end == 5.5
    assert event.text.count(r"\N") <= 1

def test_caption_band_scales_for_1270_width_source():
    graph = build_video_filter(width=1270, height=720, ass_path="ru.ass")
    assert "crop=1270:140:0:580" in graph
    assert "boxblur" in graph and "ass=" in graph
```

- [ ] **Step 2: Run RED**

Run: `tools/.venv/Scripts/python.exe -m pytest tests/localization/test_subtitles.py tests/localization/test_render.py -q`

Expected: imports fail for `localizer.subtitles` and `localizer.render`.

- [ ] **Step 3: Implement ASS escaping/wrapping and FFmpeg regional blur + dark plate + ASS filter**

```text
[0:v]split[base][region];
[region]crop=iw:140:0:ih-140,boxblur=12:2[blurred];
[base][blurred]overlay=0:H-h,drawbox=x=0:y=ih-140:w=iw:h=140:color=black@0.42:t=fill,
ass='subtitles.ru.ass'[v]
```

Encode with `h264_nvenc -preset p6 -tune hq -rc vbr -cq 19 -b:v 0`, source frame rate, AAC 192 kb/s, and faststart. Write to `.partial.mp4`, validate, then atomically move.

- [ ] **Step 4: Run tests with generated 1280×720 and 1270×720 fixtures**

Run: `tools/.venv/Scripts/python.exe -m pytest tests/localization/test_subtitles.py tests/localization/test_render.py -q`

Expected: all pass and generated frames show non-source pixels throughout the replacement band.

- [ ] **Step 5: Commit**

```powershell
git add apps/localization/localizer/subtitles.py apps/localization/localizer/render.py tests/localization/test_subtitles.py tests/localization/test_render.py
git commit -m "feat(localization): replace captions with Russian ASS"
```

### Task 8: Verification and batch CLI composition

**Files:**
- Create: `apps/localization/localizer/verify.py`
- Create: `apps/localization/localizer/cli.py`
- Modify: `apps/localization/run.ps1`
- Modify: `apps/localization/mvp.json`
- Create: `tests/localization/test_cli.py`
- Create: `tests/localization/test_recovery.py`

**Interfaces:**
- Consumes: batch root, stage adapters, optional `--id` pilot selector.
- Produces commands: `init`, `transcribe`, `translate`, `separate`, `voice`, `mix`, `render`, `pilot`, `run`, `status --json`, `verify --decode`.

- [ ] **Step 1: Write failing CLI/recovery tests**

```python
def test_resume_runs_only_lowest_unverified_stage(fake_pipeline, job):
    job.stages["transcription"] = completed_stage()
    job.stages["translation"] = failed_stage("schema")
    fake_pipeline.run(job)
    assert fake_pipeline.calls == ["translation", "separation", "voice", "mix", "render", "verify"]

def test_verify_requires_exact_74_id_mapping(batch_fixture):
    batch_fixture.remove_final("7588858424293641481")
    report = verify_batch(batch_fixture.root, decode=False)
    assert report.ok is False
    assert report.missing_ids == ["7588858424293641481"]
```

- [ ] **Step 2: Run RED**

Run: `tools/.venv/Scripts/python.exe -m pytest tests/localization/test_cli.py tests/localization/test_recovery.py -q`

Expected: imports fail for `localizer.cli` and `localizer.verify`.

- [ ] **Step 3: Implement stage commands, status JSON, per-stage locks, fail/retry classes, exact mapping checks, `ffprobe`, optional full decode, and loudness verification**

```powershell
$python = Join-Path $root "tools\.venv\Scripts\python.exe"
$env:PYTHONPATH = Join-Path $root "apps\localization"
& $python -m localizer.cli @Arguments
exit $LASTEXITCODE
```

- [ ] **Step 4: Run all localization tests and repository checks**

Run: `tools/.venv/Scripts/python.exe -m pytest tests/localization tests/repository -q`

Run: `powershell -ExecutionPolicy Bypass -File scripts/test-all.ps1`

Expected: all pass.

- [ ] **Step 5: Commit**

```powershell
git add apps/localization/localizer/verify.py apps/localization/localizer/cli.py apps/localization/run.ps1 apps/localization/mvp.json tests/localization/test_cli.py tests/localization/test_recovery.py
git commit -m "feat(localization): compose resumable Russian batch"
```

### Task 9: Public documentation and delivery evidence

**Files:**
- Modify: `apps/localization/README.md`
- Modify: `README.md`
- Modify: `TOOLS.md`
- Modify: `docs/mvp/localization/vertical-slice-brief.md`
- Modify: `docs/mvp/localization/capability-dag.md`
- Modify: `docs/mvp/localization/capability-evidence.md`
- Modify: `docs/mvp/localization/delivery-ledger.md`
- Create: `apps/localization/ATTRIBUTION.md`

**Interfaces:**
- Consumes: tested CLI and current evidence.
- Produces: reproducible install/run/status/verify documentation and explicit UVR/audio-separator attribution.

- [ ] **Step 1: Write failing repository assertions for launcher, docs, attribution, and delivery level**

```python
def test_localization_docs_expose_batch_contract(repo_root):
    readme = (repo_root / "apps/localization/README.md").read_text(encoding="utf-8")
    assert "pilot" in readme and "status --json" in readme and "verify --decode" in readme
    assert (repo_root / "apps/localization/ATTRIBUTION.md").is_file()
```

- [ ] **Step 2: Run RED**

Run: `tools/.venv/Scripts/python.exe -m pytest tests/repository -q`

Expected: new documentation assertion fails.

- [ ] **Step 3: Document exact commands, dependencies, artifact tree, recovery behavior, model licenses, and evidence limits**

```powershell
powershell -ExecutionPolicy Bypass -File apps/localization/install.ps1
powershell -ExecutionPolicy Bypass -File apps/localization/run.ps1 init --source-root "C:\Users\eugen\OneDrive\Documents\video\downloads\douyin\creator-1338558235019738-full"
powershell -ExecutionPolicy Bypass -File apps/localization/run.ps1 pilot --id 7590780099696364810
powershell -ExecutionPolicy Bypass -File apps/localization/run.ps1 run
powershell -ExecutionPolicy Bypass -File apps/localization/run.ps1 status --json
powershell -ExecutionPolicy Bypass -File apps/localization/run.ps1 verify --decode
```

- [ ] **Step 4: Run repository tests and diff checks**

Run: `tools/.venv/Scripts/python.exe -m pytest tests/repository -q`

Run: `git diff --check`

Expected: pass and no whitespace errors.

- [ ] **Step 5: Commit**

```powershell
git add README.md TOOLS.md apps/localization/README.md apps/localization/ATTRIBUTION.md docs/mvp/localization tests/repository
git commit -m "docs: document Russian localization workflow"
```

### Task 10: Install runtimes and prove the 37-second pilot

**Files:**
- Runtime outputs only under `downloads/douyin/creator-1338558235019738-full/russian/jobs/7590780099696364810`
- Runtime output: the single `.ru.mp4` in `downloads/douyin/creator-1338558235019738-full/russian/final/` whose filename starts with `[7590780099696364810]`.

**Interfaces:**
- Consumes: all verified capabilities and the shortest bilingual-caption source.
- Produces: one end-to-end pilot plus stage/verification receipts.

- [ ] **Step 1: Run idempotent installer and runtime doctors**

Run: `powershell -ExecutionPolicy Bypass -File apps/localization/install.ps1`

Expected: Ollama responds, `qwen3.5:9b` is present, Qwen worker reports CUDA, separator worker reports CUDA/Torch and CUDAExecutionProvider, FFmpeg reports libass and `h264_nvenc`.

- [ ] **Step 2: Initialize the corrected 74-job ledger**

Run: `powershell -ExecutionPolicy Bypass -File apps/localization/run.ps1 init --source-root "C:\Users\eugen\OneDrive\Documents\video\downloads\douyin\creator-1338558235019738-full"`

Expected: 74 jobs, no missing/extra/duplicate IDs.

- [ ] **Step 3: Run the pilot**

Run: `powershell -ExecutionPolicy Bypass -File apps/localization/run.ps1 pilot --id 7590780099696364810`

Expected: every stage becomes `completed`; no diagnostic substitute is used.

- [ ] **Step 4: Verify media and visual samples**

Run: `powershell -ExecutionPolicy Bypass -File apps/localization/run.ps1 verify --id 7590780099696364810 --decode --frames 5,18,30`

Expected: duration within 250 ms of source; one video and one stereo audio stream; 720p source geometry; decode errors zero; loudness/true peak pass; sampled lower Chinese/English captions are unreadable and Russian captions remain within the band.

- [ ] **Step 5: Record pilot evidence and commit only documentation changes**

Update `docs/mvp/localization/capability-evidence.md` and `delivery-ledger.md` to `DOMAIN_VERIFIED` only if every pilot gate passes.

```powershell
git add docs/mvp/localization/capability-evidence.md docs/mvp/localization/delivery-ledger.md
git commit -m "docs: record Russian localization pilot evidence"
```

### Task 11: Execute and verify all 74 jobs

**Files:**
- Runtime outputs only under `downloads/douyin/creator-1338558235019738-full/russian/`
- Modify after evidence: `docs/mvp/localization/capability-evidence.md`
- Modify after evidence: `docs/mvp/localization/delivery-ledger.md`

**Interfaces:**
- Consumes: pilot-proven pipeline and 74-job ledger.
- Produces: 74 final Russian MP4s, complete receipts, and batch verification report.

- [ ] **Step 1: Run all batch stages sequentially with model residency**

Run: `powershell -ExecutionPolicy Bypass -File apps/localization/run.ps1 run`

Expected: interruption-safe progress; completed stage artifacts are reused by fingerprint.

- [ ] **Step 2: Inspect status and retry only failures**

Run: `powershell -ExecutionPolicy Bypass -File apps/localization/run.ps1 status --json`

Expected: either 74 verified jobs or explicit stage-classified failures. Re-run `run`; it must schedule only the lowest unverified stages.

- [ ] **Step 3: Run exact ID/media/metadata verification**

Run: `powershell -ExecutionPolicy Bypass -File apps/localization/run.ps1 verify --decode`

Expected: 74 expected IDs, 74 unique final IDs, missing/extra/duplicate/partial/decode errors all zero, source-matching geometry and duration, and audio policy pass for all.

- [ ] **Step 4: Inspect beginning/middle/end frames for every output and full frame sets for the seven representative IDs**

Run: `powershell -ExecutionPolicy Bypass -File apps/localization/run.ps1 verify --frames beginning,middle,end --representative 7590780099696364810,7588858424293641481,7593419229190229254,7627053310117186854,7644194468706536756,7657867906679655707,7666656722269850926`

Expected: Russian captions fit, source narration captions are unreadable, and no renderer artifacts appear outside the bottom band.

- [ ] **Step 5: Record truthful batch evidence**

Set the delivery ledger to the highest level supported by actual local evidence; do not claim platform upload, human linguistic review of every line, or publication rights.

```powershell
git add docs/mvp/localization/capability-evidence.md docs/mvp/localization/delivery-ledger.md
git commit -m "docs: record Russian batch verification"
```

## Plan self-review

- Spec coverage: inventory, ASR, structured translation, Qwen clone, two-stem separation, bounded alignment, loudness, caption replacement, NVENC, recovery, pilot, 74-item verification, documentation, and evidence ledger each map to an explicit task.
- Placeholder scan: no unfinished markers or unspecified implementation steps remain.
- Type consistency: immutable `Segment` IDs/timestamps flow from Task 1 through Tasks 2–8; stage names and CLI commands are consistent across implementation, pilot, and batch tasks.
