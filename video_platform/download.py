from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path

from .models import JobReceipt, Platform
from .platforms import detect_platform
from .process import ProcessRunner


def fallback_heights(max_height: int) -> tuple[int, ...]:
    candidates = (1080, 720, 480, 360)
    values = tuple(height for height in candidates if height <= max_height)
    return values or (max_height,)


@dataclass(frozen=True)
class DownloadRequest:
    platform: Platform
    url: str
    output_dir: Path
    max_height: int = 1080
    cookies: Path | None = None

    def __post_init__(self) -> None:
        actual = detect_platform(self.url)
        if actual is not self.platform:
            raise ValueError(f"URL belongs to {actual.value}, not {self.platform.value}")
        if self.max_height < 144:
            raise ValueError("max_height must be at least 144")
        object.__setattr__(self, "output_dir", Path(self.output_dir).resolve())
        if self.cookies is not None:
            cookie_path = Path(self.cookies).resolve()
            if not cookie_path.is_file():
                raise ValueError(f"Cookie file does not exist: {cookie_path}")
            object.__setattr__(self, "cookies", cookie_path)


class YtDlpDownloader:
    def __init__(self, runner: ProcessRunner | None = None) -> None:
        self.runner = runner or ProcessRunner()

    def build_args(self, request: DownloadRequest) -> list[str]:
        request.output_dir.mkdir(parents=True, exist_ok=True)
        selector = (
            f"bv*[height<={request.max_height}]+ba/"
            f"b[height<={request.max_height}]/best[height<={request.max_height}]"
        )
        args = [
            "yt-dlp",
            "--no-playlist",
            "--newline",
            "--no-progress",
            "--write-info-json",
            "--merge-output-format",
            "mp4",
            "--format",
            selector,
            "--output",
            str(request.output_dir / "%(title).120B [%(id)s].%(ext)s"),
        ]
        if request.cookies:
            args.extend(["--cookies", str(request.cookies)])
        if request.platform is Platform.BILIBILI:
            args.extend([
                "--http-chunk-size", "10M",
                "--concurrent-fragments", "16",
                "--retries", "10",
                "--fragment-retries", "10",
            ])
        args.append(request.url)
        return args

    def _run_once(self, request: DownloadRequest):
        return self.runner.run(self.build_args(request))

    def download(self, request: DownloadRequest) -> JobReceipt:
        result = None
        authenticated_retry = False
        attempted_heights: list[int] = []
        for use_cookies in ((False, True) if request.cookies else (False,)):
            authenticated_retry = use_cookies
            for height in fallback_heights(request.max_height):
                attempted_heights.append(height)
                attempt = replace(request, max_height=height, cookies=request.cookies if use_cookies else None)
                result = self._run_once(attempt)
                if result.exit_code == 0:
                    break
            if result is not None and result.exit_code == 0:
                break
        if result is None or result.exit_code != 0:
            return JobReceipt(
                request.platform,
                "download",
                "failed",
                {"authenticated_retry": authenticated_retry, "attempted_heights": attempted_heights},
                error=(result.stderr[-4000:] if result else "No download attempt was made"),
            )

        media = self._latest_media(request.output_dir)
        if media is None:
            return JobReceipt(request.platform, "download", "failed", error="yt-dlp exited successfully but no media file was found")
        facts = self._probe(media)
        facts.update({
            "requested_max_height": request.max_height,
            "authenticated_retry": authenticated_retry,
            "attempted_heights": attempted_heights,
        })
        return JobReceipt(request.platform, "download", "ok", facts, str(media))

    @staticmethod
    def _latest_media(output_dir: Path) -> Path | None:
        extensions = {".mp4", ".mkv", ".webm", ".mov"}
        files = [path for path in output_dir.iterdir() if path.is_file() and path.suffix.lower() in extensions]
        return max(files, key=lambda path: path.stat().st_mtime, default=None)

    def _probe(self, media: Path) -> dict[str, object]:
        result = self.runner.run([
            "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(media)
        ])
        if result.exit_code != 0:
            raise RuntimeError(f"FFprobe failed: {result.stderr}")
        payload = json.loads(result.stdout)
        video = next((stream for stream in payload.get("streams", []) if stream.get("codec_type") == "video"), {})
        audio = next((stream for stream in payload.get("streams", []) if stream.get("codec_type") == "audio"), None)
        return {
            "width": int(video.get("width", 0)),
            "height": int(video.get("height", 0)),
            "video_codec": video.get("codec_name"),
            "has_audio": audio is not None,
            "audio_codec": audio.get("codec_name") if audio else None,
            "duration": float(payload.get("format", {}).get("duration", 0) or 0),
        }


class PlatformDownloader:
    def __init__(self, primary, social_fallback=None) -> None:
        self.primary = primary
        self.social_fallback = social_fallback

    def download(self, request: DownloadRequest) -> JobReceipt:
        receipt = self.primary.download(request)
        if (
            receipt.status != "ok"
            and self.social_fallback is not None
            and request.platform in {Platform.DOUYIN, Platform.TIKTOK}
        ):
            return self.social_fallback.download(request)
        return receipt
