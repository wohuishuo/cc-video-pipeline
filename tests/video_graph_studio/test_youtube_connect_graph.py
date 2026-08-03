import hashlib
import json
from pathlib import Path
import subprocess
import sys


APP = Path(__file__).resolve().parents[2] / "apps" / "video-graph-studio"
sys.path.insert(0, str(APP))

from studio.adapters import AdapterResult, CommandAdapter, YouTubeConnectAdapter, VerifyYouTubeCredentialAdapter
from studio.api import StudioApplication
from studio.engine import WorkflowEngine
from studio.server import build_runtime
from studio.store import RunStore


def envelope(payload):
    return {"contractId": "CMD-RUN-CREATE", "contractVersion": "1.0", "operationId": "youtube-connect-op", "correlationId": "youtube-connect-corr", "payload": payload}


def files(tmp_path):
    config = tmp_path / "client.json"; config.write_text('{"installed":{"client_id":"id","client_secret":"secret"}}', encoding="utf-8")
    vault = tmp_path / "vault.json"
    return config, vault


def test_connect_graph_admits_only_local_nonsecret_references(tmp_path, monkeypatch):
    config, vault = files(tmp_path); monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    store = RunStore(tmp_path / "studio.db"); app = StudioApplication(store, WorkflowEngine(store, {}), allowed_roots=(tmp_path,))

    status, response = app.handle("POST", "/api/v1/runs", {}, envelope({"templateId": "youtube-connect", "clientConfigPath": str(config), "credentialVaultPath": str(vault), "credentialId": "youtube-main", "label": "Main YouTube"}))
    run = store.get_run(response["value"]["runId"])

    assert status == 201
    assert [node["type"] for node in run["graph"]["nodes"]] == ["connect-youtube", "verify-youtube-credential"]
    assert run["parameters"]["credentialId"] == "youtube-main"
    assert "secret" not in json.dumps(run)


def test_connect_graph_uses_the_studio_vault_without_asking_the_browser_for_its_path(tmp_path, monkeypatch):
    config, vault = files(tmp_path)
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    store = RunStore(tmp_path / "studio.db")
    connections = type("Connections", (), {"vault_path": vault})()
    app = StudioApplication(
        store,
        WorkflowEngine(store, {}),
        allowed_roots=(tmp_path,),
        platform_connections=connections,
    )

    status, response = app.handle(
        "POST", "/api/v1/runs", {},
        envelope({"templateId": "youtube-connect", "clientConfigPath": str(config), "credentialId": "youtube-main", "label": "Main"}),
    )

    assert status == 201
    assert store.get_run(response["value"]["runId"])["parameters"]["credentialVaultPath"] == str(vault.resolve())


def test_connect_graph_rejects_vault_outside_user_home(tmp_path, monkeypatch):
    config, vault = files(tmp_path); home = tmp_path / "home"; home.mkdir(); monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    store = RunStore(tmp_path / "studio.db"); app = StudioApplication(store, WorkflowEngine(store, {}), allowed_roots=(tmp_path,))

    status, _ = app.handle("POST", "/api/v1/runs", {}, envelope({"templateId": "youtube-connect", "clientConfigPath": str(config), "credentialVaultPath": str(vault), "credentialId": "youtube-main", "label": "Main"}))

    assert status == 400
    assert store.list_runs() == []


def test_connect_graph_allows_vault_in_new_directory_inside_user_home(tmp_path, monkeypatch):
    config, _ = files(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    vault = home / "new-studio" / "vault.json"
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    store = RunStore(tmp_path / "studio.db")
    app = StudioApplication(store, WorkflowEngine(store, {}), allowed_roots=(tmp_path,))

    status, response = app.handle(
        "POST",
        "/api/v1/runs",
        {},
        envelope(
            {
                "templateId": "youtube-connect",
                "clientConfigPath": str(config),
                "credentialVaultPath": str(vault),
                "credentialId": "youtube-main",
                "label": "Main",
            }
        ),
    )

    assert status == 201
    assert store.get_run(response["value"]["runId"])["parameters"]["credentialVaultPath"] == str(vault.resolve())


def test_connect_and_verify_adapters_require_receipt_and_active_vault_fact(tmp_path, monkeypatch):
    config, vault = files(tmp_path); output = tmp_path / "oauth"; receipt = output / "run-1" / "youtube-oauth-receipt.json"; receipt.parent.mkdir(parents=True)
    receipt.write_text(json.dumps({"schemaVersion": 1, "operationId": "run-1:step:connect-youtube", "resultClass": "COMPLETED", "credentialId": "youtube-main", "provider": "youtube", "status": "ACTIVE", "scope": "https://www.googleapis.com/auth/youtube.upload"}), encoding="utf-8")
    seen = {"logs": []}
    def fake_execute(self, node, context, on_log, cancel_event):
        seen["argv"] = node.config["argv"]
        on_log('{"event":"authorization","url":"https://accounts.google.com/auth?state=ephemeral-secret"}')
        return AdapterResult(True, {"exitCode": 0})
    monkeypatch.setattr(CommandAdapter, "execute", fake_execute)
    context = {"runId": "run-1", "parameters": {"clientConfigPath": str(config), "credentialVaultPath": str(vault), "credentialId": "youtube-main", "label": "Main"}}

    connected = YouTubeConnectAdapter(tmp_path / "oauth.ps1", output).execute(type("Node", (), {"id": "connect-youtube"})(), context, seen["logs"].append, None)
    context["steps"] = [{"nodeId": "connect-youtube", "status": "COMPLETED", "result": connected.details}]
    runner = lambda argv, **kwargs: subprocess.CompletedProcess(argv, 0, '{"resultClass":"COMPLETED","value":{"credentialId":"youtube-main","provider":"youtube","status":"ACTIVE"}}', "")
    verified = VerifyYouTubeCredentialAdapter(tmp_path / "vault.ps1", runner=runner).execute(None, context, lambda _: None, None)

    assert connected.completed and verified.completed
    assert "--client-config" in seen["argv"] and "--vault" in seen["argv"]
    assert seen["logs"] == ["YouTube consent opened in the system browser; ephemeral authorization parameters were not persisted."]
    assert "ephemeral-secret" not in json.dumps(seen)
    assert connected.details["receiptSha256"] == hashlib.sha256(receipt.read_bytes()).hexdigest()


def test_runtime_registers_youtube_connect_adapters(tmp_path):
    _, engine = build_runtime(Path(__file__).resolve().parents[2], tmp_path / "runtime")

    assert isinstance(engine.adapters["connect-youtube"], YouTubeConnectAdapter)
    assert isinstance(engine.adapters["verify-youtube-credential"], VerifyYouTubeCredentialAdapter)
