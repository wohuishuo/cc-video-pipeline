# Task 3 — Structured Chinese-to-Russian translation adapter

## Scope

Implemented `localizer.translation` as the sole owner of the `translation`
stage. It reads Task 2's schema-v1 `transcript.zh.json`, sends only segment ID
and Chinese text to Ollama, then locally attaches returned Russian text to the
source-owned IDs and timings. It writes `translation.ru.json` and
`subtitles.ru.srt` atomically and leaves all non-translation stages untouched.

## RED evidence

Command:

```powershell
& 'C:\Users\eugen\OneDrive\Documents\video\tools\.venv\Scripts\python.exe' -m pytest tests/localization/test_translation.py -q --import-mode=importlib
```

Observed result before implementation: exit code 1 during collection with
`ModuleNotFoundError: No module named 'localizer.translation'` from
`tests/localization/test_translation.py`.

## GREEN evidence

Focused command:

```powershell
& 'C:\Users\eugen\OneDrive\Documents\video\tools\.venv\Scripts\python.exe' -m pytest tests/localization/test_translation.py -q --import-mode=importlib
```

Observed result: `9 passed in 0.70s`.

Regression command:

```powershell
& 'C:\Users\eugen\OneDrive\Documents\video\tools\.venv\Scripts\python.exe' -m pytest tests/localization -q --import-mode=importlib
```

Observed result: `51 passed in 0.90s`.

## Contract evidence

- The request fixes `model` to `qwen3.5:9b` by default, with `think: false`,
  `temperature: 0`, `num_ctx: 4096`, and an Ollama JSON Schema requiring only
  `id` and `text_ru`.
- The in-process loopback HTTP server verifies `/api/chat`, records the actual
  JSON payload, forces a 503 for one chunk, and proves that only that chunk is
  retried.
- Validation rejects duplicate/missing/unexpected or reordered IDs, Chinese
  residue, no Cyrillic content, and changed numerals.
- Russian artifacts use the authoritative source IDs and exact source
  millisecond SRT ranges; the model never receives timestamps.
- An invalid transcript schema produces a failed `translation` receipt and
  removes partial Russian artifacts; the retry test supplies a transient HTTP
  503 without requiring Ollama.
- A second RED/GREEN cycle proved that rewriting an overflow segment preserves
  each source numeral once rather than duplicating it from prior Russian text.

## Files

- `apps/localization/localizer/translation.py`
- `tests/localization/test_translation.py`
- `.superpowers/sdd/2026-07-30-douyin-russian-localization/task-3-report.md`

## Self-review

Reviewed stage ownership, response-schema handling, chunk-local retry bounds,
atomic artifact writes, cleanup on failure, and the complete localization test
suite. `git diff --check` was clean.

## Capability evidence and non-goals

The fake HTTP server proves the HTTP/schema/retry/timestamp boundary without
requiring Ollama. It does not prove real Qwen linguistic quality, human
editorial acceptance, or alternate target-language support. No transcription,
voice, timing-alignment, media, upload, or source-file behavior was added.

## Fix round 1

### Root cause and RED evidence

`validate_translations()` required the model's IDs to arrive in source order
and then paired source and output positionally. An exact but reversed response
therefore raised `TranslationError: translation ids must be in source order`.
Separately, `rewrite_overflow_segments()` validated that prior Russian text
existed but passed Chinese source segments into the shared request builder.
The captured payload was `[{"id": 1, "text_zh": "2026年增长10%"}]`, so the
rewrite prompt had no Russian input or duration constraint.

RED command:

```powershell
& 'C:\Users\eugen\OneDrive\Documents\video\tools\.venv\Scripts\python.exe' -m pytest tests/localization/test_translation.py::test_merge_translation_reconstructs_source_order_from_unordered_exact_ids tests/localization/test_translation.py::test_rewrite_overflow_segments_sends_current_russian_text_and_duration_constraint -q --import-mode=importlib
```

Observed result: `2 failed in 0.16s`, with the two failures above.

### GREEN evidence

The validator now indexes exact, duplicate-free IDs and returns translations in
authoritative source order. `merge_translations()` therefore always combines
by local source ID/timestamps. The rewrite path now sends the prior Russian
text and `max_duration_seconds` while omitting `start` and `end`; validation
still verifies Cyrillic and numeral preservation before local timing is joined.

Focused command:

```powershell
& 'C:\Users\eugen\OneDrive\Documents\video\tools\.venv\Scripts\python.exe' -m pytest tests/localization/test_translation.py -q --import-mode=importlib
```

Observed result: `10 passed in 0.69s`.

Regression command:

```powershell
& 'C:\Users\eugen\OneDrive\Documents\video\tools\.venv\Scripts\python.exe' -m pytest tests/localization -q --import-mode=importlib
```

Observed result: `52 passed in 0.82s`.

### Changed files and self-review

- `apps/localization/localizer/translation.py`
- `tests/localization/test_translation.py`
- `.superpowers/sdd/2026-07-30-douyin-russian-localization/task-3-report.md`

Reviewed all ID-set checks (missing, extra, duplicate), source-order
reconstruction, numeral validation after mapping, and rewrite payload contents.
`git diff --check` was clean after the GREEN run.
