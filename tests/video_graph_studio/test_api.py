import json
from pathlib import Path
import sys
import threading
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


APP = Path(__file__).resolve().parents[2] / "apps" / "video-graph-studio"
sys.path.insert(0, str(APP))

from studio.adapters import AdapterResult  # noqa: E402
from studio.api import StudioApplication  # noqa: E402
from studio.engine import WorkflowEngine  # noqa: E402
from studio.server import create_server  # noqa: E402
from studio.store import RunStore  # noqa: E402


class SuccessAdapter:
    def execute(self, node, context, on_log, cancel_event):
        on_log(f"{node.id} ok")
        return AdapterResult(True, {"node": node.id})


def request_json(base: str, path: str, *, method: str = "GET", body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = Request(
        base + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read())
    except HTTPError as error:
        return error.code, json.loads(error.read())


def running_server(tmp_path):
    store = RunStore(tmp_path / "studio.db")
    adapter = SuccessAdapter()
    engine = WorkflowEngine(
        store,
        {
            "prepared-folder": adapter,
            "edge-localize": adapter,
            "verify-output": adapter,
        },
    )
    application = StudioApplication(store, engine, allowed_roots=(tmp_path,))
    server = create_server("127.0.0.1", 0, application, web_root=tmp_path / "web")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, f"http://127.0.0.1:{server.server_port}"


def test_health_is_served_over_real_loopback_http(tmp_path):
    server, thread, base = running_server(tmp_path)
    try:
        status, body = request_json(base, "/api/v1/health")
        assert status == 200
        assert body == {
            "contractVersion": "1.0",
            "database": "ready",
            "activeWorkers": 0,
            "queuedRuns": 0,
        }
        queue_status, queue = request_json(base, "/api/v1/queue")
        assert queue_status == 200
        assert queue == {
            "contractVersion": "1.0",
            "activeRunId": None,
            "queuedRuns": 0,
            "entries": [],
        }
    finally:
        server.shutdown()
        thread.join()


def test_folder_browser_rejects_escape_and_lists_supported_media(tmp_path):
    source = tmp_path / "source"
    (source / "child").mkdir(parents=True)
    (source / "clip.mp4").write_bytes(b"video")
    server, thread, base = running_server(tmp_path)
    try:
        status, body = request_json(base, "/api/v1/folders?" + urlencode({"path": str(source)}))
        assert status == 200
        assert body["videoCount"] == 1
        assert body["directories"][0]["name"] == "child"
        status, body = request_json(base, "/api/v1/folders?" + urlencode({"path": str(tmp_path.parent)}))
        assert status == 403
        assert body["resultClass"] == "REJECTED_UNAUTHORIZED"
    finally:
        server.shutdown()
        thread.join()


def test_create_replay_conflict_and_start_use_versioned_commands(tmp_path):
    server, thread, base = running_server(tmp_path)
    command = {
        "contractId": "CMD-RUN-CREATE",
        "contractVersion": "1.0",
        "operationId": "op-1",
        "correlationId": "corr-1",
        "payload": {
            "sourceRoot": str(tmp_path),
            "languages": ["ru-RU"],
            "voice": "ru-RU-DmitryNeural",
            "platforms": ["local"],
        },
    }
    try:
        status, first = request_json(base, "/api/v1/runs", method="POST", body=command)
        status2, replay = request_json(base, "/api/v1/runs", method="POST", body=command)
        conflict_command = json.loads(json.dumps(command))
        conflict_command["payload"]["voice"] = "ru-RU-SvetlanaNeural"
        status3, conflict = request_json(
            base, "/api/v1/runs", method="POST", body=conflict_command
        )
        run_id = first["value"]["runId"]
        start = {
            "contractId": "CMD-RUN-START",
            "contractVersion": "1.0",
            "operationId": "start-1",
            "correlationId": "corr-1",
            "payload": {},
        }
        status4, _ = request_json(
            base, f"/api/v1/runs/{run_id}/start", method="POST", body=start
        )
        deadline = time.monotonic() + 5
        while True:
            _, projected = request_json(base, f"/api/v1/runs/{run_id}")
            if projected["status"] == "COMPLETED":
                break
            assert time.monotonic() < deadline
            time.sleep(0.02)

        assert (status, status2, status3, status4) == (201, 200, 409, 202)
        assert replay["resultClass"] == "DUPLICATE_COMPLETED"
        assert replay["value"]["runId"] == run_id
        assert conflict["resultClass"] == "REJECTED_CONFLICT"
        assert [step["status"] for step in projected["steps"]] == [
            "COMPLETED",
            "COMPLETED",
            "COMPLETED",
        ]
    finally:
        server.shutdown()
        thread.join()
