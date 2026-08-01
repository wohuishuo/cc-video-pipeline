"""Fast online Chinese-to-Russian translation with local timing ownership."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import re
import time
from typing import Any, Callable
import urllib.parse
import urllib.request

from .contracts import JobRecord, StageRecord, atomic_write_json, sha256_file


ADAPTER = "google-translate-gtx@1"
_DIGITS = re.compile(r"\d+(?:[.,]\d+)?")


def translate_text(text: str, *, opener: Callable[..., Any] = urllib.request.urlopen) -> str:
    query = urllib.parse.urlencode(
        {"client": "gtx", "sl": "zh-CN", "tl": "ru", "dt": "t", "q": text}
    )
    request = urllib.request.Request(
        "https://translate.googleapis.com/translate_a/single?" + query,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    with opener(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    translated = "".join(row[0] for row in payload[0] if row and row[0]).strip()
    if not translated:
        raise RuntimeError("empty Russian translation")
    return translated


def _srt_time(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    whole, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02}:{minutes:02}:{whole:02},{milliseconds:03}"


def translate_job_fast(job: JobRecord, *, output_root: Path) -> dict[str, Any]:
    transcript_stage = job.stages.get("transcription")
    if not isinstance(transcript_stage, StageRecord) or transcript_stage.status != "completed":
        raise RuntimeError("completed transcript required")
    transcript_path = Path(transcript_stage.outputs["transcript"])
    source = json.loads(transcript_path.read_text(encoding="utf-8"))
    def translate_row(row: dict[str, Any]) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                russian = translate_text(row["text"])
                return {"id": row["id"], "start": row["start"], "end": row["end"], "text_ru": russian}
            except Exception as error:
                last_error = error
                if attempt < 2:
                    time.sleep(0.5 * (attempt + 1))
        raise RuntimeError(f"translation failed for segment {row['id']}: {last_error}")

    with ThreadPoolExecutor(max_workers=8) as pool:
        rows = list(pool.map(translate_row, source["segments"]))
    job_dir = output_root / "jobs" / job.id
    translation_path = job_dir / "translation.ru.json"
    srt_path = job_dir / "subtitles.ru.srt"
    atomic_write_json(translation_path, {"schema_version": 1, "segments": rows})
    srt_path.write_text(
        "".join(
            f"{row['id']}\n{_srt_time(row['start'])} --> {_srt_time(row['end'])}\n{row['text_ru']}\n\n"
            for row in rows
        ),
        encoding="utf-8",
    )
    job.stages["translation"] = StageRecord.completed(
        ADAPTER,
        {"source_sha256": job.source_sha256, "transcript_sha256": sha256_file(transcript_path)},
        {"translation": str(translation_path), "srt": str(srt_path)},
    )
    return {"schema_version": 1, "segments": rows}
