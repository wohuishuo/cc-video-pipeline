import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
        video_sha = digest(video); metadata_sha = digest(metadata)
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
                        "ordinal": 1, "id": job_id, "platform": "youtube",
                        "account": "primary", "visibility": "private-or-draft",
                        "credentialId": "youtube-main",
                    }
                ],
            },
        )
        items.append(
            {
                "ordinal": ordinal, "targetLanguage": language, "mediaId": "m1",
                "derivativePath": str(video.resolve()), "derivativeSha256": video_sha,
                "metadataPath": str(metadata.resolve()), "metadataSha256": metadata_sha,
                "publicationPlan": str(plan.resolve()), "publicationPlanSha256": digest(plan),
                "jobCount": 1,
            }
        )
    aggregate = tmp_path / "publication-batch-plan.json"
    write_json(
        aggregate,
        {
            "schemaVersion": 1,
            "localizationManifest": str(localization.resolve()),
            "localizationManifestSha256": digest(localization),
            "metadataTemplate": str(template.resolve()),
            "metadataTemplateSha256": digest(template),
            "targetLanguages": list(languages), "expectedMediaIds": ["m1"],
            "targets": [{"platform": "youtube", "account": "primary", "credentialId": "youtube-main"}],
            "public": False, "maximumActiveItems": 1,
            "expectedDerivativeKeys": [f"{language}:m1" for language in languages],
            "items": items, "totalJobCount": len(items),
        },
    )
    vault = tmp_path / "credential-vault.json"; write_json(vault, {"schemaVersion": 1})
    return aggregate, digest(aggregate), vault
