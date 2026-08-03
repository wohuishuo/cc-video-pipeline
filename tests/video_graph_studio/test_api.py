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
from studio.server import _allowed_roots, create_server  # noqa: E402
from studio.store import CommandResult, RunStore  # noqa: E402


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


def test_retry_endpoint_validates_command_and_delegates_to_engine(tmp_path):
    calls = []

    class RetryEngine:
        def retry(self, run_id):
            calls.append(run_id)
            return CommandResult("COMPLETED", {"runId": run_id})

    app = StudioApplication(RunStore(tmp_path / "studio.db"), RetryEngine(), allowed_roots=(tmp_path,))
    command = {
        "contractId": "CMD-RUN-RETRY", "contractVersion": "1.0",
        "operationId": "retry-1", "correlationId": "corr-1", "payload": {},
    }

    status, response = app.handle("POST", "/api/v1/runs/run-123/retry", {}, command)

    assert status == 202
    assert response == {"resultClass": "COMPLETED", "value": {"runId": "run-123"}}
    assert calls == ["run-123"]


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


def test_default_roots_include_existing_onedrive_media_folders(tmp_path):
    repository = tmp_path / "OneDrive" / "Documents" / "video"
    repository.mkdir(parents=True)
    onedrive_desktop = tmp_path / "OneDrive" / "Desktop"
    onedrive_videos = tmp_path / "OneDrive" / "Videos"
    onedrive_desktop.mkdir(parents=True)
    onedrive_videos.mkdir(parents=True)

    roots = _allowed_roots(repository, home=tmp_path)

    assert repository.resolve() in roots
    assert onedrive_desktop.resolve() in roots
    assert onedrive_videos.resolve() in roots


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
            "defaultOutputRoot": str(tmp_path.resolve()),
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
    (source / "Another.MOV").write_bytes(b"second")
    (source / "notes.txt").write_text("ignore", encoding="utf-8")
    server, thread, base = running_server(tmp_path)
    try:
        status, body = request_json(base, "/api/v1/folders?" + urlencode({"path": str(source)}))
        assert status == 200
        assert body["videoCount"] == 2
        assert body["directories"][0]["name"] == "child"
        assert body["videos"] == [
            {
                "name": "Another.MOV",
                "path": str((source / "Another.MOV").resolve()),
                "size": 6,
            },
            {
                "name": "clip.mp4",
                "path": str((source / "clip.mp4").resolve()),
                "size": 5,
            },
        ]
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
