import json
from pathlib import Path
import sys

import pytest


APP = Path(__file__).resolve().parents[2] / "apps" / "translation"
sys.path.insert(0, str(APP))

from .helpers import sha256, write_transcript_manifest  # noqa: E402
from translation_app.contracts import (  # noqa: E402
    TranslationArtifact,
    TranslationDocument,
    TranslationError,
    TranslationManifest,
    TranslationSegment,
    load_transcript_manifest,
    normalize_target_languages,
)


def test_transcript_manifest_loader_preserves_order_and_verified_segments(tmp_path):
    manifest = write_transcript_manifest(tmp_path)

    loaded = load_transcript_manifest(manifest)

    assert loaded.path == manifest.resolve()
    assert [row.media_id for row in loaded.transcripts] == ["media-a", "media-b"]
    assert loaded.transcripts[0].segments[0].text == "你好世界"
    assert loaded.transcripts[0].detected_language == "zh"


def test_transcript_manifest_loader_rejects_changed_artifact(tmp_path):
    with pytest.raises(TranslationError, match="fingerprint"):
        load_transcript_manifest(write_transcript_manifest(tmp_path, changed_digest=True))


def test_target_languages_are_normalized_but_duplicates_are_rejected():
    assert normalize_target_languages(["ru", "en-US", "kk-kz", "es-ES", "fr"]) == (
        "ru-RU", "en-US", "kk-KZ", "es-ES", "fr-FR"
    )
    with pytest.raises(TranslationError, match="duplicate"):
        normalize_target_languages(["ru", "ru-RU"])
    with pytest.raises(TranslationError, match="unsupported"):
        normalize_target_languages(["xx-XX"])


def test_translation_document_preserves_source_segment_identity_and_review_state(tmp_path):
    transcript_manifest = load_transcript_manifest(write_transcript_manifest(tmp_path))
    transcript = transcript_manifest.transcripts[0]
    segments = tuple(
        TranslationSegment(row.id, row.start, row.end, row.text, f"RU:{row.text}")
        for row in transcript.segments
    )

    document = TranslationDocument(
        transcript.media_id,
        transcript.transcript_path,
        transcript.transcript_sha256,
        transcript.detected_language,
        "ru-RU",
        "MACHINE",
        segments,
    )

    value = document.to_dict()
    assert value["reviewStatus"] == "MACHINE"
    assert value["segments"][0] == {
        "id": 1,
        "start": 0.0,
        "end": 1.25,
        "sourceText": "你好世界",
        "translatedText": "RU:你好世界",
    }
    with pytest.raises(TranslationError, match="review status"):
        TranslationDocument(
            transcript.media_id,
            transcript.transcript_path,
            transcript.transcript_sha256,
            "zh",
            "ru-RU",
            "APPROVED",
            segments,
        )


def test_translation_manifest_requires_language_major_exact_coverage(tmp_path):
    transcript_manifest_path = write_transcript_manifest(tmp_path)
    output = tmp_path / "translation.json"
    subtitle = tmp_path / "translation.srt"
    output.write_text("{}", encoding="utf-8")
    subtitle.write_text("subtitle", encoding="utf-8")
    artifact = TranslationArtifact(
        "media-a", "ru-RU", str(output), sha256(output), str(subtitle), sha256(subtitle), "MACHINE", 2
    )

    with pytest.raises(TranslationError, match="exact translation coverage"):
        TranslationManifest(
            str(transcript_manifest_path),
            sha256(transcript_manifest_path),
            ("media-a", "media-b"),
            ("ru-RU", "en-US"),
            (artifact,),
        )
