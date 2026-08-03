"""Checkpointed workflow process manager with a durable, strictly serial queue."""

from __future__ import annotations

import threading
import time
from typing import Any

from .adapters import AdapterResult
from .contracts import GraphDefinition, GraphNode
from .graph import validate_graph
from .store import CommandResult, RunStore, TERMINAL_STATES
from .resource_leases import ResourceLeaseUnavailable


class WorkflowEngine:
    def __init__(
        self,
        store: RunStore,
        adapters: dict[str, Any],
        *,
        execution_gate: Any | None = None,
        lease_coordinator: Any | None = None,
        resource_retry_seconds: float = 1.0,
    ):
        self.store = store
        self.adapters = adapters
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._draining = False
        self._active_run_id: str | None = None
        self._cancel_event = threading.Event()
        self._shutdown_event = threading.Event()
        self._execution_gate = execution_gate or threading.Lock()
        self._lease_coordinator = lease_coordinator
        self._resource_retry_seconds = resource_retry_seconds
        self._resource_attempts: dict[str, int] = {}
        self._lease_failure: str | None = None

    @property
    def active_run_id(self) -> str | None:
        with self._lock:
            return self._active_run_id

    def start(self, run_id: str) -> CommandResult:
        """Idempotently enqueue a run and ensure one serial drain worker exists."""
        if self._shutdown_event.is_set():
            return CommandResult("REJECTED_CONFLICT", {"detail": "engine is stopping"})
        queued = self.store.enqueue_run(run_id)
        if queued.result_class not in {"COMPLETED", "DUPLICATE_COMPLETED"}:
            return queued
        run = self.store.get_run(run_id)
        if run["status"] in TERMINAL_STATES:
            return CommandResult("DUPLICATE_COMPLETED", run)
        self._ensure_drain()
        return queued

    def resume_pending(self) -> None:
        """Resume durable start requests recovered during server startup."""
        if self.store.queue_snapshot()["queuedRuns"]:
            self._ensure_drain()

    def retry(self, run_id: str) -> CommandResult:
        """Continue a failed run while preserving every committed owner fact."""
        if self._shutdown_event.is_set():
            return CommandResult("REJECTED_CONFLICT", {"detail": "engine is stopping"})
        result = self.store.retry_failed(run_id)
        if result.result_class in {"COMPLETED", "DUPLICATE_COMPLETED"}:
            self._ensure_drain()
        return result

    def cancel(self, run_id: str) -> CommandResult:
        with self._lock:
            try:
                run = self.store.get_run(run_id)
            except KeyError:
                return CommandResult("REJECTED_NOT_FOUND", {"runId": run_id})
            if run["status"] == "CANCELLED":
                return CommandResult("DUPLICATE_COMPLETED", run)
            if run["status"] in {"COMPLETED", "FAILED"}:
                return CommandResult("REJECTED_CONFLICT", run)
            if run["status"] in {"CREATED", "QUEUED", "INTERRUPTED"}:
                result = self.store.transition(
                    run_id, expected_version=run["version"], target="CANCELLED"
                )
                if result.result_class == "COMPLETED":
                    self.store.finish_queue_entry(run_id)
                return result
            if run["status"] == "CANCEL_REQUESTED":
                if run_id == self._active_run_id:
                    self._cancel_event.set()
                return CommandResult("DUPLICATE_COMPLETED", run)
            if run_id != self._active_run_id:
                return CommandResult("REJECTED_CONFLICT", run)
            result = self.store.transition(
                run_id, expected_version=run["version"], target="CANCEL_REQUESTED"
            )
            if result.result_class == "COMPLETED":
                self._cancel_event.set()
                for adapter in self.adapters.values():
                    stop = getattr(adapter, "stop", None)
                    if callable(stop):
                        stop()
            return result

    def shutdown(self) -> None:
        self._shutdown_event.set()
        active = self.active_run_id
        if active:
            self.cancel(active)

    def wait_idle(self, timeout: float = 10) -> bool:
        """Wait for the current drain generation without taking lifecycle ownership."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self._lock:
                thread = self._thread
                draining = self._draining
            if not draining or thread is None:
                return True
            thread.join(timeout=min(0.1, max(0.0, deadline - time.monotonic())))
        return False

    def _ensure_drain(self) -> None:
        with self._lock:
            if self._draining:
                return
            self._draining = True
            self._thread = threading.Thread(
                target=self._drain,
                name="video-graph-serial-queue",
                daemon=True,
            )
            self._thread.start()

    def _drain(self) -> None:
        while True:
            with self._execution_gate:
                if self._shutdown_event.is_set():
                    with self._lock:
                        self._draining = False
                        self._active_run_id = None
                    return
                run_id = self.store.claim_next_run()
                if run_id is None:
                    with self._lock:
                        if self.store.queue_snapshot()["queuedRuns"]:
                            continue
                        self._draining = False
                        self._active_run_id = None
                        return
                with self._lock:
                    self._active_run_id = run_id
                    self._cancel_event = threading.Event()
                    self._lease_failure = None
                lease = None
                requeue = False
                retry_delay = self._resource_retry_seconds
                try:
                    if self._lease_coordinator is not None:
                        try:
                            lease = self._lease_coordinator.acquire(run_id)
                        except ResourceLeaseUnavailable as error:
                            attempts = self._resource_attempts.get(run_id, 0) + 1
                            self._resource_attempts[run_id] = attempts
                            retry_delay = min(
                                self._resource_retry_seconds * (2 ** min(attempts - 1, 5)),
                                30.0,
                            )
                            if attempts & (attempts - 1) == 0:
                                self.store.append_log(
                                    run_id,
                                    f"resource wait: {error.result_class}: {error.detail}; retry {attempts}",
                                )
                            self.store.requeue_claim(run_id)
                            requeue = True
                        if not requeue:
                            self._resource_attempts.pop(run_id, None)
                            lease.start(self._on_lease_failure)
                    if not requeue:
                        self._execute_claimed(run_id)
                finally:
                    if lease is not None:
                        try:
                            lease.close()
                        except ResourceLeaseUnavailable as error:
                            self.store.append_log(
                                run_id,
                                f"resource release pending reconciliation: {error.result_class}",
                            )
                    if not requeue:
                        self.store.finish_queue_entry(run_id)
                    with self._lock:
                        self._active_run_id = None
            if requeue:
                self._shutdown_event.wait(retry_delay)

    def _execute_claimed(self, run_id: str) -> None:
        run = self.store.get_run(run_id)
        if run["status"] in TERMINAL_STATES:
            return
        transitioned = self.store.transition(
            run_id, expected_version=run["version"], target="RUNNING"
        )
        if transitioned.result_class not in {"COMPLETED", "DUPLICATE_COMPLETED"}:
            self.store.append_log(run_id, "queue claim could not enter RUNNING")
            return
        self._execute(run_id)

    def _execute(self, run_id: str) -> None:
        try:
            run = self.store.get_run(run_id)
            graph = GraphDefinition.from_dict(run["graph"])
            nodes: dict[str, GraphNode] = {node.id: node for node in graph.nodes}
            completed = {
                step["nodeId"] for step in run["steps"] if step["status"] == "COMPLETED"
            }
            for node_id in validate_graph(graph):
                if self._lease_failure is not None:
                    self.store.append_log(run_id, f"resource lease lost: {self._lease_failure}")
                    self._transition_latest(run_id, "FAILED")
                    return
                if node_id in completed:
                    continue
                if self._cancel_event.is_set():
                    self._finish_cancel(run_id)
                    return
                node = nodes[node_id]
                adapter = self.adapters.get(node.type)
                if adapter is None:
                    self._fail(run_id, node_id, f"no adapter registered for {node.type}")
                    return
                started = self.store.start_step(run_id, node_id)
                if started.result_class != "COMPLETED":
                    self._fail(run_id, node_id, "step could not enter RUNNING")
                    return
                self.store.append_log(run_id, f"[{node_id}] started")
                result: AdapterResult = adapter.execute(
                    node,
                    {
                        "runId": run_id,
                        "parameters": run["parameters"],
                        "steps": self.store.get_run(run_id)["steps"],
                    },
                    lambda line, rid=run_id: self.store.append_log(rid, line),
                    self._cancel_event,
                )
                if self._lease_failure is not None:
                    self.store.fail_step(run_id, node_id, self._lease_failure)
                    self.store.append_log(run_id, f"resource lease lost: {self._lease_failure}")
                    self._transition_latest(run_id, "FAILED")
                    return
                if self._cancel_event.is_set():
                    self.store.cancel_step(run_id, node_id)
                    self._finish_cancel(run_id)
                    return
                if not result.completed:
                    self.store.fail_step(run_id, node_id, result.error or "adapter failed")
                    self.store.append_log(run_id, f"[{node_id}] failed: {result.error}")
                    self._transition_latest(run_id, "FAILED")
                    return
                self.store.complete_step(run_id, node_id, result.details)
                self.store.append_log(run_id, f"[{node_id}] completed")
            self._transition_latest(run_id, "COMPLETED")
        except Exception as error:
            self.store.append_log(run_id, f"engine failure: {type(error).__name__}: {error}")
            self._transition_latest(run_id, "FAILED")

    def _fail(self, run_id: str, node_id: str, error: str) -> None:
        self.store.fail_step(run_id, node_id, error)
        self.store.append_log(run_id, f"[{node_id}] failed: {error}")
        self._transition_latest(run_id, "FAILED")

    def _finish_cancel(self, run_id: str) -> None:
        self._transition_latest(run_id, "CANCELLED")

    def _transition_latest(self, run_id: str, target: str) -> CommandResult:
        run = self.store.get_run(run_id)
        return self.store.transition(run_id, expected_version=run["version"], target=target)

    def _on_lease_failure(self, detail: str) -> None:
        with self._lock:
            self._lease_failure = detail
            self._cancel_event.set()
            for adapter in self.adapters.values():
                stop = getattr(adapter, "stop", None)
                if callable(stop):
                    stop()
