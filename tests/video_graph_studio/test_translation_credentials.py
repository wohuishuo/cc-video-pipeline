import json
from pathlib import Path
import subprocess
import sys


APP = Path(__file__).resolve().parents[2] / "apps" / "video-graph-studio"
sys.path.insert(0, str(APP))

from studio.adapters import wrap_command_with_vault  # noqa: E402
from studio.api import StudioApplication  # noqa: E402
from studio.engine import WorkflowEngine  # noqa: E402
from studio.store import RunStore  # noqa: E402
from studio.translation_credentials import TranslationCredentialService  # noqa: E402


class FakeRunner:
    def __init__(self):
        self.calls = []

    def __call__(self, argv, **kwargs):
        self.calls.append((argv, kwargs))
        operation = argv[argv.index("-File") + 2]
        if operation == "describe":
            return subprocess.CompletedProcess(argv, 2, '{"resultClass":"REJECTED_NOT_FOUND","value":{}}', "")
        return subprocess.CompletedProcess(
            argv,
            0,
            '{"resultClass":"COMPLETED","value":{"credentialId":"deepseek-api","provider":"deepseek","status":"ACTIVE"}}',
            "",
        )


def test_translation_credential_service_keeps_secret_out_of_argv_and_response(tmp_path):
    runner = FakeRunner()
    service = TranslationCredentialService(tmp_path / "vault.ps1", tmp_path / "vault.json", runner=runner)

    result = service.configure_deepseek("sk-private-value")

    assert result == {"provider": "deepseek", "configured": True, "status": "ACTIVE"}
    rendered_calls = json.dumps([call[0] for call in runner.calls])
    assert "sk-private-value" not in rendered_calls
    assert all("sk-private-value" not in (call[1].get("stdout", "") or "") for call in runner.calls)
    assert "DEEPSEEK_API_KEY" not in runner.calls[-1][1]["env"]


class FakeCredentials:
    def __init__(self):
        self.ready = False
        self.received = None

    def deepseek_configured(self):
        return self.ready

    def configure_deepseek(self, secret):
        self.received = secret
        self.ready = True
        return {"provider": "deepseek", "configured": True, "status": "ACTIVE"}


def test_api_exposes_an_actionable_deepseek_setup_without_echoing_the_key(tmp_path, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    credentials = FakeCredentials()
    store = RunStore(tmp_path / "studio.db")
    app = StudioApplication(
        store,
        WorkflowEngine(store, {}),
        allowed_roots=(tmp_path,),
        translation_credentials=credentials,
    )

    before_status, before = app.handle("GET", "/api/v1/translation-providers", {}, None)
    save_status, saved = app.handle(
        "POST",
        "/api/v1/translation-providers/deepseek/credential",
        {},
        {"apiKey": "sk-private-value"},
    )
    after_status, after = app.handle("GET", "/api/v1/translation-providers", {}, None)

    assert before_status == after_status == 200
    assert next(row for row in before["providers"] if row["id"] == "deepseek")["ready"] is False
    assert save_status == 200
    assert saved == {"resultClass": "COMPLETED", "value": {"provider": "deepseek", "configured": True, "status": "ACTIVE"}}
    assert credentials.received == "sk-private-value"
    assert "sk-private-value" not in json.dumps(saved)
    assert next(row for row in after["providers"] if row["id"] == "deepseek")["ready"] is True


def test_vault_wrapper_injects_deepseek_only_inside_the_child_environment(tmp_path):
    command = ["powershell.exe", "-NoProfile", "-File", "translation.ps1", "--json"]

    wrapped = wrap_command_with_vault(
        command,
        vault_launcher=tmp_path / "vault.ps1",
        vault_path=tmp_path / "vault.json",
        credential_id="deepseek-api",
        provider="deepseek",
        target_environment="DEEPSEEK_API_KEY",
    )

    assert wrapped[:7] == [
        "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
        str((tmp_path / "vault.ps1").resolve()), "run",
    ]
    assert "--expected-provider" in wrapped and "deepseek" in wrapped
    assert "--target-env" in wrapped and "DEEPSEEK_API_KEY" in wrapped
    assert "--argument=-NoProfile" in wrapped
    assert "--argument=--json" in wrapped
