import json
from pathlib import Path
import subprocess
import sys
import threading
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen


APP = Path(__file__).resolve().parents[2] / "apps" / "video-graph-studio"
sys.path.insert(0, str(APP))

from studio.admission import (
    AdmissionDecision,
    TOKEN_ENVIRONMENT_VARIABLE,
    WorkspaceAccessCommandAdapter,
)
from studio.server import create_server


class EchoApplication:
    def handle(self, method, path, query, body):
        if path == "/api/v1/health":
            return 200, {"contractVersion": "1.0", "database": "ready"}
        return 200, {"method": method, "path": path, "body": body}


class FakeAdmission:
    workspace_id = "local"

    def __init__(self):
        self.calls = []

    def authorize(self, workspace_id: str, token: str, scope: str) -> AdmissionDecision:
        self.calls.append((workspace_id, token, scope))
        if workspace_id != self.workspace_id:
            return AdmissionDecision(False, "REJECTED_WORKSPACE", "wrong workspace")
        scopes = {"reader": {"runs:read", "artifacts:read"}, "writer": {"runs:read", "runs:write"}}
        if scope not in scopes.get(token, set()):
            return AdmissionDecision(False, "REJECTED_UNAUTHORIZED", "scope denied")
        return AdmissionDecision(True, "AUTHORIZED", "authorized")


def request(base: str, path: str, *, method="GET", body=None, headers=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = Request(
        base + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    try:
        with urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read())
    except HTTPError as error:
        return error.code, json.loads(error.read())


def test_secure_transport_requires_workspace_and_route_scope(tmp_path):
    admission = FakeAdmission()
    server = create_server(
        "127.0.0.1",
        0,
        EchoApplication(),
        web_root=tmp_path,
        admission=admission,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        health_status, health = request(base, "/api/v1/health")
        missing_status, missing = request(base, "/api/v1/runs")
        wrong_status, wrong = request(
            base,
            "/api/v1/runs",
            headers={"Authorization": "Bearer reader", "X-Workspace-Id": "other"},
        )
        read_status, _ = request(
            base,
            "/api/v1/runs",
            headers={"Authorization": "Bearer reader", "X-Workspace-Id": "local"},
        )
        write_denied_status, write_denied = request(
            base,
            "/api/v1/runs",
            method="POST",
            body={},
            headers={"Authorization": "Bearer reader", "X-Workspace-Id": "local"},
        )
        write_status, written = request(
            base,
            "/api/v1/runs",
            method="POST",
            body={"ok": True},
            headers={"Authorization": "Bearer writer", "X-Workspace-Id": "local"},
        )

        assert health_status == 200
        assert health["accessRequired"] is True
        assert health["workspaceId"] == "local"
        assert missing_status == 401 and missing["resultClass"] == "REJECTED_UNAUTHORIZED"
        assert wrong_status == 403 and wrong["resultClass"] == "REJECTED_WORKSPACE"
        assert read_status == 200
        assert write_denied_status == 403
        assert write_denied["resultClass"] == "REJECTED_UNAUTHORIZED"
        assert write_status == 200 and written["body"] == {"ok": True}
        assert all(call[1] in {"reader", "writer"} for call in admission.calls)
    finally:
        server.shutdown()
        thread.join()


def test_folder_query_requires_artifact_scope(tmp_path):
    admission = FakeAdmission()
    server = create_server(
        "127.0.0.1", 0, EchoApplication(), web_root=tmp_path, admission=admission
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        status, _ = request(
            base,
            "/api/v1/folders",
            headers={"Authorization": "Bearer reader", "X-Workspace-Id": "local"},
        )
        assert status == 200
        assert admission.calls[-1][2] == "artifacts:read"
    finally:
        server.shutdown()
        thread.join()


def test_command_adapter_keeps_plaintext_out_of_argv_and_parses_public_json(tmp_path):
    adapter = WorkspaceAccessCommandAdapter(
        tmp_path / "run.ps1", tmp_path / "access.json", "local"
    )
    described = subprocess.CompletedProcess(
        [], 0, '{"resultClass":"COMPLETED","value":{"workspaceId":"local","allowedRoots":["C:/media"]}}\n', ""
    )
    authorized = subprocess.CompletedProcess(
        [], 0, '{"resultClass":"AUTHORIZED","value":{"workspaceId":"local"}}\n', ""
    )
    secret = "vgst_0123456789abcdef_secret"

    with patch("studio.admission.subprocess.run", side_effect=[described, authorized]) as run:
        assert adapter.describe_workspace()["allowedRoots"] == ["C:/media"]
        decision = adapter.authorize("local", secret, "runs:read")

    assert decision.authorized is True
    authorization_call = run.call_args_list[1]
    assert secret not in authorization_call.args[0]
    assert authorization_call.kwargs["env"][TOKEN_ENVIRONMENT_VARIABLE] == secret
