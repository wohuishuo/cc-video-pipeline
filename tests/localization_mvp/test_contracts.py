from pathlib import Path
import sys

import pytest

APP=Path(__file__).resolve().parents[2]/"apps"/"localization"
sys.path.insert(0,str(APP))

from .helpers import manifests  # noqa: E402
from localization_app.contracts import LocalizationError, load_composition_inputs  # noqa: E402


def test_loader_produces_language_major_jobs_with_exact_segments_and_clips(tmp_path):
    source,translation,voice=manifests(tmp_path)
    loaded=load_composition_inputs(source,translation,voice)
    assert [(job.target_language,job.media_id) for job in loaded.jobs]==[("ru-RU","m1"),("en-US","m1")]
    assert [segment.id for segment in loaded.jobs[0].segments]==[1,2]
    assert [clip.segment_id for clip in loaded.jobs[0].clips]==[1,2]
    assert loaded.jobs[0].clips[1].duration==2.5
    assert loaded.jobs[0].source_path.name=="source.mp4"


def test_loader_rejects_changed_subtitle_fingerprint(tmp_path):
    source,translation,voice=manifests(tmp_path)
    (tmp_path/"ru-RU"/"translation.srt").write_text("changed",encoding="utf-8")
    with pytest.raises(LocalizationError,match="fingerprint"):
        load_composition_inputs(source,translation,voice)


def test_loader_rejects_missing_voice_segment_and_wrong_lineage(tmp_path):
    source,translation,voice=manifests(tmp_path,omit_voice_segment=True)
    with pytest.raises(LocalizationError,match="voice coverage"):
        load_composition_inputs(source,translation,voice)

    source,translation,voice=manifests(tmp_path/"other")
    import json
    value=json.loads(voice.read_text(encoding="utf-8")); value["translationManifestSha256"]="0"*64
    voice.write_text(json.dumps(value),encoding="utf-8")
    with pytest.raises(LocalizationError,match="lineage"):
        load_composition_inputs(source,translation,voice)
