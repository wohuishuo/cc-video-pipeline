from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .models import Platform


class DuplicateUpload(RuntimeError):
    pass


@dataclass(frozen=True)
class UploadRequest:
    platform: Platform
    video: Path
    metadata: Path
    account: str
    draft: bool = True
    idempotency_key: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("video", "metadata"):
            path = Path(getattr(self, field_name)).resolve()
            if not path.is_file():
                raise ValueError(f"{field_name} does not exist: {path}")
            object.__setattr__(self, field_name, path)
        if not self.account.strip():
            raise ValueError("account is required")


@dataclass(frozen=True)
class PreparedUpload:
    platform: Platform
    status: str
    command: list[str]
    profile_dir: Path


class UploadLedger:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def reserve(self, key: str, platform: Platform) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        existing = set()
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    item = json.loads(line)
                    existing.add((item["key"], item["platform"]))
        identity = (key, platform.value)
        if identity in existing:
            raise DuplicateUpload(f"Duplicate upload key for {platform.value}: {key}")
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"key": key, "platform": platform.value}) + "\n")


def load_metadata(path: Path) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not str(payload.get("title", "")).strip():
        raise ValueError("metadata.title is required")
    payload.setdefault("description", "")
    payload.setdefault("tags", [])
    return payload


def build_upload_adapters(project_root: Path):
    from .uploaders.bilibili import BilibiliUploadAdapter
    from .uploaders.douyin import DouyinUploadAdapter
    from .uploaders.tiktok import TikTokUploadAdapter
    from .uploaders.youtube import YouTubeUploadAdapter

    root = Path(project_root).resolve()
    return {
        Platform.YOUTUBE: YouTubeUploadAdapter(root),
        Platform.BILIBILI: BilibiliUploadAdapter(root),
        Platform.DOUYIN: DouyinUploadAdapter(root),
        Platform.TIKTOK: TikTokUploadAdapter(root),
    }
