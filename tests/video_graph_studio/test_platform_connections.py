import json
from pathlib import Path
import subprocess
import sys


APP = Path(__file__).resolve().parents[2] / "apps" / "video-graph-studio"
sys.path.insert(0, str(APP))

from studio.api import StudioApplication
from studio.engine import WorkflowEngine
from studio.platform_connections import PlatformConnectionService
from studio.store import RunStore


def test_catalog_reports_real_adapter_and_redacted_account_state(tmp_path):
    repository = tmp_path / "repo"
    (repository / "apps" / "youtube-publisher").mkdir(parents=True)
    (repository / "apps" / "youtube-publisher" / "run.ps1").write_text("", encoding="utf-8")
    payload = {
        "resultClass": "COMPLETED",
        "value": {"records": [
            {"credentialId": "youtube-main", "provider": "youtube", "label": "Main channel", "status": "ACTIVE"},
            {"credentialId": "deepseek-api", "provider": "deepseek", "label": "Translation", "status": "ACTIVE"},
        ]},
    }
    runner = lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, json.dumps(payload), "")
    service = PlatformConnectionService(repository, tmp_path / "vault.ps1", tmp_path / "vault.json", runner=runner)

    catalog = service.catalog()

    youtube = next(row for row in catalog if row["id"] == "youtube")
    douyin = next(row for row in catalog if row["id"] == "douyin")
    assert youtube["uploadState"] == "READY_PRIVATE"
    assert youtube["allowedVisibilities"] == ["private"]
    assert youtube["accounts"] == [{"id": "youtube-main", "label": "Main channel"}]
    assert douyin["uploadState"] == "ADAPTER_NOT_INSTALLED"
    assert douyin["accounts"] == []
    assert "deepseek" not in json.dumps(catalog)


def test_api_exposes_platform_connections_without_secrets(tmp_path):
    class Connections:
        def catalog(self):
            return [{"id": "youtube", "uploadState": "CONNECTION_REQUIRED", "accounts": []}]

    store = RunStore(tmp_path / "studio.db")
    app = StudioApplication(
        store,
        WorkflowEngine(store, {}),
        allowed_roots=(tmp_path,),
        platform_connections=Connections(),
    )

    status, payload = app.handle("GET", "/api/v1/platform-connections", {}, None)

    assert status == 200
    assert payload["platforms"][0]["uploadState"] == "CONNECTION_REQUIRED"
