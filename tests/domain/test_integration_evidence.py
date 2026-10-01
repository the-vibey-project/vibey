# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""REVIEW's evidence is what the integration gates actually did, never a default."""

import json
from datetime import UTC, datetime
from uuid import uuid4
from xml.etree import ElementTree

import pytest

from vibey.domain.integration_evidence import (
    GATE_RESULTS_ARTIFACT_TYPE,
    GateRun,
    IntegrationEvidence,
    ItemEvidence,
)
from vibey.domain.interfaces import (
    GateRunInterface,
    IntegrationEvidenceInterface,
    ItemEvidenceInterface,
)
from vibey.domain.ledger import EventKind, LedgerEvent, Provenance
from vibey.domain.phase import Phase

NOW = datetime(2026, 9, 30, tzinfo=UTC)


def _event(
    payload: dict[str, object],
    *,
    cycle: int = 1,
    seq: int = 1,
    kind: EventKind = EventKind.ARTIFACT_PRODUCED,
) -> LedgerEvent:
    return LedgerEvent(
        event_id=uuid4(),
        project_id=uuid4(),
        cycle=cycle,
        phase=Phase.BUILD,
        seq=seq,
        kind=kind,
        engine_id=None,
        job_id=uuid4(),
        causation_id=None,
        correlation_id=uuid4(),
        provenance=Provenance.TRUSTED,
        produced_at=NOW,
        payload=payload,
        digest="d",
    )


def _recorded(item: ItemEvidence, *, cycle: int = 1, seq: int = 1) -> LedgerEvent:
    return _event(item.to_payload(cycle=cycle), cycle=cycle, seq=seq)


def test_the_types_honour_their_interfaces() -> None:
    run = GateRun(command="pytest", returncode=0, output_tail="1 passed")
    item = ItemEvidence(work_item_id="wi-1", runs=(run,))
    evidence = IntegrationEvidence(items=(item,))
    assert isinstance(run, GateRunInterface)
    assert isinstance(item, ItemEvidenceInterface)
    assert isinstance(evidence, IntegrationEvidenceInterface)


def test_a_gate_run_needs_a_command() -> None:
    with pytest.raises(ValueError, match="command"):
        GateRun(command="  ", returncode=0, output_tail="")


def test_an_item_needs_an_id() -> None:
    with pytest.raises(ValueError, match="work item"):
        ItemEvidence(work_item_id="", runs=())


def test_a_run_passes_only_on_exit_zero() -> None:
    assert GateRun(command="pytest", returncode=0, output_tail="").passed
    assert not GateRun(command="pytest", returncode=1, output_tail="").passed


def test_an_item_with_no_runs_is_unmeasured_not_green() -> None:
    assert not ItemEvidence(work_item_id="wi-1", runs=()).measured
    assert ItemEvidence(
        work_item_id="wi-1", runs=(GateRun(command="pytest", returncode=0, output_tail=""),)
    ).measured


def test_payload_round_trips() -> None:
    item = ItemEvidence(
        work_item_id="wi-1",
        runs=(
            GateRun(command="pytest tests/", returncode=0, output_tail="3 passed"),
            GateRun(command="ruff check .", returncode=0, output_tail="(no output)"),
        ),
    )
    payload = item.to_payload(cycle=2)
    assert payload["artifact_type"] == GATE_RESULTS_ARTIFACT_TYPE
    assert payload["cycle"] == 2
    assert ItemEvidence.from_payload(payload) == item


@pytest.mark.parametrize(
    "payload",
    [
        {"artifact_type": GATE_RESULTS_ARTIFACT_TYPE},
        {"artifact_type": GATE_RESULTS_ARTIFACT_TYPE, "work_item_id": "wi-1", "runs": "nope"},
        {"artifact_type": GATE_RESULTS_ARTIFACT_TYPE, "work_item_id": "wi-1", "runs": ["x"]},
        {
            "artifact_type": GATE_RESULTS_ARTIFACT_TYPE,
            "work_item_id": "wi-1",
            "runs": [{"command": "pytest", "returncode": "zero"}],
        },
        {
            "artifact_type": GATE_RESULTS_ARTIFACT_TYPE,
            "work_item_id": "wi-1",
            "runs": [{"command": "", "returncode": 0}],
        },
        {
            "artifact_type": GATE_RESULTS_ARTIFACT_TYPE,
            "work_item_id": "wi-1",
            "runs": [{"command": "pytest", "returncode": True}],
        },
        {"artifact_type": GATE_RESULTS_ARTIFACT_TYPE, "work_item_id": "  ", "runs": []},
    ],
)
def test_a_malformed_payload_is_no_evidence_rather_than_an_error(
    payload: dict[str, object],
) -> None:
    assert ItemEvidence.from_payload(payload) is None


