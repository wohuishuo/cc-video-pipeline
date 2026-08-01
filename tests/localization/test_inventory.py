import sys
from pathlib import Path

import pytest


LOCALIZATION_ROOT = Path(__file__).resolve().parents[2] / "apps" / "localization"
sys.path.insert(0, str(LOCALIZATION_ROOT))

from localizer.inventory import InventoryError, discover_jobs  # noqa: E402


def test_discover_jobs_requires_exact_manifest_coverage(tmp_path):
    (tmp_path / "video-urls.txt").write_text(
        "https://www.douyin.com/video/111\nhttps://www.douyin.com/video/222\n",
        encoding="utf-8",
    )
    (tmp_path / "videos").mkdir()
    (tmp_path / "videos" / "[111] first.mp4").write_bytes(b"a")

    with pytest.raises(InventoryError, match="missing.*222"):
        discover_jobs(tmp_path / "video-urls.txt", tmp_path / "videos")


def test_discover_jobs_returns_one_fingerprinted_job_per_manifest_id(tmp_path):
    urls = tmp_path / "video-urls.txt"
    urls.write_text(
        "https://www.douyin.com/video/222?previous_page=web_code\n"
        "https://www.douyin.com/video/111\n",
        encoding="utf-8",
    )
    videos = tmp_path / "videos"
    videos.mkdir()
    (videos / "[111] first.mp4").write_bytes(b"first")
    (videos / "[222] second.mp4").write_bytes(b"second")

    manifest = discover_jobs(urls, videos)

    assert [job.id for job in manifest.jobs] == ["222", "111"]
    assert manifest.expected_ids == ("222", "111")
    assert [Path(job.source).name for job in manifest.jobs] == [
        "[222] second.mp4",
        "[111] first.mp4",
    ]
    assert all(len(job.source_sha256) == 64 for job in manifest.jobs)


def test_discover_jobs_rejects_duplicate_manifest_ids(tmp_path):
    urls = tmp_path / "video-urls.txt"
    urls.write_text(
        "https://www.douyin.com/video/111\nhttps://www.douyin.com/video/111\n",
        encoding="utf-8",
    )
    videos = tmp_path / "videos"
    videos.mkdir()
    (videos / "[111] first.mp4").write_bytes(b"first")

    with pytest.raises(InventoryError, match="duplicate manifest ID.*111"):
        discover_jobs(urls, videos)


def test_discover_jobs_rejects_duplicate_source_files_for_one_manifest_id(tmp_path):
    urls = tmp_path / "video-urls.txt"
    urls.write_text("https://www.douyin.com/video/111\n", encoding="utf-8")
    videos = tmp_path / "videos"
    videos.mkdir()
    (videos / "[111] first.mp4").write_bytes(b"first")
    (videos / "[111] second.mp4").write_bytes(b"second")

    with pytest.raises(InventoryError, match="duplicate source ID.*111"):
        discover_jobs(urls, videos)


def test_discover_jobs_rejects_source_ids_not_in_the_manifest(tmp_path):
    urls = tmp_path / "video-urls.txt"
    urls.write_text("https://www.douyin.com/video/111\n", encoding="utf-8")
    videos = tmp_path / "videos"
    videos.mkdir()
    (videos / "[111] first.mp4").write_bytes(b"first")
    (videos / "[999] non-target.mp4").write_bytes(b"other")

    with pytest.raises(InventoryError, match="unexpected.*999"):
        discover_jobs(urls, videos)
