from ..models import Platform
from ..upload import UploadRequest
from . import SauUploadAdapter, common_upload_args


class YouTubeUploadAdapter(SauUploadAdapter):
    platform = Platform.YOUTUBE
    upstream_name = "youtube"

    def build_upload_command(self, request: UploadRequest, metadata: dict) -> list[str]:
        visibility = "private" if request.draft else str(metadata.get("visibility", "public"))
        return self._base() + common_upload_args(request, metadata) + ["--visibility", visibility, "--headed"]