def test_from_ledger_keeps_this_cycles_latest_record_per_item() -> None:
    old = ItemEvidence(
        work_item_id="wi-1", runs=(GateRun(command="pytest", returncode=0, output_tail="old"),)
    )
    new = ItemEvidence(
        work_item_id="wi-1", runs=(GateRun(command="pytest", returncode=0, output_tail="new"),)
    )
    other = ItemEvidence(
        work_item_id="wi-2", runs=(GateRun(command="make", returncode=0, output_tail=""),)
    )
    events = (
        _recorded(old, seq=1),
        _recorded(other, seq=2),
        _recorded(new, seq=3),
        _recorded(other, cycle=2, seq=4),  # another cycle never counts
        _event({"artifact_type": "vibey_skills_context_packet"}, seq=5),
        _event({"finding_id": "f"}, kind=EventKind.FINDING_RAISED, seq=6),
        # An unreadable record is no evidence; it never replaces a readable one.
        _event({"artifact_type": GATE_RESULTS_ARTIFACT_TYPE, "work_item_id": "wi-1"}, seq=7),
    )
    evidence = IntegrationEvidence.from_ledger(events, cycle=1)
    assert evidence.items == (new, other)


def test_no_records_is_unmeasured() -> None:
    evidence = IntegrationEvidence.from_ledger((), cycle=1)
    assert not evidence.measured
    assert evidence.unmeasured == ()


def test_any_item_without_runs_makes_the_cycle_unmeasured() -> None:
    ran = ItemEvidence(
        work_item_id="wi-1", runs=(GateRun(command="pytest", returncode=0, output_tail=""),)
    )
    empty = ItemEvidence(work_item_id="wi-2", runs=())
    evidence = IntegrationEvidence(items=(ran, empty))
    assert not evidence.measured
    assert evidence.unmeasured == ("wi-2",)
    assert IntegrationEvidence(items=(ran,)).measured


def test_the_report_counts_only_what_ran() -> None:
    evidence = IntegrationEvidence(
        items=(
            ItemEvidence(
                work_item_id="wi-1",
                runs=(
                    GateRun(command="pytest", returncode=0, output_tail="3 passed"),
                    GateRun(command="ruff check .", returncode=1, output_tail="E501 <long>"),
                ),
            ),
            ItemEvidence(work_item_id="wi-2", runs=()),
        )
    )
    root = ElementTree.fromstring(evidence.junit_xml())
    assert root.get("tests") == "2"
    assert root.get("failures") == "1"
    assert root.get("skipped") == "1"
    cases = root.findall(".//testcase")
    assert [(c.get("classname"), c.get("name")) for c in cases] == [
        ("wi-1", "pytest"),
        ("wi-1", "ruff check ."),
        ("wi-2", "no verification commands"),
    ]
    failure = cases[1].find("failure")
    assert failure is not None
    assert failure.text == "E501 <long>"
    assert cases[2].find("skipped") is not None


def test_an_empty_report_says_nothing_ran() -> None:
    xml = IntegrationEvidence(items=()).junit_xml()
    root = ElementTree.fromstring(xml)
    assert root.get("tests") == "0"
    assert root.get("failures") == "0"
    assert "no integration gate evidence was recorded" in xml


def test_coverage_is_never_claimed() -> None:
    measured = IntegrationEvidence(
        items=(
            ItemEvidence(
                work_item_id="wi-1",
                runs=(GateRun(command="pytest", returncode=0, output_tail=""),),
            ),
        )
    )
    for evidence in (measured, IntegrationEvidence(items=())):
        coverage = json.loads(evidence.coverage_json())
        assert coverage["measured"] is False
        assert "coverage" not in coverage


def test_the_statement_names_what_is_missing() -> None:
    ran = ItemEvidence(
        work_item_id="wi-1", runs=(GateRun(command="pytest", returncode=0, output_tail=""),)
    )
    assert IntegrationEvidence(items=(ran,)).statement() == (
        "1 integration gate run(s) across 1 work item(s); 0 failed."
    )
    assert "no integration gate evidence was recorded" in (
        IntegrationEvidence(items=()).statement()
    )
    assert (
        "wi-2"
        in IntegrationEvidence(items=(ran, ItemEvidence(work_item_id="wi-2", runs=()))).statement()
    )


def test_awkward_commands_and_output_stay_well_formed_xml() -> None:
    evidence = IntegrationEvidence(
        items=(
            ItemEvidence(
                work_item_id='wi-"1"',
                runs=(GateRun(command="test \"a\" & 'b' < c", returncode=2, output_tail="<&>"),),
            ),
        )
    )
    case = ElementTree.fromstring(evidence.junit_xml()).find(".//testcase")
    assert case is not None
    assert case.get("classname") == 'wi-"1"'
    assert case.get("name") == "test \"a\" & 'b' < c"
    failure = case.find("failure")
    assert failure is not None
    assert failure.text == "<&>"
