import hashlib
import json
from pathlib import Path
import sys

import pytest


APP = Path(__file__).resolve().parents[2] / "apps" / "publication-batch"
sys.path.insert(0, str(APP))

from publication_batch.contracts import (
    BatchContractError,
    BatchPolicy,
    load_localization_manifest,
    load_metadata_template,
    render_metadata,
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_localization_manifest(tmp_path: Path, rows=None) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    source = tmp_path / "source-manifest.json"
    translation = tmp_path / "translation-manifest.json"
    voice = tmp_path / "voice-manifest.json"
    for path, content in ((source, b"source"), (translation, b"translation"), (voice, b"voice")):
        path.write_bytes(content)
    derivatives = []
    for ordinal, (language, media_id) in enumerate(rows or [("ru-RU", "m1"), ("en-US", "m1")], 1):
        video = tmp_path / f"localized-{ordinal}.mp4"
        video.write_bytes(f"video-{ordinal}".encode())
        derivatives.append(
            {
                "targetLanguage": language,
                "mediaId": media_id,
                "path": str(video),
                "sha256": digest(video),
                "size": video.stat().st_size,
                "duration": 4.5,
                "width": 1080,
                "height": 1920,
                "videoCodec": "h264",
                "audioCodec": "aac",
            }
        )
    value = {
        "schemaVersion": 1,
        "sourceManifest": str(source),
        "sourceManifestSha256": digest(source),
        "translationManifest": str(translation),
        "translationManifestSha256": digest(translation),
        "voiceManifest": str(voice),
        "voiceManifestSha256": digest(voice),
        "sourceVolume": 0.12,
        "targetLanguages": list(dict.fromkeys(row[0] for row in rows or [("ru-RU", "m1"), ("en-US", "m1")])),
        "expectedMediaIds": list(dict.fromkeys(row[1] for row in rows or [("ru-RU", "m1"), ("en-US", "m1")])),
        "derivatives": derivatives,
    }
    path = tmp_path / "localization-manifest.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def write_template(tmp_path: Path, title="{filename} · {language} · {media_id}", **values) -> Path:
    path = tmp_path / "metadata.json"
    path.write_text(json.dumps({"title": title, **values}, ensure_ascii=False), encoding="utf-8")
    return path


def test_loader_preserves_derivative_order_and_verifies_lineage(tmp_path):
    value = load_localization_manifest(write_localization_manifest(tmp_path))

    assert [(row.ordinal, row.target_language, row.media_id) for row in value.derivatives] == [
        (1, "ru-RU", "m1"),
        (2, "en-US", "m1"),
    ]
    assert len(value.manifest_sha256) == 64
    assert value.target_languages == ("ru-RU", "en-US")
    assert value.expected_media_ids == ("m1",)


def test_loader_rejects_duplicate_missing_or_changed_derivative(tmp_path):
    duplicate = write_localization_manifest(tmp_path, [("ru-RU", "m1"), ("ru-RU", "m1")])
    with pytest.raises(BatchContractError, match="coverage"):
        load_localization_manifest(duplicate)

    changed = write_localization_manifest(tmp_path / "changed")
    value = json.loads(changed.read_text(encoding="utf-8"))
    Path(value["derivatives"][0]["path"]).write_bytes(b"tampered")
    with pytest.raises(BatchContractError, match="fingerprint"):
        load_localization_manifest(changed)


def test_loader_requires_exact_language_media_cross_product(tmp_path):
    incomplete = write_localization_manifest(tmp_path, [("ru-RU", "m1"), ("en-US", "m2")])

    with pytest.raises(BatchContractError, match="coverage"):
        load_localization_manifest(incomplete)


def test_metadata_renderer_expands_supported_tokens_in_all_strings(tmp_path):
    source = load_localization_manifest(write_localization_manifest(tmp_path))
    template = load_metadata_template(
        write_template(
            tmp_path,
            description="Dubbed {filename} for {language}",
            tags=["{media_id}", "localized-{language}"],
        )
    )

    rendered = render_metadata(template, source.derivatives[0])

    assert rendered == {
        "title": "localized-1 · ru-RU · m1",
        "description": "Dubbed localized-1 for ru-RU",
        "tags": ["m1", "localized-ru-RU"],
    }


@pytest.mark.parametrize("title", ["{unknown}", "broken {language", "broken language}"])
def test_metadata_template_rejects_unknown_or_unbalanced_tokens(tmp_path, title):
    with pytest.raises(BatchContractError, match="metadata token"):
        load_metadata_template(write_template(tmp_path, title))


def test_metadata_template_rejects_unknown_fields_and_invalid_tags(tmp_path):
    for value in (
        {"title": "Title", "visibility": "public"},
        {"title": "Title", "tags": "not-a-list"},
        {"title": "", "tags": []},
    ):
        path = tmp_path / f"metadata-{len(list(tmp_path.iterdir()))}.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        with pytest.raises(BatchContractError):
            load_metadata_template(path)


def test_batch_policy_preserves_target_order_and_bounded_credential_references():
    policy = BatchPolicy.create(
        [("youtube", "primary"), ("tiktok", "brand")],
        {"youtube": "youtube-main"},
    )

    assert policy.targets == (("youtube", "primary"), ("tiktok", "brand"))
    assert policy.credentials == (("youtube", "youtube-main"),)
    assert policy.to_public_dict()["public"] is False

    invalid = [
        ([], {}),
        ([("unknown", "main")], {}),
        ([("youtube", "")], {}),
        ([("youtube", "main"), ("youtube", "other")], {}),
        ([("youtube", "main")], {"tiktok": "missing-target"}),
        ([("youtube", "main")], {"youtube": "../secret"}),
    ]
    for targets, credentials in invalid:
        with pytest.raises(BatchContractError):
            BatchPolicy.create(targets, credentials)


def test_public_contract_representations_contain_no_secret_or_vault_material(tmp_path):
    source = load_localization_manifest(write_localization_manifest(tmp_path))
    template = load_metadata_template(write_template(tmp_path))
    policy = BatchPolicy.create([("youtube", "primary")], {"youtube": "youtube-main"})

    rendered = repr(source) + repr(template) + repr(policy) + json.dumps(policy.to_public_dict())

    assert "credentialValue" not in rendered
    assert "credentialVault" not in rendered
    assert "secret" not in rendered.lower()
