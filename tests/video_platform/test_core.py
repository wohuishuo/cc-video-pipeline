import json
import sys

from video_platform.models import JobReceipt, Platform
from video_platform.process import ProcessRunner
from video_platform.receipts import write_receipt


def test_receipt_json_redacts_credentials(tmp_path):
    receipt = JobReceipt(
        platform=Platform.YOUTUBE,
        operation="download",
        status="ok",
        facts={"cookie_file": "secret.txt", "height": 1080},
    )
    path = write_receipt(receipt, tmp_path / "receipt.json")
    content = path.read_text(encoding="utf-8")
    assert "secret.txt" not in content
    assert json.loads(content)["facts"]["cookie_file"] == "[REDACTED]"


def test_process_runner_returns_structured_result():
    result = ProcessRunner().run([sys.executable, "-c", "print('ok')"])
    assert result.exit_code == 0
    assert result.stdout.strip() == "ok"
    assert result.args[0] == sys.executable
