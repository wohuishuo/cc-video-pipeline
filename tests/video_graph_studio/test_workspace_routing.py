import json
from pathlib import Path
import subprocess
import sys
import threading
import time
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen


APP = Path(__file__).resolve().parents[2] / "apps" / "video-graph-studio"
sys.path.insert(0, str(APP))

from studio.admission import AdmissionDecision
from studio.adapters import AdapterResult
from studio.contracts import GraphDefinition
from studio.engine import WorkflowEngine
from studio.server import create_server
from studio.store import CreateRun, RunStore
from studio.workspace_routing import (
    WorkspaceRoutingError,
    WorkspaceRuntimeRouter,
    WorkspaceStorageCommandAdapter,
)


class RecordingApplication:
    def __init__(self, workspace_id):
        self.workspace_id = workspace_id
        self.calls = []

    def handle(self, method, path, query, body):
        self.calls.append((method, path, body))
        return 200, {"workspaceId": self.workspace_id, "method": method, "body": body}


class MultiAdmission:
    workspace_id = None

    def authorize(self, workspace_id, token, scope):
        if token != f"{workspace_id}-writer":
            return AdmissionDecision(False, "REJECTED_UNAUTHORIZED", "scope denied")
        return AdmissionDecision(True, "AUTHORIZED", "authorized")


class FakeTransportRouter:
    def __init__(self):
        self.apps = {key: RecordingApplication(key) for key in ("alpha", "beta")}
        self.calls = []

    def application_for(self, workspace_id, *, required_bytes=0):
        self.calls.append((workspace_id, required_bytes))
        return self.apps[workspace_id]

    def health(self):
        return {"database": "workspace-routed", "activeWorkers": 0, "queuedRuns": 0}


def request(base, path, *, method="GET", body=None, workspace=None, token=None):
    headers = {"Content-Type": "application/json"}
    if workspace:
        headers["X-Workspace-Id"] = workspace
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    value = Request(base + path, data=data, method=method, headers=headers)
    try:
        with urlopen(value, timeout=5) as response:
            return response.status, json.loads(response.read())
    except HTTPError as error:
        return error.code, json.loads(error.read())


