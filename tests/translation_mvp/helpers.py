import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_transcript_manifest(tmp_path: Path, *, changed_digest: bool = False) -> Path:
    source_manifest = tmp_path / "source-manifest.json"
    source_manifest.write_text('{"schemaVersion":1}', encoding="utf-8")
    rows = []
    for index, (media_id, text, language) in enumerate(
        (("media-a", "你好世界", "zh"), ("media-b", "第二条", "zh")), 1
    ):
        source = tmp_path / f"{media_id}.mp4"
        source.write_bytes(f"media-{index}".encode())
        item = tmp_path / media_id
        item.mkdir()
        transcript = item / "transcript.json"
        transcript.write_text(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "source": {"mediaId": media_id, "path": str(source), "sha256": sha256(source)},
                    "detectedLanguage": language,
                    "segments": [
                        {"id": 1, "start": 0.0, "end": 1.25, "text": text},
                        {"id": 2, "start": 1.25, "end": 2.0, "text": f"{text}！"},
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        srt = item / "transcript.srt"
        srt.write_text(f"1\n00:00:00,000 --> 00:00:01,250\n{text}\n", encoding="utf-8")
        rows.append(
            {
                "mediaId": media_id,
                "sourcePath": str(source),
                "sourceSha256": sha256(source),
                "transcriptPath": str(transcript),
                "transcriptSha256": "0" * 64 if changed_digest and index == 1 else sha256(transcript),
                "srtPath": str(srt),
                "srtSha256": sha256(srt),
                "detectedLanguage": language,
                "segmentCount": 2,
            }
        )
    path = tmp_path / "transcript-manifest.json"
    path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "sourceManifest": str(source_manifest),
                "sourceManifestSha256": sha256(source_manifest),
                "expectedMediaIds": ["media-a", "media-b"],
                "transcripts": rows,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path
