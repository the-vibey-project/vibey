# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What the integration gates actually did, as REVIEW's evidence (sub-doctrine 10.f).

`build.integrate` runs a work item's verification commands against the merged
integration branch. Each successful integrate writes what ran -- every command, its exit
code and the tail of its output -- to the ledger as an `ArtifactProduced` event of type
`integration_gate_results`. `review.demo` reads the cycle's latest record per work item
back and renders it as the evidence a person reviews.

Nothing here invents a result. Before this, `review.demo` was always enqueued with an
empty payload and fell back to a hard-coded "0 failures" test report and a
`{"coverage": 100, "status": "green"}` coverage file, so every REVIEW showed a green
report nobody had measured. Now:

- an item whose plan carried no verification commands is *unmeasured*, never green;
- a cycle with no record at all is unmeasured, and the report says so;
- coverage is never claimed, because vibey does not measure it.
"""

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from xml.sax.saxutils import escape, quoteattr

from vibey.domain.ledger import EventKind, LedgerEvent

GATE_RESULTS_ARTIFACT_TYPE = "integration_gate_results"
"""The `artifact_type` of the `ArtifactProduced` event a successful integrate records."""

EVIDENCE_MISSING_GATE_KIND = "review_evidence_missing"
"""The human gate REVIEW parks on when it has no measured evidence to show."""

_NO_EVIDENCE = "no integration gate evidence was recorded for this cycle"


@dataclass(frozen=True, slots=True)
class GateRun:
    """One verification command run against the integration branch."""

    command: str
    returncode: int
    output_tail: str

    def __post_init__(self) -> None:
        if not self.command.strip():
            raise ValueError("a gate run names the command that ran")

    @property
    def passed(self) -> bool:
        return self.returncode == 0

    def to_payload(self) -> dict[str, object]:
        return {
            "command": self.command,
            "returncode": self.returncode,
            "output_tail": self.output_tail,
        }


@dataclass(frozen=True, slots=True)
class ItemEvidence:
    """Every gate run for one work item's integration. No runs means unmeasured."""

    work_item_id: str
    runs: tuple[GateRun, ...]

    def __post_init__(self) -> None:
        if not self.work_item_id.strip():
            raise ValueError("item evidence names the work item it is for")

    @property
    def measured(self) -> bool:
        return bool(self.runs)

    def to_payload(self, *, cycle: int) -> dict[str, object]:
        """The `ArtifactProduced` payload a successful integrate records."""
        return {
            "artifact_id": f"integrate-gates-{self.work_item_id}",
            "artifact_type": GATE_RESULTS_ARTIFACT_TYPE,
            "cycle": cycle,
            "work_item_id": self.work_item_id,
            "runs": [run.to_payload() for run in self.runs],
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> "ItemEvidence | None":
        """The record read back, or None when it cannot be read. An unreadable record
        is no evidence -- it never becomes a pass."""
        work_item_id = payload.get("work_item_id")
        raw_runs = payload.get("runs")
        if not isinstance(work_item_id, str) or not isinstance(raw_runs, list):
            return None
        runs: list[GateRun] = []
        for raw in raw_runs:
            if not isinstance(raw, Mapping):
                return None
            command = raw.get("command")
            returncode = raw.get("returncode")
            output_tail = raw.get("output_tail", "")
            if (
                not isinstance(command, str)
                or not command.strip()
                or not isinstance(returncode, int)
                or isinstance(returncode, bool)
            ):
                return None
            runs.append(GateRun(command, returncode, str(output_tail)))
        try:
            return cls(work_item_id=work_item_id, runs=tuple(runs))
        except ValueError:
            return None


@dataclass(frozen=True, slots=True)
class IntegrationEvidence:
    """A cycle's integration gate evidence: the latest record per work item."""

    items: tuple[ItemEvidence, ...]

    @classmethod
    def from_ledger(cls, events: Iterable[LedgerEvent], *, cycle: int) -> "IntegrationEvidence":
        """Read this cycle's records in ledger order. A later record for an item
        supersedes an earlier one -- a repaired item's re-integration is what counts."""
        latest: dict[str, ItemEvidence] = {}
        for event in events:
            if (
                not event.interpretable
                or event.kind is not EventKind.ARTIFACT_PRODUCED
                or event.cycle != cycle
                or event.payload.get("artifact_type") != GATE_RESULTS_ARTIFACT_TYPE
            ):
                continue
            item = ItemEvidence.from_payload(event.payload)
            if item is not None:
                latest[item.work_item_id] = item
        return cls(items=tuple(latest.values()))

    @property
    def unmeasured(self) -> tuple[str, ...]:
        """The work items whose integration ran no verification command."""
        return tuple(item.work_item_id for item in self.items if not item.measured)

    @property
    def measured(self) -> bool:
        """True only when there is a record and every item ran at least one gate."""
        return bool(self.items) and not self.unmeasured

    def _runs(self) -> tuple[GateRun, ...]:
        return tuple(run for item in self.items for run in item.runs)

    def statement(self) -> str:
        """One plain sentence for the reviewer and for a gate prompt."""
        if not self.items:
            return f"Unmeasured: {_NO_EVIDENCE}."
        runs = self._runs()
        failed = sum(1 for run in runs if not run.passed)
        sentence = (
            f"{len(runs)} integration gate run(s) across {len(self.items)} work item(s); "
            f"{failed} failed."
        )
        if self.unmeasured:
            sentence += (
                " Unmeasured -- no verification commands ran for: "
                + ", ".join(self.unmeasured)
                + "."
            )
        return sentence

    def junit_xml(self) -> str:
        """A JUnit report of exactly what ran. An unmeasured item is a skipped case,
        so it is visible in any JUnit viewer instead of silently absent."""
        runs = self._runs()
        failures = sum(1 for run in runs if not run.passed)
        skipped = len(self.unmeasured)
        cases: list[str] = []
        for item in self.items:
            classname = quoteattr(item.work_item_id)
            if not item.runs:
                cases.append(
                    f"    <testcase classname={classname} name="
                    f'"no verification commands"><skipped message="unmeasured"/></testcase>'
                )
            for run in item.runs:
                name = quoteattr(run.command)
                if run.passed:
                    cases.append(f"    <testcase classname={classname} name={name}/>")
                else:
                    cases.append(
                        f"    <testcase classname={classname} name={name}>"
                        f'<failure message="exit {run.returncode}">{escape(run.output_tail)}'
                        "</failure></testcase>"
                    )
        if not cases:
            cases.append(f"    <!-- {_NO_EVIDENCE} -->")
        counts = f'tests="{len(runs)}" failures="{failures}" skipped="{skipped}"'
        return "\n".join(
            (
                '<?xml version="1.0" encoding="UTF-8"?>',
                f"<testsuites {counts}>",
                f'  <testsuite name="integration-gates" {counts}>',
                *cases,
                "  </testsuite>",
                "</testsuites>",
                "",
            )
        )

    def coverage_json(self) -> str:
        """Coverage is not measured by vibey, so it is never claimed."""
        return json.dumps(
            {
                "measured": False,
                "reason": (
                    "vibey does not measure coverage; the gates that ran are in test-report.xml"
                ),
            },
            indent=2,
        )
