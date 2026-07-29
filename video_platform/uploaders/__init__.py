from __future__ import annotations

import os
from pathlib import Path

from ..models import Platform
from ..upload import PreparedUpload, UploadRequest, load_metadata


class SauUploadAdapter:
    platform: Platform
    upstream_name: str

    def __init__(self, project_root: Path) -> None:
        self.project_root = Path(project_root)
        self.checkout = self.project_root / ".tools" / "social-auto-upload"
        self.profile_dir = self.project_root / "profiles" / self.platform.value

    def _python(self) -> Path:
        relative = Path("Scripts/python.exe") if os.name == "nt" else Path("bin/python")
        return self.checkout / ".venv" / relative

    def _base(self) -> list[str]:
        return [str(self._python()), str(self.checkout / "sau_cli.py"), self.upstream_name]

    def prepare(self, request: UploadRequest) -> PreparedUpload:
        if request.platform is not self.platform:
            raise ValueError("Upload request routed to the wrong platform adapter")
        metadata = load_metadata(request.metadata)
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        return PreparedUpload(self.platform, "prepared", self.build_upload_command(request, metadata), self.profile_dir)

    def build_upload_command(self, request: UploadRequest, metadata: dict) -> list[str]:
        raise NotImplementedError

    def login_command(self, account: str) -> list[str]:
        return self._base() + ["login", "--account", account, "--headed"]

    def check_command(self, account: str) -> list[str]:
        return self._base() + ["check", "--account", account]


def common_upload_args(request: UploadRequest, metadata: dict) -> list[str]:
    tags = ",".join(str(tag).lstrip("#") for tag in metadata.get("tags", []))
    return [
        "upload-video", "--account", request.account, "--file", str(request.video),
        "--title", str(metadata["title"]), "--desc", str(metadata.get("description", "")), "--tags", tags,
    ]
