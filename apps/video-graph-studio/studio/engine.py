"""Checkpointed, strictly serial workflow process manager."""

from __future__ import annotations

import threading
from typing import Any

from .adapters import AdapterResult
from .contracts import GraphDefinition, GraphNode
from .graph import validate_graph
from .store import CommandResult, RunStore, TERMINAL_STATES


class WorkflowEngine:
    def __init__(self, store: RunStore, adapters: dict[str, Any]):
        self.store = store
        self.adapters = adapters
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._active_run_id: str | None = None
        self._cancel_event = threading.Event()

    @property
    def active_run_id(self) -> str | None:
        with self._lock:
            return self._active_run_id

    def start(self, run_id: str) -> CommandResult:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return CommandResult("REJECTED_CONFLICT", {"activeRunId": self._active_run_id})
            try:
                run = self.store.get_run(run_id)
            except KeyError:
                return CommandResult("REJECTED_NOT_FOUND", {"runId": run_id})
            if run["status"] in TERMINAL_STATES:
                return CommandResult("DUPLICATE_COMPLETED", run)
            transitioned = self.store.transition(
                run_id, expected_version=run["version"], target="RUNNING"
            )
            if transitioned.result_class not in {"COMPLETED", "DUPLICATE_COMPLETED"}:
                return transitioned
            self._cancel_event = threading.Event()
            self._active_run_id = run_id
            self._thread = threading.Thread(
                target=self._execute,
                args=(run_id,),
                name=f"video-graph-{run_id}",
                daemon=True,
            )
            self._thread.start()
            return CommandResult("COMPLETED", self.store.get_run(run_id))

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
            if run["status"] == "QUEUED":
                return self.store.transition(
                    run_id, expected_version=run["version"], target="CANCELLED"
                )
            if run["status"] == "CANCEL_REQUESTED":
                self._cancel_event.set()
                return CommandResult("DUPLICATE_COMPLETED", run)
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

    def _execute(self, run_id: str) -> None:
        try:
            run = self.store.get_run(run_id)
            graph = GraphDefinition.from_dict(run["graph"])
            nodes: dict[str, GraphNode] = {node.id: node for node in graph.nodes}
            completed = {
                step["nodeId"] for step in run["steps"] if step["status"] == "COMPLETED"
            }
            for node_id in validate_graph(graph):
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
                    {"runId": run_id, "parameters": run["parameters"]},
                    lambda line, rid=run_id: self.store.append_log(rid, line),
                    self._cancel_event,
                )
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
        finally:
            with self._lock:
                self._active_run_id = None

    def _fail(self, run_id: str, node_id: str, error: str) -> None:
        self.store.fail_step(run_id, node_id, error)
        self.store.append_log(run_id, f"[{node_id}] failed: {error}")
        self._transition_latest(run_id, "FAILED")

    def _finish_cancel(self, run_id: str) -> None:
        self._transition_latest(run_id, "CANCELLED")

    def _transition_latest(self, run_id: str, target: str) -> CommandResult:
        run = self.store.get_run(run_id)
        return self.store.transition(run_id, expected_version=run["version"], target=target)

