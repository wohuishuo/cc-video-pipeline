from ..models import Platform
from ..upload import UploadRequest
from . import SauUploadAdapter, common_upload_args


class DouyinUploadAdapter(SauUploadAdapter):
    platform = Platform.DOUYIN
    upstream_name = "douyin"

    def build_upload_command(self, request: UploadRequest, metadata: dict) -> list[str]:
        return self._base() + common_upload_args(request, metadata) + ["--headed"]
