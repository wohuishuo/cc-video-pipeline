import json
from pathlib import Path
import subprocess
import sys
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen


APP = Path(__file__).resolve().parents[2] / "apps" / "video-graph-studio"
sys.path.insert(0, str(APP))

from studio.client_contracts import ClientContractsCommandAdapter, ClientContractsError  # noqa: E402
from studio.server import create_server  # noqa: E402


class NoApplication:
    def handle(self, method, path, query, body):
        return 404, {"resultClass": "REJECTED_NOT_FOUND"}


class FakeContracts:
    def __init__(self):
        self.calls = 0

    def discover(self):
        self.calls += 1
        return {
            "resultClass": "COMPLETED",
            "value": {
                "bundle": {
                    "schemaVersion": 1,
                    "contractVersion": "1.0",
                    "commands": {key: {} for key in ("CMD-RUN-CREATE", "CMD-RUN-START", "CMD-RUN-CANCEL")},
                    "endpoints": {"GET /api/v1/contracts": {"scope": None}},
                },
                "sha256": "a" * 64,
            },
        }


def request(base, path, *, headers=None):
    value = Request(base + path, headers=headers or {})
    try:
        with urlopen(value, timeout=5) as response:
            return response.status, json.loads(response.read())
    except HTTPError as error:
        return error.code, json.loads(error.read())


def test_http_contract_discovery_is_public_before_workspace_admission(tmp_path):
    contracts = FakeContracts()
    server = create_server(
        "127.0.0.1", 0, NoApplication(), web_root=tmp_path,
        admission=object(), client_contracts=contracts,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        status, payload = request(f"http://127.0.0.1:{server.server_port}", "/api/v1/contracts")
        assert status == 200
        assert payload["value"]["bundle"]["contractVersion"] == "1.0"
        assert contracts.calls == 1
    finally:
        server.shutdown(); thread.join()


def test_command_adapter_parses_and_caches_public_cli_result(tmp_path, monkeypatch):
    payload = {"resultClass":"COMPLETED","value":{"bundle":{"schemaVersion":1,"contractVersion":"1.0","commands":{key:{} for key in ("CMD-RUN-CREATE","CMD-RUN-START","CMD-RUN-CANCEL")},"endpoints":{"GET /api/v1/contracts":{"scope":None}}},"sha256":"b"*64}}
    completed = subprocess.CompletedProcess([], 0, "note\n" + json.dumps(payload) + "\n", "")
    calls=[]
    monkeypatch.setattr("studio.client_contracts.subprocess.run", lambda *args, **kwargs: calls.append(args) or completed)
    adapter=ClientContractsCommandAdapter(tmp_path/"run.ps1")

    assert adapter.discover()==payload
    assert adapter.discover()==payload
    assert len(calls)==1


def test_command_adapter_fails_closed_on_malformed_bundle(tmp_path, monkeypatch):
    completed = subprocess.CompletedProcess([], 0, '{"resultClass":"COMPLETED","value":{"bundle":{}}}\n', "secret stderr")
    monkeypatch.setattr("studio.client_contracts.subprocess.run", lambda *args, **kwargs: completed)
    try:
        ClientContractsCommandAdapter(tmp_path/"run.ps1").discover()
    except ClientContractsError as error:
        assert "secret stderr" not in str(error)
    else:
        raise AssertionError("malformed contract bundle was admitted")
