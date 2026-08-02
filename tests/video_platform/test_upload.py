import json
from pathlib import Path

import pytest

from video_platform.models import Platform
from video_platform.upload import DuplicateUpload, UploadLedger, UploadRequest, build_upload_adapters
from video_platform.uploaders.youtube import YouTubeApiUploadAdapter


def _video_and_metadata(tmp_path: Path):
    video = tmp_path / "video.mp4"
    video.write_bytes(b"not-real-video")
    metadata = tmp_path / "metadata.json"
    metadata.write_text(json.dumps({"title": "Test", "description": "Draft", "tags": ["test"], "tid": 17}), encoding="utf-8")
    return video, metadata


def test_prepare_does_not_execute_publish_command(tmp_path):
    video, metadata = _video_and_metadata(tmp_path)
    request = UploadRequest(Platform.DOUYIN, video, metadata, "account", draft=True)
    adapter = build_upload_adapters(tmp_path)[Platform.DOUYIN]
    prepared = adapter.prepare(request)
    assert prepared.status == "prepared"
    assert "upload-video" in prepared.command


def test_each_adapter_uses_its_own_profile_directory(tmp_path):
    adapters = build_upload_adapters(tmp_path)
    assert len({adapter.profile_dir for adapter in adapters.values()}) == 4


def test_youtube_draft_is_forced_private(tmp_path):
    video, metadata = _video_and_metadata(tmp_path)
    request = UploadRequest(Platform.YOUTUBE, video, metadata, "account", draft=True)
    prepared = build_upload_adapters(tmp_path)[Platform.YOUTUBE].prepare(request)
    index = prepared.command.index("--visibility")
    assert prepared.command[index + 1] == "private"


def test_duplicate_idempotency_key_is_rejected(tmp_path):
    ledger = UploadLedger(tmp_path / "uploads.jsonl")
    ledger.reserve("same", Platform.TIKTOK)
    with pytest.raises(DuplicateUpload):
        ledger.reserve("same", Platform.TIKTOK)


def test_credential_backed_youtube_command_uses_internal_private_publisher(tmp_path):
    video, metadata = _video_and_metadata(tmp_path)
    request = UploadRequest(Platform.YOUTUBE, video, metadata, "account", draft=True)

    prepared = YouTubeApiUploadAdapter(tmp_path).prepare(request, "VIDEO_PLATFORM_CREDENTIAL", "operation-1")

    command = " ".join(prepared.command)
    assert "apps\\youtube-publisher\\run.ps1" in command
    assert "--credential-env VIDEO_PLATFORM_CREDENTIAL" in command
    assert "--operation-id operation-1" in command
    assert "--public" not in command


def test_internal_youtube_publisher_rejects_public_request(tmp_path):
    video, metadata = _video_and_metadata(tmp_path)
    request = UploadRequest(Platform.YOUTUBE, video, metadata, "account", draft=False)

    with pytest.raises(ValueError, match="private"):
        YouTubeApiUploadAdapter(tmp_path).prepare(request, "VIDEO_PLATFORM_CREDENTIAL", "operation-1")
