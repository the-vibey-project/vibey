# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from __future__ import annotations

import json
from pathlib import Path

import pytest

from vibey_gh.delivery_estimate import (
    BillingUsage,
    DeliveryEstimator,
    IssueObservation,
    WorkHistoryCalculator,
)
from vibey_gh.delivery_sources import DeliverySourceSnapshot
from vibey_gh.estimate_ledger import BillingLedgerReader, DeliveryEstimateLedger, _digest
from vibey_gh.feasibility import StateVector
from vibey_gh.interfaces.delivery_estimate_interface import (
    BillingLedgerReaderInterface,
    BillingLedgerSnapshotInterface,
    DeliveryEstimateLedgerInterface,
)


def _forecast(fingerprint: str = "fingerprint", dollars: float = 2.0):
    snapshot = DeliverySourceSnapshot(
        issues=(IssueObservation(1, "OPEN"),), source_revision="revision"
    )
    history = WorkHistoryCalculator().calculate(snapshot)
    return DeliveryEstimator().calculate(
        history,
        BillingUsage(dollars=dollars, budget_turns=1),
        state=StateVector.unknown(),
        recorded_at="2026-09-19T00:00:00Z",
        source_fingerprint=fingerprint,
    )


def test_billing_reader_uses_the_budget_brake_vocabulary(tmp_path: Path) -> None:
    source = tmp_path / "billing.jsonl"
    source.write_text(
        "\n".join(
            [
                json.dumps({"shard": {"format": "test"}}),
                json.dumps(
                    {
                        "kind": "TurnCompleted",
                        "produced_at": "2026-09-18T00:00:00Z",
                        "payload": {"cost_usd": 1.5},
                    }
                ),
                json.dumps(
                    {
                        "kind": "BudgetSpent",
                        "produced_at": "2026-09-18T00:00:05Z",
                        "payload": {"dollars": 2, "turns": 3},
                    }
                ),
                json.dumps(
                    {
                        "kind": "BudgetSpent",
                        "payload": {"dollars": 0, "turns": True},
                    }
                ),
                json.dumps({"kind": "PhaseTransitioned", "produced_at": "bad", "payload": {}}),
                json.dumps({"kind": "CapacityRejected", "payload": {}}),
                json.dumps({"kind": "HandoffInitiated", "payload": {}}),
                json.dumps({"kind": "ToolInvoked", "payload": {}}),
                json.dumps({"kind": "FileEdited", "payload": {}}),
                json.dumps({"kind": "ArtifactProduced", "payload": {}}),
                json.dumps({"kind": "UnclassifiedEvent", "payload": {}}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    reader = BillingLedgerReader()
    result = reader.read(source)
    assert isinstance(reader, BillingLedgerReaderInterface)
    assert isinstance(result, BillingLedgerSnapshotInterface)
    assert result.usage.dollars == 3.5
    assert result.usage.turn_completed_events == 1
    assert result.usage.budget_turns == 3
    assert result.usage.elapsed_seconds == 5.0
    assert result.usage.ledger_events == 10
    assert result.usage.phase_transition_events == 1
    assert result.usage.capacity_rejections == 1
    assert result.usage.handoffs == 1
    assert result.usage.tool_invocations == 1
    assert result.usage.file_edits == 1
    assert result.usage.artifacts_produced == 1
    untimed = tmp_path / "untimed.jsonl"
    untimed.write_text('{"kind": "PhaseTransitioned", "payload": {}}\n', encoding="utf-8")
    untimed_usage = reader.read(untimed).usage
    assert untimed_usage.elapsed_seconds is None
    assert untimed_usage.dollars is None


def test_billing_reader_does_not_turn_missing_or_corrupt_data_into_zero(tmp_path: Path) -> None:
    reader = BillingLedgerReader()
    missing = reader.read(tmp_path / "missing.jsonl")
    assert missing.usage.dollars is None
    assert missing.problems
    source = tmp_path / "bad.jsonl"
    source.write_text("not-json\n[]\n", encoding="utf-8")
    bad = reader.read(source)
    assert bad.usage.ledger_events is None
    assert len(bad.problems) == 2
    empty = tmp_path / "empty.jsonl"
    empty.write_text("\n", encoding="utf-8")
    assert "no event records" in reader.read(empty).problems[0]
    no_events = tmp_path / "header.jsonl"
    no_events.write_text('{"shard": {}}\n', encoding="utf-8")
    assert "no event records" in reader.read(no_events).problems[0]


def test_estimate_ledger_is_digest_linked_idempotent_and_human_readable(tmp_path: Path) -> None:
    ledger = DeliveryEstimateLedger()
    assert isinstance(ledger, DeliveryEstimateLedgerInterface)
    path = tmp_path / "estimates.jsonl"
    report = tmp_path / "docs" / "estimate.md"
    first = _forecast("a")
    second = _forecast("b")
    changed_billing = _forecast("a", dollars=4.0)
    assert ledger.record(first, path)
    assert not ledger.record(first, path)
    assert ledger.record(second, path)
    assert ledger.record(changed_billing, path)
    records = ledger.read(path)
    assert len(records) == 3
    assert records[0]["source_fingerprint"] == "a"
    ledger.write_report(changed_billing, report)
    assert "Continuous delivery estimate" in report.read_text(encoding="utf-8")
    envelopes = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert envelopes[1]["previous_digest"] == envelopes[0]["digest"]
    assert all(envelope["kind"] == "DeliveryEstimateRecorded" for envelope in envelopes)


@pytest.mark.parametrize(
    "mutator, message",
    [
        (lambda value: value.replace('"seq":1', '"seq":2'), "seq"),
        (
            lambda value: value.replace('"previous_digest":"' + "0" * 64, '"previous_digest":"bad'),
            "chain",
        ),
        (lambda value: value.replace('"digest":"', '"digest":"bad'), "digest"),
        (lambda value: "[]\n", "object"),
        (lambda value: '{"seq":1}\n', "previous_digest"),
    ],
)
def test_estimate_ledger_refuses_tampering(tmp_path: Path, mutator, message: str) -> None:
    path = tmp_path / "ledger.jsonl"
    ledger = DeliveryEstimateLedger()
    ledger.record(_forecast(), path)
    original = path.read_text(encoding="utf-8")
    path.write_text(mutator(original), encoding="utf-8")
    with pytest.raises((ValueError, TypeError), match=message):
        ledger.read(path)


def test_estimate_ledger_refuses_bad_existing_shape(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    path.write_text("not json\n", encoding="utf-8")
    with pytest.raises(ValueError, match="not JSON"):
        DeliveryEstimateLedger().record(_forecast(), path)


def test_estimate_ledger_skips_blank_lines_and_checks_payload_and_seq_types(tmp_path: Path) -> None:
    path = tmp_path / "ledger.jsonl"
    ledger = DeliveryEstimateLedger()
    ledger.record(_forecast(), path)
    original = path.read_text(encoding="utf-8")
    path.write_text("\n" + original, encoding="utf-8")
    assert len(ledger.read(path)) == 1
    legacy = json.loads(original)
    legacy.pop("input_digest")
    legacy["digest"] = _digest({key: value for key, value in legacy.items() if key != "digest"})
    path.write_text(json.dumps(legacy) + "\n", encoding="utf-8")
    assert not ledger.record(_forecast(), path)

    envelope = json.loads(original)
    envelope["payload"] = []
    path.write_text(json.dumps(envelope) + "\n", encoding="utf-8")
    with pytest.raises(TypeError, match="no object payload"):
        ledger.read(path)

    envelope = json.loads(original)
    envelope["seq"] = "1"
    path.write_text(json.dumps(envelope) + "\n", encoding="utf-8")
    with pytest.raises(TypeError, match="seq must be an integer"):
        ledger.read(path)


def test_estimate_ledger_reports_unreadable_paths(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="cannot read estimate ledger"):
        DeliveryEstimateLedger().read(tmp_path)
    assert DeliveryEstimateLedger._input_digest({"payload": []}) is None
