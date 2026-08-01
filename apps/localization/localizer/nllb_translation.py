"""Batch Chinese-to-Russian translation with Meta NLLB, independent of Qwen."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .contracts import BatchManifest, StageRecord, atomic_write_json, sha256_file


MODEL_ID = "facebook/nllb-200-distilled-600M"
ADAPTER = "nllb-200-distilled-600M@zho_Hans-rus_Cyrl"


def translate_batch(batch_path: Path, *, model_id: str = MODEL_ID, batch_size: int = 8) -> None:
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    batch = BatchManifest.from_dict(json.loads(batch_path.read_text(encoding="utf-8")))
    tokenizer = AutoTokenizer.from_pretrained(model_id, src_lang="zho_Hans")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = AutoModelForSeq2SeqLM.from_pretrained(model_id).to(device)
    model.eval()
    forced_id = tokenizer.convert_tokens_to_ids("rus_Cyrl")

    for index, job in enumerate(batch.jobs, 1):
        transcript = Path(job.stages["transcription"].outputs["transcript"])
        job_dir = transcript.parent
        source_rows = json.loads(transcript.read_text(encoding="utf-8"))["segments"]
        texts = [str(row["text"]).strip() for row in source_rows]
        translated: list[str] = []
        for offset in range(0, len(texts), batch_size):
            encoded = tokenizer(
                texts[offset : offset + batch_size],
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=256,
            ).to(device)
            with torch.inference_mode():
                output = model.generate(
                    **encoded,
                    forced_bos_token_id=forced_id,
                    max_new_tokens=128,
                    num_beams=4,
                )
            translated.extend(tokenizer.batch_decode(output, skip_special_tokens=True))

        rows = [
            {"id": row["id"], "start": row["start"], "end": row["end"], "text_ru": text}
            for row, text in zip(source_rows, translated, strict=True)
        ]
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
            {"source_sha256": job.source_sha256, "transcript_sha256": sha256_file(transcript)},
            {"translation": str(translation_path), "srt": str(srt_path)},
        )
        atomic_write_json(batch_path, batch.to_dict())
        print(f"[翻译 {index}/{len(batch.jobs)}] {job.id}", flush=True)


def _srt_time(seconds: float) -> str:
    millis = round(float(seconds) * 1000)
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    seconds, millis = divmod(millis, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-manifest", required=True, type=Path)
    parser.add_argument("--batch-size", type=int, default=8)
    args = parser.parse_args()
    translate_batch(args.batch_manifest, batch_size=args.batch_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
