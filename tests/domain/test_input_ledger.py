# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Rows are held to the ledger's adds one to one, in ledger order (SP-LOOPS Phase 3c, fix round 1:
review I2, I3). Module-level test functions (ADR-0016 is about production code)."""

from __future__ import annotations

import pytest

from vibey.domain.input_ledger import (
    INPUT_LEDGER,
    InputLedger,
    RecordedInput,
    RecordedInputs,
)
from vibey.domain.interfaces.input_ledger_interface import InputLedgerInterface
from vibey.domain.run_input import RUN_INPUT_RULE, RunInput, digest_of

D1, D2 = digest_of(b"one"), digest_of(b"two")


def _add(
    digest: str,
    kind: str = "file",
    size: int = 3,
    name: str | None = "spec.md",
    artifact_type: str = "vibey_run_input",
) -> dict[str, object]:
    payload: dict[str, object] = {
        "artifact_type": artifact_type,
        "digest": digest,
        "kind": kind,
        "size": size,
    }
    if name is not None:
        payload["name_digest"] = RUN_INPUT_RULE.name_digest(name)
    return payload


def _row(digest: str, kind: str = "file", name: str = "spec.md", size: int = 3) -> RunInput:
    return RunInput(digest=digest, kind=kind, name=name, size=size)  # type: ignore[arg-type]


def test_the_rule_meets_its_interface() -> None:
    assert isinstance(INPUT_LEDGER, InputLedgerInterface)
    assert isinstance(InputLedger(), InputLedgerInterface)


def test_adds_are_in_seq_order_and_malformed_payloads_are_ignored() -> None:
    recorded = INPUT_LEDGER.recorded(
        [
            (9, _add(D2)),
            (2, _add(D1)),
            (3, {"artifact_type": "vibey_run_inputs_given", "digests": [D1]}),
            (4, _add("nothex")),
            (5, _add(D1, kind="note")),
            (6, _add(D1, size=-1)),
            (7, _add(D1, size=True)),  # type: ignore[arg-type]
            (8, {**_add(D1), "name_digest": "x"}),
        ]
    )
    assert [(r.seq, r.digest) for r in recorded.added] == [(2, D1), (9, D2)]


def test_a_failure_correction_cancels_the_latest_matching_add_before_it() -> None:
    recorded = INPUT_LEDGER.recorded(
        [
            (1, _add(D1)),
            (2, _add(D1)),
            (3, _add(D1, artifact_type="vibey_run_input_failed")),
            (4, _add(D2, artifact_type="vibey_run_input_failed")),  # cancels nothing
        ]
    )
    assert [r.seq for r in recorded.added] == [1]


def test_rows_are_given_in_ledger_order_one_row_per_add() -> None:
    recorded = INPUT_LEDGER.recorded([(1, _add(D1)), (2, _add(D2))])
    rows = [_row(D2), _row(D1)]  # the store lists them the other way round
    reconciled = INPUT_LEDGER.reconcile(rows, recorded)
    assert [r.digest for r in reconciled.given] == [D1, D2]
    assert reconciled.unrecorded == 0 and reconciled.missing == ()


def test_a_planted_older_version_of_a_file_is_not_a_rollback() -> None:
    recorded = INPUT_LEDGER.recorded([(1, _add(D1)), (2, _add(D2))])
    rows = [_row(D1), _row(D2), _row(D1)]  # the attacker's newer row brings the old bytes back
    reconciled = INPUT_LEDGER.reconcile(rows, recorded)
    assert [r.digest for r in reconciled.given] == [D1, D2]  # later-add-wins gives D2
    assert reconciled.unrecorded == 1


@pytest.mark.parametrize(
    "planted",
    [
        _row(D1, kind="paste", name="paste"),  # a recorded file re-planted as a paste
        _row(D1, name="other.md"),  # under another name
        _row(D1, size=10**10),  # a size that would fail every read
    ],
)
def test_a_row_differing_in_kind_name_or_size_is_not_the_add(planted: RunInput) -> None:
    recorded = INPUT_LEDGER.recorded([(1, _add(D1))])
    reconciled = INPUT_LEDGER.reconcile([planted], recorded)
    assert reconciled.given == ()
    assert reconciled.unrecorded == 1
    assert [m.digest for m in reconciled.missing] == [D1]


def test_a_duplicated_paste_row_is_given_once() -> None:
    recorded = INPUT_LEDGER.recorded([(1, _add(D1, kind="paste", name="paste"))])
    rows = [_row(D1, kind="paste", name="paste")] * 2
    reconciled = INPUT_LEDGER.reconcile(rows, recorded)
    assert len(reconciled.given) == 1 and reconciled.unrecorded == 1


def test_an_add_with_no_name_digest_matches_any_name() -> None:
    recorded = INPUT_LEDGER.recorded([(1, _add(D1, name=None))])
    assert INPUT_LEDGER.reconcile([_row(D1, name="anything.md")], recorded).given


def test_a_recorded_input_says_what_it_is() -> None:
    record = RecordedInput(1, D1, "file", 3, None)
    assert record.describe() == f"file {D1} (3 bytes)"
    assert RecordedInputs(added=(record,)).added == (record,)
