from __future__ import annotations

from pathlib import Path

from .download import DownloadRequest, YtDlpDownloader
from .models import JobReceipt, Platform
from .process import ProcessRunner


class F2Downloader:
    """Independent Douyin/TikTok fallback backed by a pinned f2 checkout."""

    APPS = {Platform.DOUYIN: "dy", Platform.TIKTOK: "tk"}

    def __init__(self, executable: Path, runner: ProcessRunner | None = None) -> None:
        self.executable = Path(executable)
        self.runner = runner or ProcessRunner()

    def download(self, request: DownloadRequest) -> JobReceipt:
        app = self.APPS.get(request.platform)
        if app is None:
            return JobReceipt(request.platform, "download", "failed", error="f2 supports only Douyin and TikTok in this adapter")
        request.output_dir.mkdir(parents=True, exist_ok=True)
        args = [str(self.executable), app, "-u", request.url, "-M", "one", "-p", str(request.output_dir), "-l", "en_US"]
        if request.cookies:
            args.extend(["-k", request.cookies.read_text(encoding="utf-8").strip()])
        result = self.runner.run(args, env={"PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"})
        media = YtDlpDownloader._latest_media(request.output_dir)
        if result.exit_code != 0 or media is None:
            detail = result.stderr[-4000:] or result.stdout[-4000:]
            if media is None:
                detail = f"f2 exited {result.exit_code} but no media file was produced. {detail}"
            return JobReceipt(request.platform, "download", "failed", {"adapter": "f2"}, error=detail)
        facts = YtDlpDownloader(self.runner)._probe(media)
        facts.update({"adapter": "f2", "requested_max_height": request.max_height})
        return JobReceipt(request.platform, "download", "ok", facts, str(media))
