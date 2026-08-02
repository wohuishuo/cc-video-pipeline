import hashlib
import json
from pathlib import Path
import sys

import pytest


APP = Path(__file__).resolve().parents[2] / "apps" / "publication-batch-execution"
sys.path.insert(0, str(APP))

from publication_batch_execution.contracts import (
    BatchExecutionContractError,
    load_batch_plan,
    sha256_file,
)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def build_batch(tmp_path: Path, languages=("ru-RU", "en-US")) -> tuple[Path, str, Path]:
    localization = tmp_path / "localization-manifest.json"
    write_json(localization, {"schemaVersion": 1, "owner": "localization"})
    template = tmp_path / "metadata-template.json"
    write_json(template, {"title": "{language} release"})
    items = []
    for ordinal, language in enumerate(languages, 1):
        item_root = tmp_path / "items" / f"{ordinal:04d}"
        video = item_root / f"localized-{language}.mp4"
        video.parent.mkdir(parents=True, exist_ok=True)
        video.write_bytes(f"video-{language}".encode("utf-8"))
        metadata = item_root / "metadata.json"
        write_json(metadata, {"title": f"{language} release"})
        video_sha = sha256_file(video); metadata_sha = sha256_file(metadata)
        job_id = hashlib.sha256(
            f"{video_sha}\0{metadata_sha}\0youtube\0primary\0private-or-draft\0youtube-main".encode("utf-8")
        ).hexdigest()
        plan = item_root / "publication-plan.json"
        write_json(
            plan,
            {
                "schemaVersion": 1,
                "video": {"path": str(video.resolve()), "sha256": video_sha, "size": video.stat().st_size},
                "metadata": {"path": str(metadata.resolve()), "sha256": metadata_sha, "title": f"{language} release"},
                "public": False,
                "jobs": [
                    {
                        "ordinal": 1,
                        "id": job_id,
                        "platform": "youtube",
                        "account": "primary",
                        "visibility": "private-or-draft",
                        "credentialId": "youtube-main",
                    }
                ],
            },
        )
        items.append(
            {
                "ordinal": ordinal,
                "targetLanguage": language,
                "mediaId": "m1",
                "derivativePath": str(video.resolve()),
                "derivativeSha256": video_sha,
                "metadataPath": str(metadata.resolve()),
                "metadataSha256": metadata_sha,
                "publicationPlan": str(plan.resolve()),
                "publicationPlanSha256": sha256_file(plan),
                "jobCount": 1,
            }
        )
    aggregate = tmp_path / "publication-batch-plan.json"
    write_json(
        aggregate,
        {
            "schemaVersion": 1,
            "localizationManifest": str(localization.resolve()),
            "localizationManifestSha256": sha256_file(localization),
            "metadataTemplate": str(template.resolve()),
            "metadataTemplateSha256": sha256_file(template),
            "targetLanguages": list(languages),
            "expectedMediaIds": ["m1"],
            "targets": [{"platform": "youtube", "account": "primary", "credentialId": "youtube-main"}],
            "public": False,
            "maximumActiveItems": 1,
            "expectedDerivativeKeys": [f"{language}:m1" for language in languages],
            "items": items,
            "totalJobCount": len(items),
        },
    )
    vault = tmp_path / "credential-vault.json"; write_json(vault, {"schemaVersion": 1})
    return aggregate, sha256_file(aggregate), vault


def rewrite(path: Path, change) -> None:
    value = json.loads(path.read_text(encoding="utf-8"))
    change(value)
    write_json(path, value)


def test_loads_exact_private_youtube_batch_in_derivative_order(tmp_path):
    path, confirmation, vault = build_batch(tmp_path)

    batch = load_batch_plan(path, confirmation, vault)

    assert batch.plan_path == path.resolve()
    assert batch.plan_sha256 == confirmation
    assert batch.vault_path == vault.resolve()
    assert batch.maximum_active_items == 1
    assert [item.identity for item in batch.items] == ["ru-RU:m1", "en-US:m1"]
    assert [item.credential_id for item in batch.items] == ["youtube-main", "youtube-main"]
    assert batch.total_job_count == 2


def test_rejects_wrong_exact_confirmation_before_loading_children(tmp_path):
    path, _confirmation, vault = build_batch(tmp_path)

    with pytest.raises(BatchExecutionContractError) as caught:
        load_batch_plan(path, "0" * 64, vault)

    assert caught.value.code == "REJECTED_CONFIRMATION"


def test_rejects_mutated_derivative_as_stale(tmp_path):
    path, confirmation, vault = build_batch(tmp_path)
    value = json.loads(path.read_text(encoding="utf-8"))
    Path(value["items"][0]["derivativePath"]).write_bytes(b"changed")

    with pytest.raises(BatchExecutionContractError) as caught:
        load_batch_plan(path, confirmation, vault)

    assert caught.value.code == "REJECTED_STALE"


@pytest.mark.parametrize(
    "change",
    [
        lambda value: value.update(targets=[{"platform":"tiktok","account":"primary","credentialId":"youtube-main"}]),
        lambda value: value["targets"][0].pop("credentialId"),
        lambda value: value.update(public=True),
    ],
)
def test_rejects_unsupported_or_uncredentialed_batch_policy_before_execution(tmp_path, change):
    path, _confirmation, vault = build_batch(tmp_path)
    rewrite(path, change); confirmation = sha256_file(path)

    with pytest.raises(BatchExecutionContractError) as caught:
        load_batch_plan(path, confirmation, vault)

    assert caught.value.code == "REJECTED_POLICY"


def test_rejects_reordered_or_incomplete_derivative_coverage(tmp_path):
    path, _confirmation, vault = build_batch(tmp_path)
    rewrite(path, lambda value: value["items"].reverse()); confirmation = sha256_file(path)

    with pytest.raises(BatchExecutionContractError) as caught:
        load_batch_plan(path, confirmation, vault)

    assert caught.value.code == "REJECTED_MALFORMED"


def test_rejects_missing_vault_without_reading_credential_material(tmp_path):
    path, confirmation, vault = build_batch(tmp_path); vault.unlink()

    with pytest.raises(BatchExecutionContractError) as caught:
        load_batch_plan(path, confirmation, vault)

    assert caught.value.code == "REJECTED_MALFORMED"


@pytest.mark.parametrize(
    "change",
    [
        lambda value: value.update(targetLanguages=[{"locale": "ru-RU"}]),
        lambda value: value.update(items=["not-an-item", *value["items"][1:]]),
    ],
)
def test_rejects_unhashable_or_non_object_rows_with_stable_contract_error(tmp_path, change):
    path, _confirmation, vault = build_batch(tmp_path)
    rewrite(path, change); confirmation = sha256_file(path)

    with pytest.raises(BatchExecutionContractError) as caught:
        load_batch_plan(path, confirmation, vault)

    assert caught.value.code == "REJECTED_MALFORMED"
