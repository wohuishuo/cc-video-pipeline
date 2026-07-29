from ..models import Platform
from ..upload import UploadRequest
from . import SauUploadAdapter, common_upload_args


class TikTokUploadAdapter(SauUploadAdapter):
    platform = Platform.TIKTOK
    upstream_name = "tiktok"

    def build_upload_command(self, request: UploadRequest, metadata: dict) -> list[str]:
        return [str(self._python()), str(self.project_root / "tools" / "tiktok_upload_bridge.py"), "--checkout", str(self.checkout)] + common_upload_args(request, metadata)[1:]

    def login_command(self, account: str) -> list[str]:
        return [str(self._python()), str(self.project_root / "tools" / "tiktok_upload_bridge.py"), "--checkout", str(self.checkout), "login", "--account", account]

    def check_command(self, account: str) -> list[str]:
        return [str(self._python()), str(self.project_root / "tools" / "tiktok_upload_bridge.py"), "--checkout", str(self.checkout), "check", "--account", account]