def test_transport_routes_authorized_workspaces_and_denies_cross_workspace(tmp_path):
    router = FakeTransportRouter()
    server = create_server(
        "127.0.0.1",
        0,
        None,
        web_root=tmp_path,
        admission=MultiAdmission(),
        workspace_router=router,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        health_status, health = request(base, "/api/v1/health")
        alpha_status, alpha = request(
            base,
            "/api/v1/runs",
            method="POST",
            body={"name": "alpha"},
            workspace="alpha",
            token="alpha-writer",
        )
        beta_status, beta = request(
            base,
            "/api/v1/runs",
            method="POST",
            body={"name": "beta"},
            workspace="beta",
            token="beta-writer",
        )
        denied_status, denied = request(
            base,
            "/api/v1/runs",
            workspace="beta",
            token="alpha-writer",
        )

        assert health_status == 200
        assert health["multiWorkspace"] is True
        assert alpha_status == beta_status == 200
        assert alpha["workspaceId"] == "alpha" and beta["workspaceId"] == "beta"
        assert denied_status == 403
        assert denied["resultClass"] == "REJECTED_UNAUTHORIZED"
        assert router.calls == [("alpha", 1), ("beta", 1)]
        assert len(router.apps["alpha"].calls) == len(router.apps["beta"].calls) == 1
    finally:
        server.shutdown()
        thread.join()


class FakeAccess:
    def describe_workspace(self, workspace_id):
        return {"workspaceId": workspace_id, "allowedRoots": [f"C:/{workspace_id}/sources"]}


class FakeStorage:
    def __init__(self):
        self.capacity_calls = []

    def describe_workspace(self, workspace_id):
        return {
            "workspaceId": workspace_id,
            "roots": {
                "state": f"C:/{workspace_id}/state",
                "artifacts": f"C:/{workspace_id}/artifacts",
                "temp": f"C:/{workspace_id}/temp",
            },
        }

    def check_capacity(self, workspace_id, required_bytes):
        self.capacity_calls.append((workspace_id, required_bytes))
        return {"resultClass": "ALLOWED", "value": {"workspaceId": workspace_id}}


class FakeEngine:
    def __init__(self):
        self.shutdown_calls = 0

    def shutdown(self):
        self.shutdown_calls += 1


def test_runtime_router_builds_and_caches_isolated_roots_then_shuts_down():
    storage = FakeStorage()
    builds = []

    def factory(workspace_id, state_root, artifact_root, allowed_roots):
        result = RecordingApplication(workspace_id), FakeEngine()
        builds.append((workspace_id, state_root, artifact_root, allowed_roots, result))
        return result

    router = WorkspaceRuntimeRouter(FakeAccess(), storage, factory)

    alpha = router.application_for("alpha", required_bytes=1)
    replay = router.application_for("alpha")
    beta = router.application_for("beta")
    health = router.health()
    router.shutdown()

    assert alpha is replay and alpha is not beta
    assert len(builds) == 2
    assert builds[0][:4] == (
        "alpha",
        Path("C:/alpha/state/video-graph-studio"),
        Path("C:/alpha/artifacts/video-graph-studio"),
        (Path("C:/alpha/sources"),),
    )
    assert storage.capacity_calls == [("alpha", 1)]
    assert health["initializedWorkspaces"] == 2
    assert all(item[4][1].shutdown_calls == 1 for item in builds)


def test_runtime_router_rejects_capacity_before_building_workspace():
    storage = FakeStorage()
    storage.check_capacity = lambda workspace_id, required_bytes: {
        "resultClass": "REJECTED_QUOTA",
        "value": {"workspaceId": workspace_id},
    }
    builds = []
    router = WorkspaceRuntimeRouter(
        FakeAccess(), storage, lambda *arguments: builds.append(arguments)
    )

    try:
        router.application_for("alpha", required_bytes=1)
    except WorkspaceRoutingError as error:
        assert error.result_class == "REJECTED_QUOTA"
    else:
        raise AssertionError("quota denial admitted a runtime")
    assert builds == []


def test_runtime_router_bounds_factory_failure():
    def fail(*arguments):
        raise OSError("disk unavailable")

    router = WorkspaceRuntimeRouter(FakeAccess(), FakeStorage(), fail)
    try:
        router.application_for("alpha")
    except WorkspaceRoutingError as error:
        assert error.result_class == "REJECTED_STORAGE"
        assert "initialized" in error.detail
    else:
        raise AssertionError("runtime factory failure escaped")


def test_storage_command_adapter_uses_public_cli_json(tmp_path):
    adapter = WorkspaceStorageCommandAdapter(
        tmp_path / "run.ps1", tmp_path / "storage.json"
    )
    described = subprocess.CompletedProcess(
        [],
        0,
        '{"resultClass":"COMPLETED","value":{"workspaceId":"alpha","roots":{"state":"C:/state","artifacts":"C:/artifacts","temp":"C:/temp"}}}\n',
        "",
    )
    capacity = subprocess.CompletedProcess(
        [], 0, '{"resultClass":"ALLOWED","value":{"workspaceId":"alpha"}}\n', ""
    )

    with patch("studio.workspace_routing.subprocess.run", side_effect=[described, capacity]) as run:
        assert adapter.describe_workspace("alpha")["workspaceId"] == "alpha"
        assert adapter.check_capacity("alpha", 1)["resultClass"] == "ALLOWED"

    assert run.call_args_list[0].args[0][6] == "describe"
    assert "alpha" in run.call_args_list[0].args[0]


class GloballyBlockingAdapter:
    def __init__(self):
        self.active = 0
        self.maximum_active = 0
        self.started = threading.Event()
        self.release = threading.Event()
        self._lock = threading.Lock()

    def execute(self, node, context, on_log, cancel_event):
        with self._lock:
            self.active += 1
            self.maximum_active = max(self.maximum_active, self.active)
            self.started.set()
        assert self.release.wait(timeout=5)
        with self._lock:
            self.active -= 1
        return AdapterResult(True, {})


def test_workspace_engines_share_one_global_execution_gate(tmp_path):
    graph = GraphDefinition.from_dict(
        {
            "schemaVersion": 1,
            "graphId": "one-step",
            "revision": 1,
            "nodes": [{"id": "work", "type": "work", "config": {}}],
            "edges": [],
        }
    )
    gate = threading.Lock()
    adapter = GloballyBlockingAdapter()
    stores = [RunStore(tmp_path / name / "studio.db") for name in ("alpha", "beta")]
    engines = [WorkflowEngine(store, {"work": adapter}, execution_gate=gate) for store in stores]
    run_ids = [
        store.create_run(CreateRun(f"op-{index}", f"corr-{index}", graph, {})).value["runId"]
        for index, store in enumerate(stores)
    ]

    engines[0].start(run_ids[0])
    assert adapter.started.wait(timeout=5)
    engines[1].start(run_ids[1])
    time.sleep(0.1)

    assert adapter.maximum_active == 1
    assert stores[1].get_run(run_ids[1])["status"] == "CREATED"
    adapter.release.set()
    deadline = time.monotonic() + 5
    while any(store.get_run(run_id)["status"] != "COMPLETED" for store, run_id in zip(stores, run_ids)):
        assert time.monotonic() < deadline
        time.sleep(0.02)
    assert adapter.maximum_active == 1
