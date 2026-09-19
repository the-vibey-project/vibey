# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

import json
from datetime import UTC, datetime
from unittest.mock import patch
from uuid import uuid4

import pytest

from vibey.domain.interfaces.ledger_tier_interface import LedgerTierManagerInterface
from vibey.domain.ledger import EventKind, LedgerEvent, Provenance, digest_event
from vibey.domain.ledger_record import LEDGER_RECORDS
from vibey.domain.ledger_tier import TierConfig
from vibey.domain.phase import Phase
from vibey.infrastructure.ledger.compression import DEFAULT_CODEC
from vibey.infrastructure.ledger.tier_manager import TierManager
from vibey.infrastructure.ledger.tier_store import InMemoryLedgerTierStore


def test_tier_manager_satisfies_its_interface() -> None:
    project_id = uuid4()
    store = InMemoryLedgerTierStore()
    manager = TierManager(store)

    assert isinstance(manager, LedgerTierManagerInterface)
    assert manager.reconcile_tiers(project_id, TierConfig(10, 100)) == (0, 0)
    assert manager.get_event(project_id, 1) is None
    assert manager.get_range(project_id, 1, 10) == ()


def test_reconciliation_verifies_compressed_copies_before_removing_raw_events() -> None:
    project_id = uuid4()
    store = InMemoryLedgerTierStore()
    events = tuple(
        LedgerEvent(
            event_id=uuid4(),
            project_id=project_id,
            cycle=1,
            phase=Phase.BUILD,
            seq=seq,
            kind=EventKind.TURN_COMPLETED,
            engine_id=None,
            job_id=None,
            causation_id=None,
            correlation_id=project_id,
            provenance=Provenance.AGENT,
            produced_at=datetime(2026, 1, 1, tzinfo=UTC),
            payload={"seq": seq},
            digest=digest_event({"seq": seq}),
        )
        for seq in range(1, 4)
    )
    for event in events:
        store.put_raw(event)

    manager = TierManager(store)
    assert manager.reconcile_tiers(project_id, TierConfig(standard_n=1, mid_tier_n=2)) == (1, 2)
    assert manager.get_event(project_id, 1) == events[0]
    assert manager.get_range(project_id, 1, 3) == events
    assert manager.get_range(project_id, 1, 2) == events[:2]

    # Reconciliation is idempotent when a compressed copy already exists, and
    # range reads ignore records outside the requested window.
    store.put_raw(events[0])
    assert manager.reconcile_tiers(project_id, TierConfig(standard_n=0, mid_tier_n=2)) == (0, 3)
    assert manager.get_range(project_id, 4, 3) == ()
    assert manager.get_range(project_id, 4, 5) == ()


def test_reconciliation_keeps_raw_event_when_verification_fails() -> None:
    project_id = uuid4()
    event = LedgerEvent(
        event_id=uuid4(),
        project_id=project_id,
        cycle=1,
        phase=Phase.BUILD,
        seq=1,
        kind=EventKind.TURN_COMPLETED,
        engine_id=None,
        job_id=None,
        causation_id=None,
        correlation_id=project_id,
        provenance=Provenance.AGENT,
        produced_at=datetime(2026, 1, 1, tzinfo=UTC),
        payload={},
        digest=digest_event({}),
    )
    store = InMemoryLedgerTierStore()
    store.put_raw(event)
    manager = TierManager(store)

    with (
        patch.object(manager, "get_event", return_value=None),
        pytest.raises(ValueError, match="failed verification"),
    ):
        manager.reconcile_tiers(project_id, TierConfig(standard_n=0, mid_tier_n=0))

    assert store.raw_events(project_id) == (event,)


def test_range_skips_a_compressed_record_that_decodes_to_none() -> None:
    project_id = uuid4()
    store = InMemoryLedgerTierStore()
    store.put_compressed(project_id, 1, b"placeholder")
    manager = TierManager(store)

    with patch.object(manager, "get_event", return_value=None):
        assert manager.get_range(project_id, 1, 1) == ()


def test_tier_manager_rejects_corrupt_and_misidentified_compressed_records() -> None:
    project_id = uuid4()
    store = InMemoryLedgerTierStore()
    manager = TierManager(store)

    store.put_compressed(project_id, 1, b"not compressed")
    with pytest.raises(ValueError, match="invalid compressed"):
        manager.get_event(project_id, 1)

    event = LedgerEvent(
        event_id=uuid4(),
        project_id=project_id,
        cycle=1,
        phase=Phase.BUILD,
        seq=1,
        kind=EventKind.TURN_COMPLETED,
        engine_id=None,
        job_id=None,
        causation_id=None,
        correlation_id=project_id,
        provenance=Provenance.AGENT,
        produced_at=datetime(2026, 1, 1, tzinfo=UTC),
        payload={},
        digest=digest_event({}),
    )
    fields = LEDGER_RECORDS.to_fields(event)
    store.put_compressed(
        project_id,
        2,
        DEFAULT_CODEC.compress(json.dumps(fields).encode("utf-8")),
    )
    with pytest.raises(ValueError, match="identity mismatch"):
        manager.get_event(project_id, 2)


def test_tier_store_refuses_conflicting_compressed_replays() -> None:
    project_id = uuid4()
    store = InMemoryLedgerTierStore()
    store.put_compressed(project_id, 1, b"first")

    with pytest.raises(ValueError, match="already exists"):
        store.put_compressed(project_id, 1, b"different")
