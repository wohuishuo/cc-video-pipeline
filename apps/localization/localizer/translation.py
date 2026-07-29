"""Deterministic, timestamp-safe Chinese-to-Russian translation via Ollama."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import re
from tempfile import NamedTemporaryFile
from typing import Any, Callable, Iterable, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .contracts import JobRecord, Segment, StageRecord, atomic_write_json, sha256_file


ADAPTER = "ollama@qwen3.5:9b"
MODEL = "qwen3.5:9b"
DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
MAX_CHUNK_ATTEMPTS = 3
TRANSLATION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["translations"],
    "properties": {
        "translations": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "text_ru"],
                "properties": {"id": {"type": "integer"}, "text_ru": {"type": "string"}},
            },
        }
    },
}
SYSTEM_PROMPT = (
    "Translate each Chinese text_zh value into natural Russian. Return exactly one "
    "translation for every supplied id. Preserve all numerals exactly. Do not emit "
    "Chinese characters, timestamps, start/end fields, commentary, or markdown."
)
REWRITE_PROMPT = (
    "Shorten only the supplied Russian text for the listed ids while retaining its "
    "meaning and every numeral. Return exactly one Russian translation per id. Do not "
    "emit Chinese characters, timestamps, commentary, or markdown."
)
_CHINESE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
_CYRILLIC = re.compile(r"[\u0400-\u052f]")
_NUMERALS = re.compile(r"\d+(?:[.,]\d+)?")

HttpPost = Callable[[str, dict[str, Any]], dict[str, Any]]


class TranslationError(ValueError):
    """Translation input or model output violates the immutable segment contract."""


@dataclass(frozen=True)
class TranslationSegment:
    """Russian text joined to the source-owned identity and timing."""

    id: int
    start: float
    end: float
    text: str

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "start": self.start, "end": self.end, "text_ru": self.text}


def _row_value(row: Segment | TranslationSegment | Mapping[str, Any], name: str) -> Any:
    if isinstance(row, Mapping):
        return row.get(name)
    return getattr(row, name, None)


def _source_rows(segments: Sequence[Segment | Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, segment in enumerate(segments, 1):
        identifier = _row_value(segment, "id")
        text = _row_value(segment, "text")
        if isinstance(segment, Mapping) and text is None:
            text = _row_value(segment, "text_zh")
        if isinstance(identifier, bool) or not isinstance(identifier, int) or identifier <= 0:
            raise TranslationError(f"source segment {index} requires a positive integer id")
        if not isinstance(text, str) or not text.strip():
            raise TranslationError(f"source segment {identifier} requires non-empty Chinese text")
        rows.append({"id": identifier, "text_zh": text})
    ids = [row["id"] for row in rows]
    duplicates = sorted({identifier for identifier in ids if ids.count(identifier) > 1})
    if duplicates:
        raise TranslationError("duplicate source ids: " + ", ".join(map(str, duplicates)))
    if not rows:
        raise TranslationError("empty transcript")
    return rows


def build_translation_request(
    segments: Sequence[Segment | Mapping[str, Any]], *, model: str = MODEL, system_prompt: str = SYSTEM_PROMPT
) -> dict[str, Any]:
    """Build the constrained Ollama chat payload without source timing data."""

    if not isinstance(model, str) or not model:
        raise TranslationError("model must be a non-empty string")
    return {
        "model": model,
        "stream": False,
        "think": False,
        "format": TRANSLATION_SCHEMA,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(_source_rows(segments), ensure_ascii=False)},
        ],
        "options": {"temperature": 0, "num_ctx": 4096},
    }


def _ids_message(label: str, identifiers: Iterable[int]) -> str:
    return f"{label}: " + ", ".join(map(str, sorted(identifiers)))


def validate_translations(
    source_segments: Sequence[Segment | Mapping[str, Any]], translations: Any
) -> list[dict[str, Any]]:
    """Validate one complete, ordered Russian response against authoritative source text."""

    source_rows = _source_rows(source_segments)
    if not isinstance(translations, list):
        raise TranslationError("translations must be an array")
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(translations, 1):
        if not isinstance(item, Mapping) or set(item) != {"id", "text_ru"}:
            raise TranslationError(f"translation {index} must contain only id and text_ru")
        identifier = item["id"]
        text = item["text_ru"]
        if isinstance(identifier, bool) or not isinstance(identifier, int):
            raise TranslationError(f"translation {index} requires an integer id")
        if not isinstance(text, str) or not text.strip():
            raise TranslationError(f"translation {identifier} requires non-empty Russian text")
        if _CHINESE.search(text):
            raise TranslationError(f"translation {identifier} contains Chinese characters")
        if not _CYRILLIC.search(text):
            raise TranslationError(f"translation {identifier} requires Cyrillic content")
        normalized.append({"id": identifier, "text_ru": text})

    expected_ids = [row["id"] for row in source_rows]
    received_ids = [item["id"] for item in normalized]
    duplicates = {identifier for identifier in received_ids if received_ids.count(identifier) > 1}
    if duplicates:
        raise TranslationError(_ids_message("duplicate ids", duplicates))
    missing = set(expected_ids) - set(received_ids)
    if missing:
        raise TranslationError(_ids_message("missing ids", missing))
    unexpected = set(received_ids) - set(expected_ids)
    if unexpected:
        raise TranslationError(_ids_message("unexpected ids", unexpected))
    if received_ids != expected_ids:
        raise TranslationError("translation ids must be in source order")

    for source, translated in zip(source_rows, normalized, strict=True):
        expected_numerals = Counter(_NUMERALS.findall(source["text_zh"]))
        received_numerals = Counter(_NUMERALS.findall(translated["text_ru"]))
        if expected_numerals != received_numerals:
            raise TranslationError(f"translation {source['id']} does not preserve numerals")
    return normalized


def merge_translations(
    source_segments: Sequence[Segment], translations: Any
) -> list[TranslationSegment]:
    """Attach validated Russian text to immutable source identity and timing only."""

    normalized = validate_translations(source_segments, translations)
    return [
        TranslationSegment(
            id=source.id,
            start=source.start,
            end=source.end,
            text=translated["text_ru"],
        )
        for source, translated in zip(source_segments, normalized, strict=True)
    ]


def _default_http_post(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=30) as response:  # noqa: S310 - URL is a configured local boundary.
            parsed = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        raise TranslationError(f"Ollama request failed: {error}") from error
    if not isinstance(parsed, dict):
        raise TranslationError("Ollama response must be an object")
    return parsed


def _extract_translations(response: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        content = response["message"]["content"]
    except (KeyError, TypeError) as error:
        raise TranslationError("Ollama response is missing message content") from error
    if not isinstance(content, str):
        raise TranslationError("Ollama message content must be JSON text")
    try:
        decoded = json.loads(content)
    except json.JSONDecodeError as error:
        raise TranslationError("Ollama message content is not valid JSON") from error
    if not isinstance(decoded, dict) or set(decoded) != {"translations"}:
        raise TranslationError("Ollama translation schema mismatch")
    return decoded["translations"]


def _translate_chunks(
    source_segments: Sequence[Segment | Mapping[str, Any]],
    *,
    ollama_base_url: str,
    model: str,
    chunk_size: int,
    http_post: HttpPost,
    system_prompt: str,
) -> list[dict[str, Any]]:
    if not isinstance(chunk_size, int) or isinstance(chunk_size, bool) or chunk_size <= 0:
        raise TranslationError("chunk_size must be a positive integer")
    translations: list[dict[str, Any]] = []
    endpoint = ollama_base_url.rstrip("/") + "/api/chat"
    for start in range(0, len(source_segments), chunk_size):
        chunk = source_segments[start : start + chunk_size]
        last_error: Exception | None = None
        for _attempt in range(MAX_CHUNK_ATTEMPTS):
            try:
                response = http_post(endpoint, build_translation_request(chunk, model=model, system_prompt=system_prompt))
                translations.extend(validate_translations(chunk, _extract_translations(response)))
                break
            except Exception as error:
                last_error = error
        else:
            raise TranslationError(f"translation chunk starting at {start + 1} failed after {MAX_CHUNK_ATTEMPTS} attempts: {last_error}") from last_error
    return translations


def _job_artifact_dir(job: JobRecord, output_root: str | Path | None) -> Path:
    if output_root is None:
        return Path(job.source).parent / "russian" / "jobs" / job.id
    return Path(output_root) / "jobs" / job.id


def _read_source_segments(job: JobRecord) -> tuple[Path, list[Segment]]:
    stage = job.stages.get("transcription")
    if not isinstance(stage, StageRecord) or stage.status != "completed":
        raise TranslationError("completed transcription receipt is required")
    transcript_name = stage.outputs.get("transcript")
    if not transcript_name:
        raise TranslationError("transcription receipt is missing transcript output")
    transcript_path = Path(transcript_name)
    try:
        raw = json.loads(transcript_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise TranslationError(f"cannot read transcript: {error}") from error
    if not isinstance(raw, dict) or set(raw) != {"schema_version", "segments"}:
        raise TranslationError("transcript schema mismatch")
    if raw["schema_version"] != 1:
        raise TranslationError(f"unsupported transcript schema version: {raw['schema_version']}")
    if not isinstance(raw["segments"], list):
        raise TranslationError("transcript segments must be an array")
    expected_keys = {"id", "start", "end", "text", "words"}
    segments: list[Segment] = []
    previous_end = -math.inf
    for index, value in enumerate(raw["segments"], 1):
        if not isinstance(value, dict) or set(value) != expected_keys:
            raise TranslationError(f"transcript segment {index} schema mismatch")
        try:
            segment = Segment.from_dict(value)
        except (KeyError, TypeError, ValueError) as error:
            raise TranslationError(f"invalid transcript segment {index}") from error
        if segment.id <= 0 or not math.isfinite(segment.start) or not math.isfinite(segment.end) or segment.end <= segment.start:
            raise TranslationError(f"invalid transcript timing for segment {index}")
        if segment.start < previous_end:
            raise TranslationError("transcript segments must be ordered without overlap")
        segments.append(segment)
        previous_end = segment.end
    _source_rows(segments)
    return transcript_path, segments


def _srt_timestamp(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    whole_seconds, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02}:{minutes:02}:{whole_seconds:02},{milliseconds:03}"


def _srt(segments: Sequence[TranslationSegment]) -> str:
    return "".join(
        f"{segment.id}\n{_srt_timestamp(segment.start)} --> {_srt_timestamp(segment.end)}\n{segment.text}\n\n"
        for segment in segments
    )


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _mark_failed(job: JobRecord, inputs: dict[str, str], error: Exception) -> None:
    job.stages["translation"] = StageRecord.failed(
        adapter=ADAPTER,
        inputs=inputs,
        outputs={},
        error={"type": type(error).__name__, "message": str(error)},
    )


def translate_job(
    job: JobRecord,
    *,
    output_root: str | Path | None = None,
    ollama_base_url: str = DEFAULT_OLLAMA_BASE_URL,
    model: str = MODEL,
    chunk_size: int = 20,
    http_post: HttpPost | None = None,
) -> dict[str, Any]:
    """Translate a completed Chinese transcript, retaining only locally owned timing."""

    artifact_dir = _job_artifact_dir(job, output_root)
    translation_path = artifact_dir / "translation.ru.json"
    srt_path = artifact_dir / "subtitles.ru.srt"
    inputs: dict[str, str] = {"source_sha256": job.source_sha256, "model": model}
    try:
        transcript_path, source_segments = _read_source_segments(job)
        inputs["transcript_sha256"] = sha256_file(transcript_path)
        raw_translations = _translate_chunks(
            source_segments,
            ollama_base_url=ollama_base_url,
            model=model,
            chunk_size=chunk_size,
            http_post=http_post or _default_http_post,
            system_prompt=SYSTEM_PROMPT,
        )
        merged = merge_translations(source_segments, raw_translations)
        result = {"schema_version": 1, "segments": [segment.to_dict() for segment in merged]}
        atomic_write_json(translation_path, result)
        _atomic_write_text(srt_path, _srt(merged))
        job.stages["translation"] = StageRecord.completed(
            adapter=ADAPTER,
            inputs=inputs,
            outputs={"translation": str(translation_path), "srt": str(srt_path)},
        )
        return result
    except Exception as error:
        for output in (translation_path, srt_path):
            if output.exists():
                output.unlink()
        _mark_failed(job, inputs, error)
        raise


def rewrite_overflow_segments(
    source_segments: Sequence[Segment],
    overflow_ids: Iterable[int],
    current_translations: Sequence[TranslationSegment],
    *,
    ollama_base_url: str = DEFAULT_OLLAMA_BASE_URL,
    model: str = MODEL,
    http_post: HttpPost | None = None,
) -> list[TranslationSegment]:
    """Request shorter Russian text for selected IDs without touching their timing."""

    requested = set(overflow_ids)
    if not requested:
        return list(current_translations)
    by_id = {segment.id: segment for segment in current_translations}
    source_by_id = {segment.id: segment for segment in source_segments}
    if requested - set(source_by_id) or requested - set(by_id):
        raise TranslationError("overflow ids must exist in source and current translations")
    rewrite_sources = [source_by_id[identifier] for identifier in sorted(requested)]
    rewritten_rows = _translate_chunks(
        rewrite_sources,
        ollama_base_url=ollama_base_url,
        model=model,
        chunk_size=len(rewrite_sources),
        http_post=http_post or _default_http_post,
        system_prompt=REWRITE_PROMPT,
    )
    rewritten = merge_translations([source_by_id[item["id"]] for item in rewritten_rows], rewritten_rows)
    replacement = {segment.id: segment for segment in rewritten}
    return [replacement.get(segment.id, segment) for segment in current_translations]
