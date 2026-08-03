"""SQLite owners for workflow runs, steps, operations and logs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import threading
from typing import Any
import uuid

from .contracts import GraphDefinition, canonical_json
from .graph import validate_graph


TERMINAL_STATES = frozenset({"COMPLETED", "FAILED", "CANCELLED"})
ALLOWED_TRANSITIONS = {
    "CREATED": frozenset({"RUNNING", "CANCELLED"}),
    # QUEUED is retained as a legacy run state for databases created before
    # the durable Start Queue became its own state owner.
    "QUEUED": frozenset({"RUNNING", "CANCELLED"}),
    "RUNNING": frozenset({"COMPLETED", "FAILED", "CANCEL_REQUESTED", "INTERRUPTED"}),
    "CANCEL_REQUESTED": frozenset({"CANCELLED", "FAILED"}),
    "INTERRUPTED": frozenset({"RUNNING", "FAILED", "CANCELLED"}),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class CommandResult:
    result_class: str
    value: dict[str, Any]


@dataclass(frozen=True)
class CreateRun:
    operation_id: str
    correlation_id: str
    graph: GraphDefinition
    parameters: dict[str, Any]

    @property
    def fingerprint(self) -> str:
        payload = {
            "contractId": "CMD-RUN-CREATE",
            "contractVersion": "1.0",
            "correlationId": self.correlation_id,
            "graphFingerprint": self.graph.fingerprint,
            "parameters": self.parameters,
        }
        return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


class RunStore:
    def __init__(self, database: Path):
        self.database = Path(database)
        self.database.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    correlation_id TEXT NOT NULL,
                    graph_json TEXT NOT NULL,
                    graph_fingerprint TEXT NOT NULL,
                    parameters_json TEXT NOT NULL,
                    input_fingerprint TEXT NOT NULL,
                    status TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    terminal_result_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS operations (
                    operation_id TEXT PRIMARY KEY,
                    fingerprint TEXT NOT NULL,
                    run_id TEXT NOT NULL REFERENCES runs(run_id)
                );
                CREATE TABLE IF NOT EXISTS steps (
                    run_id TEXT NOT NULL REFERENCES runs(run_id),
                    node_id TEXT NOT NULL,
                    ordinal INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    child_operation_id TEXT NOT NULL,
                    result_json TEXT,
                    error TEXT,
                    PRIMARY KEY (run_id, node_id)
                );
                CREATE TABLE IF NOT EXISTS run_logs (
                    run_id TEXT NOT NULL REFERENCES runs(run_id),
                    sequence INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (run_id, sequence)
                );
                CREATE TABLE IF NOT EXISTS start_queue (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL UNIQUE REFERENCES runs(run_id),
                    status TEXT NOT NULL,
                    requested_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )

    def create_run(self, command: CreateRun) -> CommandResult:
        order = validate_graph(command.graph)
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT fingerprint, run_id FROM operations WHERE operation_id = ?",
                (command.operation_id,),
            ).fetchone()
            if existing:
                if existing["fingerprint"] != command.fingerprint:
                    connection.rollback()
                    return CommandResult("REJECTED_CONFLICT", {"operationId": command.operation_id})
                run = self._run_row(connection, existing["run_id"])
                connection.commit()
                return CommandResult("DUPLICATE_COMPLETED", run)

            run_id = str(uuid.uuid4())
            created_at = _now()
            connection.execute(
                """INSERT INTO runs
                (run_id, correlation_id, graph_json, graph_fingerprint, parameters_json,
                 input_fingerprint, status, version, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 'CREATED', 0, ?, ?)""",
                (
                    run_id,
                    command.correlation_id,
                    canonical_json(command.graph.to_dict()),
                    command.graph.fingerprint,
                    canonical_json(command.parameters),
                    command.fingerprint,
                    created_at,
                    created_at,
                ),
            )
            connection.execute(
                "INSERT INTO operations (operation_id, fingerprint, run_id) VALUES (?, ?, ?)",
                (command.operation_id, command.fingerprint, run_id),
            )
            for ordinal, node_id in enumerate(order):
                connection.execute(
                    """INSERT INTO steps
                    (run_id, node_id, ordinal, status, version, child_operation_id)
                    VALUES (?, ?, ?, 'PENDING', 0, ?)""",
                    (run_id, node_id, ordinal, f"{run_id}:step:{node_id}"),
                )
            result = self._run_row(connection, run_id)
            connection.commit()
            return CommandResult("COMPLETED", result)

    def transition(self, run_id: str, *, expected_version: int, target: str) -> CommandResult:
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
            if row is None:
                connection.rollback()
                return CommandResult("REJECTED_NOT_FOUND", {"runId": run_id})
            current = row["status"]
            if current == target and current in TERMINAL_STATES:
                result = self._run_row(connection, run_id)
                connection.commit()
                return CommandResult("DUPLICATE_COMPLETED", result)
            if row["version"] != expected_version or target not in ALLOWED_TRANSITIONS.get(current, ()):
                connection.rollback()
                return CommandResult(
                    "REJECTED_CONFLICT",
                    {"runId": run_id, "status": current, "version": row["version"]},
                )
            next_version = expected_version + 1
            terminal = canonical_json({"runId": run_id, "status": target, "version": next_version}) if target in TERMINAL_STATES else None
            connection.execute(
                """UPDATE runs SET status = ?, version = ?, terminal_result_json = ?, updated_at = ?
                WHERE run_id = ? AND version = ?""",
                (target, next_version, terminal, _now(), run_id, expected_version),
            )
            result = self._run_row(connection, run_id)
            connection.commit()
            return CommandResult("COMPLETED", result)

    def append_log(self, run_id: str, message: str) -> int:
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if connection.execute("SELECT 1 FROM runs WHERE run_id = ?", (run_id,)).fetchone() is None:
                raise KeyError(run_id)
            sequence = connection.execute(
                "SELECT COALESCE(MAX(sequence), 0) + 1 FROM run_logs WHERE run_id = ?",
                (run_id,),
            ).fetchone()[0]
            connection.execute(
                "INSERT INTO run_logs (run_id, sequence, message, created_at) VALUES (?, ?, ?, ?)",
                (run_id, sequence, message, _now()),
            )
            connection.commit()
            return int(sequence)

    def start_step(self, run_id: str, node_id: str) -> CommandResult:
        return self._change_step(run_id, node_id, {"PENDING", "INTERRUPTED"}, "RUNNING")

    def complete_step(self, run_id: str, node_id: str, result: dict[str, Any]) -> CommandResult:
        return self._change_step(run_id, node_id, {"RUNNING"}, "COMPLETED", result=result)

    def fail_step(self, run_id: str, node_id: str, error: str) -> CommandResult:
        return self._change_step(run_id, node_id, {"RUNNING"}, "FAILED", error=error)

    def cancel_step(self, run_id: str, node_id: str) -> CommandResult:
        return self._change_step(run_id, node_id, {"RUNNING"}, "CANCELLED")

    def interrupt_active(self) -> int:
        """Fence process handles lost during a previous server generation."""
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            steps = connection.execute(
                "UPDATE steps SET status = 'INTERRUPTED', version = version + 1 WHERE status = 'RUNNING'"
            ).rowcount
            connection.execute(
                """UPDATE runs SET status = 'INTERRUPTED', version = version + 1, updated_at = ?
                WHERE status IN ('RUNNING', 'CANCEL_REQUESTED')""",
                (_now(),),
            )
            connection.commit()
            return int(steps)

    def enqueue_run(self, run_id: str) -> CommandResult:
        """Durably request execution without claiming a worker."""
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            run = connection.execute(
                "SELECT status FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone()
            if run is None:
                connection.rollback()
                return CommandResult("REJECTED_NOT_FOUND", {"runId": run_id})
            if run["status"] in TERMINAL_STATES:
                result = self._run_row(connection, run_id)
                connection.commit()
                return CommandResult("DUPLICATE_COMPLETED", result)
            if run["status"] not in {"CREATED", "QUEUED", "INTERRUPTED", "RUNNING"}:
                connection.rollback()
                return CommandResult(
                    "REJECTED_CONFLICT", {"runId": run_id, "status": run["status"]}
                )
            existing = connection.execute(
                "SELECT sequence, status FROM start_queue WHERE run_id = ?", (run_id,)
            ).fetchone()
            if existing is not None:
                connection.commit()
                return CommandResult(
                    "DUPLICATE_COMPLETED",
                    {
                        "runId": run_id,
                        "queueSequence": existing["sequence"],
                        "queueStatus": existing["status"],
                    },
                )
            requested_at = _now()
            cursor = connection.execute(
                """INSERT INTO start_queue (run_id, status, requested_at, updated_at)
                VALUES (?, 'QUEUED', ?, ?)""",
                (run_id, requested_at, requested_at),
            )
            connection.commit()
            return CommandResult(
                "COMPLETED",
                {
                    "runId": run_id,
                    "queueSequence": int(cursor.lastrowid),
                    "queueStatus": "QUEUED",
                },
            )

    def retry_failed(self, run_id: str) -> CommandResult:
        """Reset only failed owners and durably enqueue the same run for continuation."""
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            run = connection.execute(
                "SELECT status, version FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone()
            if run is None:
                connection.rollback()
                return CommandResult("REJECTED_NOT_FOUND", {"runId": run_id})
            queue = connection.execute(
                "SELECT sequence, status FROM start_queue WHERE run_id = ?", (run_id,)
            ).fetchone()
            if run["status"] == "INTERRUPTED" and queue is not None and queue["status"] in {"QUEUED", "RUNNING"}:
                value = self._run_row(connection, run_id)
                connection.commit()
                return CommandResult("DUPLICATE_COMPLETED", value)
            if run["status"] != "FAILED":
                connection.rollback()
                return CommandResult("REJECTED_CONFLICT", {"runId": run_id, "status": run["status"]})
            reset_count = connection.execute(
                """UPDATE steps SET status = 'PENDING', version = version + 1,
                   result_json = NULL, error = NULL WHERE run_id = ? AND status = 'FAILED'""",
                (run_id,),
            ).rowcount
            if reset_count < 1:
                connection.rollback()
                return CommandResult("REJECTED_CONFLICT", {"runId": run_id, "detail": "failed step missing"})
            now = _now()
            connection.execute(
                """UPDATE runs SET status = 'INTERRUPTED', version = version + 1,
                   terminal_result_json = NULL, updated_at = ? WHERE run_id = ?""",
                (now, run_id),
            )
            sequence = connection.execute(
                "SELECT COALESCE(MAX(sequence), 0) + 1 FROM run_logs WHERE run_id = ?", (run_id,)
            ).fetchone()[0]
            connection.execute(
                "INSERT INTO run_logs (run_id, sequence, message, created_at) VALUES (?, ?, ?, ?)",
                (run_id, sequence, f"retry requested: reset {reset_count} failed step(s)", now),
            )
            if queue is None:
                connection.execute(
                    """INSERT INTO start_queue (run_id, status, requested_at, updated_at)
                    VALUES (?, 'QUEUED', ?, ?)""",
                    (run_id, now, now),
                )
            else:
                connection.execute(
                    """UPDATE start_queue SET status = 'QUEUED', requested_at = ?, updated_at = ?
                    WHERE run_id = ?""",
                    (now, now, run_id),
                )
            value = self._run_row(connection, run_id)
            connection.commit()
            return CommandResult("COMPLETED", value)

    def claim_next_run(self) -> str | None:
        """Claim the oldest runnable start request for the single worker."""
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            while True:
                row = connection.execute(
                    """SELECT q.sequence, q.run_id, r.status AS run_status
                    FROM start_queue q JOIN runs r ON r.run_id = q.run_id
                    WHERE q.status = 'QUEUED'
                    ORDER BY q.sequence LIMIT 1"""
                ).fetchone()
                if row is None:
                    connection.commit()
                    return None
                if row["run_status"] in TERMINAL_STATES:
                    connection.execute(
                        "UPDATE start_queue SET status = 'COMPLETED', updated_at = ? WHERE sequence = ?",
                        (_now(), row["sequence"]),
                    )
                    continue
                if row["run_status"] not in {"CREATED", "QUEUED", "INTERRUPTED"}:
                    connection.commit()
                    return None
                connection.execute(
                    "UPDATE start_queue SET status = 'RUNNING', updated_at = ? WHERE sequence = ?",
                    (_now(), row["sequence"]),
                )
                connection.commit()
                return str(row["run_id"])

    def finish_queue_entry(self, run_id: str) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """UPDATE start_queue SET status = 'COMPLETED', updated_at = ?
                WHERE run_id = ? AND status IN ('QUEUED', 'RUNNING')""",
                (_now(), run_id),
            )

    def requeue_claim(self, run_id: str) -> None:
        """Return one live claim to its original FIFO position."""
        with self._lock, self._connect() as connection:
            connection.execute(
                """UPDATE start_queue SET status = 'QUEUED', updated_at = ?
                WHERE run_id = ? AND status = 'RUNNING'""",
                (_now(), run_id),
            )

    def recover_queue(self) -> int:
        """Return claims abandoned by a previous server generation to FIFO order."""
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                """UPDATE start_queue SET status = 'QUEUED', updated_at = ?
                WHERE status = 'RUNNING'""",
                (_now(),),
            )
            return int(cursor.rowcount)

    def queue_snapshot(self) -> dict[str, Any]:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT sequence, run_id, status, requested_at, updated_at
                FROM start_queue WHERE status IN ('QUEUED', 'RUNNING')
                ORDER BY sequence"""
            ).fetchall()
            entries = [
                {
                    "sequence": row["sequence"],
                    "runId": row["run_id"],
                    "status": row["status"],
                    "requestedAt": row["requested_at"],
                    "updatedAt": row["updated_at"],
                }
                for row in rows
            ]
            return {
                "activeRunId": next(
                    (entry["runId"] for entry in entries if entry["status"] == "RUNNING"),
                    None,
                ),
                "queuedRuns": sum(entry["status"] == "QUEUED" for entry in entries),
                "entries": entries,
            }

    def _change_step(
        self,
        run_id: str,
        node_id: str,
        allowed: set[str],
        target: str,
        *,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> CommandResult:
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT status, version, result_json, error FROM steps WHERE run_id = ? AND node_id = ?",
                (run_id, node_id),
            ).fetchone()
            if row is None:
                connection.rollback()
                return CommandResult("REJECTED_NOT_FOUND", {"runId": run_id, "nodeId": node_id})
            if row["status"] == target and target in {"COMPLETED", "FAILED", "CANCELLED"}:
                connection.commit()
                return CommandResult(
                    "DUPLICATE_COMPLETED",
                    {"runId": run_id, "nodeId": node_id, "status": target},
                )
            if row["status"] not in allowed:
                connection.rollback()
                return CommandResult(
                    "REJECTED_CONFLICT",
                    {"runId": run_id, "nodeId": node_id, "status": row["status"]},
                )
            connection.execute(
                """UPDATE steps SET status = ?, version = version + 1, result_json = ?, error = ?
                WHERE run_id = ? AND node_id = ? AND version = ?""",
                (
                    target,
                    canonical_json(result) if result is not None else None,
                    error,
                    run_id,
                    node_id,
                    row["version"],
                ),
            )
            connection.commit()
            return CommandResult(
                "COMPLETED", {"runId": run_id, "nodeId": node_id, "status": target}
            )

    def get_run(self, run_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            if connection.execute("SELECT 1 FROM runs WHERE run_id = ?", (run_id,)).fetchone() is None:
                raise KeyError(run_id)
            return self._run_row(connection, run_id)

    def list_runs(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            identifiers = connection.execute(
                "SELECT run_id FROM runs ORDER BY created_at DESC"
            ).fetchall()
            return [self._run_row(connection, row["run_id"]) for row in identifiers]

    def _run_row(self, connection: sqlite3.Connection, run_id: str) -> dict[str, Any]:
        row = connection.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(run_id)
        steps = connection.execute(
            "SELECT * FROM steps WHERE run_id = ? ORDER BY ordinal", (run_id,)
        ).fetchall()
        logs = connection.execute(
            "SELECT sequence, message, created_at FROM run_logs WHERE run_id = ? ORDER BY sequence",
            (run_id,),
        ).fetchall()
        return {
            "runId": row["run_id"],
            "correlationId": row["correlation_id"],
            "graph": json.loads(row["graph_json"]),
            "graphFingerprint": row["graph_fingerprint"],
            "parameters": json.loads(row["parameters_json"]),
            "status": row["status"],
            "version": row["version"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
            "steps": [
                {
                    "nodeId": step["node_id"],
                    "ordinal": step["ordinal"],
                    "status": step["status"],
                    "version": step["version"],
                    "childOperationId": step["child_operation_id"],
                    "result": json.loads(step["result_json"]) if step["result_json"] else None,
                    "error": step["error"],
                }
                for step in steps
            ],
            "logs": [dict(log) for log in logs],
        }
