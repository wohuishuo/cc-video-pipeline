import json
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
from urllib.error import HTTPError
from urllib.error import URLError
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
                    "commands": {key: {} for key in ("CMD-RUN-CREATE", "CMD-RUN-START", "CMD-RUN-CANCEL", "CMD-RUN-RETRY")},
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


def free_loopback_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def test_public_launcher_resolves_current_studio_from_an_untrusted_cwd(tmp_path):
    fake_package = tmp_path / "studio"
    fake_package.mkdir()
    (fake_package / "__init__.py").write_text("", encoding="utf-8")
    (fake_package / "server.py").write_text(
        'raise RuntimeError("wrong studio package loaded")\n', encoding="utf-8"
    )
    port = free_loopback_port()
    launcher = APP / "run.ps1"
    process = subprocess.Popen(
        [
            "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(launcher), "-Port", str(port),
            "-DataRoot", str(tmp_path / "data"), "-NoBrowser",
        ],
        cwd=tmp_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            if process.poll() is not None:
                stdout, stderr = process.communicate(timeout=2)
                raise AssertionError(f"launcher exited early: {stdout} {stderr}")
            try:
                contract_status, contracts = request(base, "/api/v1/contracts")
                catalog_status, catalog = request(base, "/api/v1/capabilities")
                break
            except (URLError, TimeoutError, ConnectionError):
                time.sleep(0.15)
        else:
            raise AssertionError("launcher did not expose Studio within 12 seconds")

        assert contract_status == 200
        assert contracts["value"]["bundle"]["commands"]["CMD-RUN-CREATE"] is not None
        assert catalog_status == 200
        assert len(catalog["capabilities"]) == 20
        assert all(row["templateId"] and row["nodes"] for row in catalog["capabilities"])
    finally:
        subprocess.run(
            ["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
            capture_output=True,
            check=False,
        )


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
    payload = {"resultClass":"COMPLETED","value":{"bundle":{"schemaVersion":1,"contractVersion":"1.0","commands":{key:{} for key in ("CMD-RUN-CREATE","CMD-RUN-START","CMD-RUN-CANCEL","CMD-RUN-RETRY")},"endpoints":{"GET /api/v1/contracts":{"scope":None}}},"sha256":"b"*64}}
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
