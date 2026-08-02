from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys


APP = Path(__file__).resolve().parents[2] / "apps" / "resource-budget"
sys.path.insert(0, str(APP))

from resource_budget.budget import BudgetError, ResourceBudget


class Clock:
    def __init__(self):
        self.value = datetime(2026, 8, 2, tzinfo=timezone.utc)

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += timedelta(seconds=seconds)


def test_configure_replays_and_rejects_changed_limits(tmp_path):
    budget = ResourceBudget(tmp_path / "budget.db", clock=Clock())

    first = budget.configure("alpha", byte_limit=1_000, execution_slots=2)
    replay = budget.configure("alpha", byte_limit=1_000, execution_slots=2)
    conflict = budget.configure("alpha", byte_limit=2_000, execution_slots=2)

    assert first.result_class == "COMPLETED"
    assert replay.result_class == "DUPLICATE_COMPLETED"
    assert conflict.result_class == "REJECTED_CONFLICT"


def test_reserve_never_oversubscribes_bytes_or_slots(tmp_path):
    budget = ResourceBudget(tmp_path / "budget.db", clock=Clock())
    budget.configure("alpha", byte_limit=100, execution_slots=1)

    accepted = budget.reserve("alpha", "run-one", bytes_requested=60, slots=1, ttl_seconds=30)
    denied = budget.reserve("alpha", "run-two", bytes_requested=40, slots=1, ttl_seconds=30)
    snapshot = budget.snapshot("alpha")

    assert accepted.result_class == "COMPLETED"
    assert denied.result_class == "REJECTED_BUDGET"
    assert snapshot.value["reservedBytes"] == 60
    assert snapshot.value["reservedSlots"] == 1
    assert snapshot.value["activeReservations"] == 1


def test_reserve_exact_replay_is_duplicate_and_changed_input_conflicts(tmp_path):
    budget = ResourceBudget(tmp_path / "budget.db", clock=Clock())
    budget.configure("alpha", byte_limit=100, execution_slots=2)
    first = budget.reserve("alpha", "run-one", bytes_requested=40, slots=1, ttl_seconds=30)

    replay = budget.reserve("alpha", "run-one", bytes_requested=40, slots=1, ttl_seconds=30)
    conflict = budget.reserve("alpha", "run-one", bytes_requested=41, slots=1, ttl_seconds=30)

    assert replay.result_class == "DUPLICATE_COMPLETED"
    assert replay.value["generation"] == first.value["generation"] == 1
    assert conflict.result_class == "REJECTED_CONFLICT"


def test_renew_and_release_require_current_generation_and_are_idempotent(tmp_path):
    clock = Clock(); budget = ResourceBudget(tmp_path / "budget.db", clock=clock)
    budget.configure("alpha", byte_limit=100, execution_slots=1)
    budget.reserve("alpha", "run-one", bytes_requested=40, slots=1, ttl_seconds=30)

    renewed = budget.renew("alpha", "run-one", expected_generation=1, ttl_seconds=60)
    renewed_replay = budget.renew("alpha", "run-one", expected_generation=1, ttl_seconds=60)
    try:
        budget.release("alpha", "run-one", expected_generation=1)
    except BudgetError as error:
        assert error.code == "REJECTED_STALE"
    else:
        raise AssertionError("stale release accepted")
    released = budget.release("alpha", "run-one", expected_generation=2)
    replay = budget.release("alpha", "run-one", expected_generation=2)

    assert renewed.value["generation"] == 2
    assert renewed_replay.result_class == "DUPLICATE_COMPLETED"
    assert renewed_replay.value["generation"] == 2
    assert released.result_class == "COMPLETED"
    assert replay.result_class == "DUPLICATE_COMPLETED"
    assert budget.snapshot("alpha").value["availableBytes"] == 100


def test_expired_reservation_is_reclaimed_transactionally(tmp_path):
    clock = Clock(); budget = ResourceBudget(tmp_path / "budget.db", clock=clock)
    budget.configure("alpha", byte_limit=100, execution_slots=1)
    budget.reserve("alpha", "run-one", bytes_requested=100, slots=1, ttl_seconds=5)
    clock.advance(6)

    second = budget.reserve("alpha", "run-two", bytes_requested=100, slots=1, ttl_seconds=5)
    first = budget.describe_reservation("alpha", "run-one")

    assert second.result_class == "COMPLETED"
    assert first.value["status"] == "EXPIRED"


def test_expired_stable_reservation_can_reactivate_without_weakening_conflicts(tmp_path):
    clock = Clock(); budget = ResourceBudget(tmp_path / "budget.db", clock=clock)
    budget.configure("alpha", byte_limit=100, execution_slots=1)
    first = budget.reserve("alpha", "studio-run-one", bytes_requested=100, slots=1, ttl_seconds=5)
    clock.advance(6)

    reactivated = budget.reserve(
        "alpha", "studio-run-one", bytes_requested=100, slots=1, ttl_seconds=5
    )
    changed = budget.reserve(
        "alpha", "studio-run-one", bytes_requested=99, slots=1, ttl_seconds=5
    )

    assert first.value["generation"] == 1
    assert reactivated.result_class == "COMPLETED"
    assert reactivated.value["status"] == "ACTIVE"
    assert reactivated.value["generation"] == 2
    assert changed.result_class == "REJECTED_CONFLICT"
