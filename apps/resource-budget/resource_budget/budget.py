"""Durable transactional byte and execution-slot reservations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from typing import Any, Callable


IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
MAX_BYTES = 2**63 - 1
MAX_SLOTS = 65_535
MAX_TTL_SECONDS = 86_400


@dataclass(frozen=True)
class BudgetResult:
    result_class: str
    value: dict[str, Any]


class BudgetError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


class ResourceBudget:
    def __init__(self, path: Path, *, clock: Callable[[], datetime] = _utc_now):
        self.path = Path(path).resolve()
        self.clock = clock
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def configure(
        self, workspace_id: str, *, byte_limit: int, execution_slots: int
    ) -> BudgetResult:
        self._identifier(workspace_id, "workspace ID")
        self._bounded(byte_limit, "byte limit", minimum=1, maximum=MAX_BYTES)
        self._bounded(
            execution_slots, "execution slots", minimum=1, maximum=MAX_SLOTS
        )
        with self._transaction() as connection:
            row = connection.execute(
                "SELECT byte_limit, execution_slots FROM workspace_budgets WHERE workspace_id=?",
                (workspace_id,),
            ).fetchone()
            value = {
                "workspaceId": workspace_id,
                "byteLimit": byte_limit,
                "executionSlots": execution_slots,
            }
            if row is not None:
                current = {
                    "workspaceId": workspace_id,
                    "byteLimit": row[0],
                    "executionSlots": row[1],
                }
                return BudgetResult(
                    "DUPLICATE_COMPLETED" if current == value else "REJECTED_CONFLICT",
                    current,
                )
            connection.execute(
                "INSERT INTO workspace_budgets(workspace_id,byte_limit,execution_slots,created_at) VALUES(?,?,?,?)",
                (workspace_id, byte_limit, execution_slots, _timestamp(self.clock())),
            )
            return BudgetResult("COMPLETED", value)

    def reserve(
        self,
        workspace_id: str,
        reservation_id: str,
        *,
        bytes_requested: int,
        slots: int,
        ttl_seconds: int,
    ) -> BudgetResult:
        self._identifier(workspace_id, "workspace ID")
        self._identifier(reservation_id, "reservation ID")
        self._bounded(bytes_requested, "requested bytes", minimum=0, maximum=MAX_BYTES)
        self._bounded(slots, "slots", minimum=0, maximum=MAX_SLOTS)
        if bytes_requested == 0 and slots == 0:
            raise BudgetError("REJECTED_MALFORMED", "reservation must request a resource")
        self._ttl(ttl_seconds)
        fingerprint = self._fingerprint(bytes_requested, slots, ttl_seconds)
        now = self.clock()
        with self._transaction() as connection:
            budget = self._required_budget(connection, workspace_id)
            self._expire(connection, workspace_id, now)
            existing = self._reservation(connection, workspace_id, reservation_id)
            if existing is not None:
                if (
                    existing["status"] == "EXPIRED"
                    and existing["fingerprint"] == fingerprint
                ):
                    reserved_bytes, reserved_slots, active = self._totals(
                        connection, workspace_id
                    )
                    if (
                        reserved_bytes + bytes_requested > budget[0]
                        or reserved_slots + slots > budget[1]
                    ):
                        return BudgetResult(
                            "REJECTED_BUDGET",
                            self._capacity_value(
                                workspace_id,
                                budget,
                                reserved_bytes,
                                reserved_slots,
                                active,
                                bytes_requested=bytes_requested,
                                slots=slots,
                            ),
                        )
                    connection.execute(
                        """UPDATE reservations
                        SET status='ACTIVE',generation=generation+1,last_renewed_from=NULL,
                            expires_at=?,updated_at=?,released_at=NULL
                        WHERE workspace_id=? AND reservation_id=?""",
                        (
                            _timestamp(now + timedelta(seconds=ttl_seconds)),
                            _timestamp(now),
                            workspace_id,
                            reservation_id,
                        ),
                    )
                    return BudgetResult(
                        "COMPLETED",
                        self._public(
                            self._reservation(connection, workspace_id, reservation_id)
                        ),
                    )
                return BudgetResult(
                    "DUPLICATE_COMPLETED"
                    if existing["status"] == "ACTIVE"
                    and existing["fingerprint"] == fingerprint
                    else "REJECTED_CONFLICT",
                    self._public(existing),
                )
            reserved_bytes, reserved_slots, active = self._totals(
                connection, workspace_id
            )
            if (
                reserved_bytes + bytes_requested > budget[0]
                or reserved_slots + slots > budget[1]
            ):
                return BudgetResult(
                    "REJECTED_BUDGET",
                    self._capacity_value(
                        workspace_id,
                        budget,
                        reserved_bytes,
                        reserved_slots,
                        active,
                        bytes_requested=bytes_requested,
                        slots=slots,
                    ),
                )
            expires_at = now + timedelta(seconds=ttl_seconds)
            connection.execute(
                """INSERT INTO reservations(
                    workspace_id,reservation_id,fingerprint,bytes_reserved,slots_reserved,
                    ttl_seconds,status,generation,expires_at,created_at,updated_at,released_at
                ) VALUES(?,?,?,?,?,?, 'ACTIVE',1,?,?,?,NULL)""",
                (
                    workspace_id,
                    reservation_id,
                    fingerprint,
                    bytes_requested,
                    slots,
                    ttl_seconds,
                    _timestamp(expires_at),
                    _timestamp(now),
                    _timestamp(now),
                ),
            )
            return BudgetResult(
                "COMPLETED",
                self._public(
                    self._reservation(connection, workspace_id, reservation_id)
                ),
            )

    def renew(
        self,
        workspace_id: str,
        reservation_id: str,
        *,
        expected_generation: int,
        ttl_seconds: int,
    ) -> BudgetResult:
        self._identifier(workspace_id, "workspace ID")
        self._identifier(reservation_id, "reservation ID")
        self._bounded(expected_generation, "expected generation", minimum=1, maximum=MAX_BYTES)
        self._ttl(ttl_seconds)
        now = self.clock()
        with self._transaction() as connection:
            self._required_budget(connection, workspace_id)
            self._expire(connection, workspace_id, now)
            row = self._required_reservation(connection, workspace_id, reservation_id)
            if row["status"] != "ACTIVE":
                raise BudgetError("REJECTED_EXPIRED", "reservation is not active")
            if (
                row["generation"] == expected_generation + 1
                and row["last_renewed_from"] == expected_generation
                and row["ttl_seconds"] == ttl_seconds
            ):
                return BudgetResult("DUPLICATE_COMPLETED", self._public(row))
            if row["generation"] != expected_generation:
                raise BudgetError("REJECTED_STALE", "reservation generation is stale")
            connection.execute(
                "UPDATE reservations SET generation=generation+1,last_renewed_from=?,ttl_seconds=?,expires_at=?,updated_at=? WHERE workspace_id=? AND reservation_id=?",
                (
                    expected_generation,
                    ttl_seconds,
                    _timestamp(now + timedelta(seconds=ttl_seconds)),
                    _timestamp(now),
                    workspace_id,
                    reservation_id,
                ),
            )
            return BudgetResult(
                "COMPLETED",
                self._public(
                    self._reservation(connection, workspace_id, reservation_id)
                ),
            )

    def release(
        self,
        workspace_id: str,
        reservation_id: str,
        *,
        expected_generation: int,
    ) -> BudgetResult:
        self._identifier(workspace_id, "workspace ID")
        self._identifier(reservation_id, "reservation ID")
        self._bounded(expected_generation, "expected generation", minimum=1, maximum=MAX_BYTES)
        now = self.clock()
        with self._transaction() as connection:
            self._required_budget(connection, workspace_id)
            self._expire(connection, workspace_id, now)
            row = self._required_reservation(connection, workspace_id, reservation_id)
            if row["status"] == "RELEASED" and row["generation"] == expected_generation:
                return BudgetResult("DUPLICATE_COMPLETED", self._public(row))
            if row["status"] != "ACTIVE":
                raise BudgetError("REJECTED_EXPIRED", "reservation is not active")
            if row["generation"] != expected_generation:
                raise BudgetError("REJECTED_STALE", "reservation generation is stale")
            connection.execute(
                "UPDATE reservations SET status='RELEASED',updated_at=?,released_at=? WHERE workspace_id=? AND reservation_id=?",
                (_timestamp(now), _timestamp(now), workspace_id, reservation_id),
            )
            return BudgetResult(
                "COMPLETED",
                self._public(
                    self._reservation(connection, workspace_id, reservation_id)
                ),
            )

    def snapshot(self, workspace_id: str) -> BudgetResult:
        self._identifier(workspace_id, "workspace ID")
        with self._transaction() as connection:
            budget = self._required_budget(connection, workspace_id)
            self._expire(connection, workspace_id, self.clock())
            reserved_bytes, reserved_slots, active = self._totals(
                connection, workspace_id
            )
            return BudgetResult(
                "COMPLETED",
                self._capacity_value(
                    workspace_id, budget, reserved_bytes, reserved_slots, active
                ),
            )

    def describe_reservation(
        self, workspace_id: str, reservation_id: str
    ) -> BudgetResult:
        self._identifier(workspace_id, "workspace ID")
        self._identifier(reservation_id, "reservation ID")
        with self._transaction() as connection:
            self._required_budget(connection, workspace_id)
            self._expire(connection, workspace_id, self.clock())
            return BudgetResult(
                "COMPLETED",
                self._public(
                    self._required_reservation(
                        connection, workspace_id, reservation_id
                    )
                ),
            )

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS workspace_budgets(
                    workspace_id TEXT PRIMARY KEY,
                    byte_limit INTEGER NOT NULL CHECK(byte_limit > 0),
                    execution_slots INTEGER NOT NULL CHECK(execution_slots > 0),
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS reservations(
                    workspace_id TEXT NOT NULL,
                    reservation_id TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    bytes_reserved INTEGER NOT NULL,
                    slots_reserved INTEGER NOT NULL,
                    ttl_seconds INTEGER NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('ACTIVE','RELEASED','EXPIRED')),
                    generation INTEGER NOT NULL,
                    last_renewed_from INTEGER,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    released_at TEXT,
                    PRIMARY KEY(workspace_id,reservation_id),
                    FOREIGN KEY(workspace_id) REFERENCES workspace_budgets(workspace_id)
                );
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=30000")
        return connection

    class _Transaction:
        def __init__(self, owner: "ResourceBudget"):
            self.connection = owner._connect()
        def __enter__(self):
            self.connection.execute("BEGIN IMMEDIATE")
            return self.connection
        def __exit__(self, kind, value, traceback):
            try:
                self.connection.execute("COMMIT" if kind is None else "ROLLBACK")
            finally:
                self.connection.close()

    def _transaction(self):
        return self._Transaction(self)

    @staticmethod
    def _required_budget(connection, workspace_id):
        row = connection.execute(
            "SELECT byte_limit,execution_slots FROM workspace_budgets WHERE workspace_id=?",
            (workspace_id,),
        ).fetchone()
        if row is None:
            raise BudgetError("REJECTED_NOT_FOUND", "workspace budget is not configured")
        return row

    @staticmethod
    def _reservation(connection, workspace_id, reservation_id):
        return connection.execute(
            "SELECT * FROM reservations WHERE workspace_id=? AND reservation_id=?",
            (workspace_id, reservation_id),
        ).fetchone()

    def _required_reservation(self, connection, workspace_id, reservation_id):
        row = self._reservation(connection, workspace_id, reservation_id)
        if row is None:
            raise BudgetError("REJECTED_NOT_FOUND", "reservation does not exist")
        return row

    @staticmethod
    def _expire(connection, workspace_id, now):
        stamp = _timestamp(now)
        connection.execute(
            "UPDATE reservations SET status='EXPIRED',updated_at=? WHERE workspace_id=? AND status='ACTIVE' AND expires_at<=?",
            (stamp, workspace_id, stamp),
        )

    @staticmethod
    def _totals(connection, workspace_id):
        row = connection.execute(
            "SELECT COALESCE(SUM(bytes_reserved),0),COALESCE(SUM(slots_reserved),0),COUNT(*) FROM reservations WHERE workspace_id=? AND status='ACTIVE'",
            (workspace_id,),
        ).fetchone()
        return int(row[0]), int(row[1]), int(row[2])

    @staticmethod
    def _capacity_value(
        workspace_id,
        budget,
        reserved_bytes,
        reserved_slots,
        active,
        *,
        bytes_requested=0,
        slots=0,
    ):
        return {
            "workspaceId": workspace_id,
            "byteLimit": int(budget[0]),
            "executionSlots": int(budget[1]),
            "reservedBytes": reserved_bytes,
            "reservedSlots": reserved_slots,
            "availableBytes": int(budget[0]) - reserved_bytes,
            "availableSlots": int(budget[1]) - reserved_slots,
            "activeReservations": active,
            "requestedBytes": bytes_requested,
            "requestedSlots": slots,
        }

    @staticmethod
    def _public(row):
        return {
            "workspaceId": row["workspace_id"],
            "reservationId": row["reservation_id"],
            "bytes": row["bytes_reserved"],
            "slots": row["slots_reserved"],
            "ttlSeconds": row["ttl_seconds"],
            "status": row["status"],
            "generation": row["generation"],
            "expiresAt": row["expires_at"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
            "releasedAt": row["released_at"],
        }

    @staticmethod
    def _fingerprint(bytes_requested, slots, ttl_seconds):
        value = json.dumps(
            {"bytes": bytes_requested, "slots": slots, "ttlSeconds": ttl_seconds},
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _identifier(value, label):
        if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
            raise BudgetError("REJECTED_MALFORMED", f"invalid {label}")

    @staticmethod
    def _bounded(value, label, *, minimum, maximum):
        if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
            raise BudgetError("REJECTED_MALFORMED", f"invalid {label}")

    def _ttl(self, value):
        self._bounded(
            value, "TTL seconds", minimum=1, maximum=MAX_TTL_SECONDS
        )
