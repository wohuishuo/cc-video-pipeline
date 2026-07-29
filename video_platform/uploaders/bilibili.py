from ..models import Platform
from ..upload import UploadRequest
from . import SauUploadAdapter, common_upload_args


class BilibiliUploadAdapter(SauUploadAdapter):
    platform = Platform.BILIBILI
    upstream_name = "bilibili"

    def build_upload_command(self, request: UploadRequest, metadata: dict) -> list[str]:
        return self._base() + common_upload_args(request, metadata) + ["--tid", str(metadata.get("tid", 17))]
