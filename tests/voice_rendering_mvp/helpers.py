import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def translation_manifest(tmp_path: Path) -> Path:
    transcript = tmp_path / "transcript-manifest.json"
    transcript.write_text('{"schemaVersion":1}', encoding="utf-8")
    rows = []
    for language, words in (("ru-RU", ("Привет", "Мир")), ("en-US", ("Hello", "World"))):
        item = tmp_path / language
        item.mkdir()
        document = item / "translation.json"
        document.write_text(json.dumps({
            "schemaVersion": 1,
            "source": {"mediaId": "m1", "language": "zh"},
            "targetLanguage": language,
            "reviewStatus": "MACHINE",
            "segments": [
                {"id": 1, "start": 0.0, "end": 1.0, "sourceText": "一", "translatedText": words[0]},
                {"id": 2, "start": 1.0, "end": 2.0, "sourceText": "二", "translatedText": words[1]},
            ],
        }, ensure_ascii=False), encoding="utf-8")
        srt = item / "translation.srt"
        srt.write_text("subtitle", encoding="utf-8")
        rows.append({
            "mediaId": "m1", "targetLanguage": language,
            "translationPath": str(document), "translationSha256": digest(document),
            "srtPath": str(srt), "srtSha256": digest(srt),
            "reviewStatus": "MACHINE", "segmentCount": 2,
        })
    manifest = tmp_path / "translation-manifest.json"
    manifest.write_text(json.dumps({
        "schemaVersion": 1,
        "transcriptManifest": str(transcript), "transcriptManifestSha256": digest(transcript),
        "expectedMediaIds": ["m1"], "targetLanguages": ["ru-RU", "en-US"],
        "translations": rows,
    }, ensure_ascii=False), encoding="utf-8")
    return manifest
