import hashlib
import json
from pathlib import Path
import sys

import pytest


APP = Path(__file__).resolve().parents[2] / "apps" / "publication-batch"
sys.path.insert(0, str(APP))

from publication_batch.child_planner import PlanChildError, ProcessResult, PublicPublicationPlanner
from publication_batch.contracts import BatchPolicy, Derivative


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def derivative(tmp_path: Path) -> Derivative:
    video = tmp_path / "localized.mp4"
    video.write_bytes(b"localized-video")
    return Derivative(1, "ru-RU", "m1", video.resolve(), digest(video), video.stat().st_size, 2.0, 1080, 1920, "h264", "aac")


def policy() -> BatchPolicy:
    return BatchPolicy.create(
        [("youtube", "primary"), ("tiktok", "brand")],
        {"youtube": "youtube-main"},
    )


def write_child_files(argv):
    video = Path(argv[argv.index("plan") + 1]).resolve()
    metadata = Path(argv[argv.index("--metadata") + 1]).resolve()
    output = Path(argv[argv.index("--output-dir") + 1]).resolve()
    operation_id = argv[argv.index("--operation-id") + 1]
    targets = [argv[index + 1].split("=", 1) for index, value in enumerate(argv) if value == "--target"]
    credentials = dict(argv[index + 1].split("=", 1) for index, value in enumerate(argv) if value == "--credential")
    output.mkdir(parents=True, exist_ok=True)
    jobs = []
    for ordinal, (platform, account) in enumerate(targets, 1):
        row = {
            "ordinal": ordinal,
            "id": hashlib.sha256(f"{platform}:{video}".encode()).hexdigest(),
            "platform": platform,
            "account": account,
            "visibility": "private-or-draft",
        }
        if platform in credentials:
            row["credentialId"] = credentials[platform]
        jobs.append(row)
    plan = output / "publication-plan.json"
    plan.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "video": {"path": str(video), "sha256": digest(video), "size": video.stat().st_size},
                "metadata": {
                    "path": str(metadata),
                    "sha256": digest(metadata),
                    "title": json.loads(metadata.read_text(encoding="utf-8"))["title"],
                },
                "public": False,
                "jobs": jobs,
            }
        ),
        encoding="utf-8",
    )
    receipt = output / "planning-receipt.json"
    receipt.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "operationId": operation_id,
                "inputFingerprint": "0" * 64,
                "resultClass": "COMPLETED",
                "plan": str(plan),
                "planSha256": digest(plan),
                "jobCount": len(jobs),
            }
        ),
        encoding="utf-8",
    )
    return plan, receipt


def test_public_planner_builds_argv_and_verifies_child_fact(tmp_path):
    calls = []

    def runner(argv, on_log):
        calls.append(list(argv))
        plan, _receipt = write_child_files(argv)
        on_log("planned")
        return ProcessResult(0, json.dumps({"resultClass": "COMPLETED", "manifest": str(plan)}), "")

    metadata = tmp_path / "metadata.json"
    metadata.write_text('{"title":"Localized"}', encoding="utf-8")
    fact = PublicPublicationPlanner(tmp_path / "publication" / "run.ps1", runner=runner).plan(
        derivative(tmp_path), metadata, tmp_path / "out", "child-1", policy(), lambda _line: None
    )

    assert fact.plan_sha256 == digest(fact.plan_path)
    assert fact.job_count == 2
    argv = calls[0]
    assert argv[:6] == [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str((tmp_path / "publication" / "run.ps1").resolve()),
    ]
    assert argv.count("--target") == 2
    assert argv[argv.index("--credential") + 1] == "youtube=youtube-main"
    assert "--public" not in argv


def test_public_planner_rejects_success_without_verified_receipt(tmp_path):
    metadata = tmp_path / "metadata.json"
    metadata.write_text('{"title":"Localized"}', encoding="utf-8")

    with pytest.raises(PlanChildError, match="receipt"):
        PublicPublicationPlanner(
            tmp_path / "publication" / "run.ps1",
            runner=lambda _argv, _log: ProcessResult(0, '{"resultClass":"COMPLETED"}', ""),
        ).plan(derivative(tmp_path), metadata, tmp_path / "out", "child-1", policy(), lambda _line: None)


def test_adjacent_real_publication_launcher_commits_verified_plan(tmp_path):
    metadata = tmp_path / "metadata.json"
    metadata.write_text('{"title":"Localized {language}"}', encoding="utf-8")
    launcher = APP.parent / "publication" / "run.ps1"

    fact = PublicPublicationPlanner(launcher).plan(
        derivative(tmp_path), metadata, tmp_path / "real", "adjacent-child", policy(), lambda _line: None
    )

    assert fact.plan_path.is_file()
    assert fact.plan_sha256 == digest(fact.plan_path)
    assert fact.job_count == 2
