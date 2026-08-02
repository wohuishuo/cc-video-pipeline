from ..models import Platform
from pathlib import Path
import re

from ..upload import PreparedUpload, UploadRequest
from . import SauUploadAdapter, common_upload_args


class YouTubeUploadAdapter(SauUploadAdapter):
    platform = Platform.YOUTUBE
    upstream_name = "youtube"

    def build_upload_command(self, request: UploadRequest, metadata: dict) -> list[str]:
        visibility = "private" if request.draft else str(metadata.get("visibility", "public"))
        return self._base() + common_upload_args(request, metadata) + ["--visibility", visibility, "--headed"]


class YouTubeApiUploadAdapter:
    """Route credential-backed private uploads to the repository-owned API MVP."""

    platform = Platform.YOUTUBE

    def __init__(self, project_root: Path) -> None:
        self.project_root = Path(project_root).resolve()
        self.checkout = self.project_root
        self.profile_dir = self.project_root / "receipts" / "youtube-api"

    def prepare(self, request: UploadRequest, credential_env: str, operation_id: str) -> PreparedUpload:
        if request.platform is not Platform.YOUTUBE:
            raise ValueError("Upload request routed to the wrong platform adapter")
        if not request.draft:
            raise ValueError("internal YouTube Publisher accepts private visibility only")
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", credential_env):
            raise ValueError("invalid credential environment name")
        if not operation_id:
            raise ValueError("operation ID is required")
        output = self.profile_dir / operation_id
        command = [
            "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
            str(self.project_root / "apps" / "youtube-publisher" / "run.ps1"),
            "upload", str(request.video), "--metadata", str(request.metadata),
            "--credential-env", credential_env, "--output-dir", str(output),
            "--operation-id", operation_id, "--json",
        ]
        return PreparedUpload(self.platform, "prepared", command, self.profile_dir)
