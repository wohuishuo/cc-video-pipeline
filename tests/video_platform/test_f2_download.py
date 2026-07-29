from pathlib import Path

from video_platform.download import DownloadRequest, PlatformDownloader
from video_platform.models import JobReceipt
from video_platform.f2_download import F2Downloader
from video_platform.models import Platform, ProcessResult


class RecordingRunner:
    def __init__(self, output_dir: Path, create_media: bool = True):
        self.output_dir = output_dir
        self.create_media = create_media
        self.calls = []

    def run(self, args, cwd=None, env=None):
        self.calls.append((list(args), env))
        if args[0] == "ffprobe":
            return ProcessResult(tuple(args), 0, '{"streams":[{"codec_type":"video","width":1080,"height":1920,"codec_name":"h264"},{"codec_type":"audio","codec_name":"aac"}],"format":{"duration":"12.5"}}', "")
        if self.create_media:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            (self.output_dir / "clip.mp4").write_bytes(b"media")
        return ProcessResult(tuple(args), 0, "ok", "")


def test_f2_builds_douyin_single_video_command_and_verifies_media(tmp_path):
    runner = RecordingRunner(tmp_path)
    request = DownloadRequest(Platform.DOUYIN, "https://www.douyin.com/video/7538955201693994298", tmp_path)
    receipt = F2Downloader(Path("f2.exe"), runner).download(request)
    command = runner.calls[0][0]
    assert command[1:3] == ["dy", "-u"]
    assert "one" in command
    assert receipt.status == "ok"
    assert receipt.facts["adapter"] == "f2"


def test_f2_does_not_treat_zero_exit_without_media_as_success(tmp_path):
    request = DownloadRequest(Platform.TIKTOK, "https://www.tiktok.com/@pokemonlife22/video/7059698374567611694", tmp_path)
    receipt = F2Downloader(Path("f2.exe"), RecordingRunner(tmp_path, create_media=False)).download(request)
    assert receipt.status == "failed"
    assert "no media" in receipt.error.lower()


def test_platform_downloader_uses_f2_only_after_primary_social_failure(tmp_path):
    class Adapter:
        def __init__(self, receipt):
            self.receipt = receipt
            self.calls = 0
        def download(self, request):
            self.calls += 1
            return self.receipt

    primary = Adapter(JobReceipt(Platform.DOUYIN, "download", "failed", error="cookies required"))
    fallback = Adapter(JobReceipt(Platform.DOUYIN, "download", "ok", {"adapter": "f2"}, "clip.mp4"))
    request = DownloadRequest(Platform.DOUYIN, "https://www.douyin.com/video/7538955201693994298", tmp_path)
    receipt = PlatformDownloader(primary, fallback).download(request)
    assert receipt.status == "ok"
    assert primary.calls == fallback.calls == 1
