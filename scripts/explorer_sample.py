# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Write the ledger explorer's sample shard and its static site.

The explorer (docs/explorer/) reads what `vibey ledger site` writes. Until a project
publishes its own shard, the page shows this one, built through the same exporter, policy
and site builder a real project goes through -- so it exercises every path of the page
(published, withheld, trimmed) while claiming nothing about any real project. Its name
says it is a sample, and so does the page.

Deterministic: ids come from uuid5 and times from a fixed start, so rerunning writes the
same bytes. Run `uv run python scripts/explorer_sample.py` after changing the sample.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from vibey.application.ledger_publication import LedgerExporter, LedgerSiteBuilder
from vibey.cli.ledger_publication import PUBLIC_POLICY, SHARD_STORE, SITE_WRITER
from vibey.domain.engine import EngineId
from vibey.domain.ledger import EventKind, LedgerEvent, Provenance, digest_event
from vibey.domain.ledger_chain import LEDGER_CHAIN
from vibey.domain.phase import Phase

REPO = Path(__file__).resolve().parents[1]
PROJECT_NAME = "sample-shift-signup"
OUT = REPO / "docs" / "explorer" / "data" / PROJECT_NAME
START = datetime(2026, 1, 12, 9, 0, tzinfo=UTC)


class SampleLedger:
    """An invented project's events, in the order a real one would write them."""

    def __init__(self) -> None:
        self.project_id = uuid5(NAMESPACE_URL, "vibey:explorer:sample")
        self._correlation = uuid5(NAMESPACE_URL, "vibey:explorer:sample:run")
        self._events: list[LedgerEvent] = []

    def add(
        self,
        kind: EventKind,
        phase: Phase,
        payload: dict[str, object],
        *,
        engine: EngineId | None = None,
        provenance: Provenance = Provenance.TRUSTED,
        cycle: int = 1,
    ) -> None:
        seq = len(self._events) + 1
        self._events.append(
            LedgerEvent(
                event_id=uuid5(self.project_id, f"event:{seq}"),
                project_id=self.project_id,
                cycle=cycle,
                phase=phase,
                seq=seq,
                kind=kind,
                engine_id=engine,
                job_id=None,
                causation_id=self._events[-1].event_id if self._events else None,
                correlation_id=self._correlation,
                provenance=provenance,
                produced_at=START + timedelta(minutes=7 * seq),
                payload=payload,
                digest=digest_event(payload),
            )
        )

    def events(self) -> tuple[LedgerEvent, ...]:
        return tuple(self._events)

    def build(self) -> None:
        P, K, E = Phase, EventKind, EngineId.GPTOSSLOOP
        self.add(K.SESSION_SEEDED, P.INTAKE, {"prompt": "A page where volunteers pick a shift"})
        self.add(
            K.QUESTION_ASKED,
            P.DESIGN,
            {
                "item_id": "item-1",
                "question_id": "q1",
                "stage": "design",
                "cycle": 1,
                "text": "Should a volunteer be able to cancel a shift they signed up for?",
                "default": "Yes, up to 24 hours before it starts",
                "blocking": True,
            },
        )
        self.add(
            K.ANSWER_GIVEN,
            P.DESIGN,
            {
                "item_id": "item-1",
                "question_id": "q1",
                "answer": "Yes, up to 24 hours before. Notes are in /Users/sam/handbook/shifts.md, "
                "questions to sam@example.org.",
            },
        )
        self.add(
            K.ASSUMPTION_STATED,
            P.DESIGN,
            {
                "item_id": "item-1",
                "assumption_id": "a1",
                "text": "Shifts are whole hours and never overlap.",
                "question": "q1",
            },
        )
        self.add(
            K.DECISION_RECORDED,
            P.DESIGN,
            {
                "decision_id": "d1",
                "decision": "Store shifts in SQLite for the first release",
                "title": "Storage",
                "choice": "sqlite",
                "rationale": "One small team, one server, no concurrent writers.",
                "alternatives": ["postgres", "a spreadsheet"],
                "next_phase": "build",
            },
        )
        self.add(
            K.PHASE_TRANSITIONED,
            P.DESIGN,
            {"from": "design", "to": "build", "cycle": 1, "guard": "spec_accepted"},
        )
        self.add(K.TURN_REQUESTED, P.BUILD, {"prompt": "Implement the shift list"}, engine=E)
        self.add(K.TURN_COMPLETED, P.BUILD, {"tokens": 4120, "output": "..."}, engine=E)
        self.add(K.BUDGET_SPENT, P.BUILD, {"usd": 0, "turns": 1}, engine=E)
        self.add(
            K.ARTIFACT_PRODUCED,
            P.BUILD,
            {
                "artifact_id": "art-1",
                "artifact_type": "source",
                "title": "Shift list page",
                "cycle": 1,
            },
            engine=E,
        )
        self.add(
            K.FINDING_RAISED,
            P.REVIEW,
            {
                "finding_id": "f1",
                "severity": "medium",
                "ambiguity": False,
                "text": "Cancelling twice books the shift for nobody.",
                "automated": True,
            },
        )
        self.add(
            K.PHASE_TRANSITIONED,
            P.REVIEW,
            {"from": "review", "to": "build", "cycle": 1, "guard": "findings_open"},
        )
        self.add(K.TURN_REQUESTED, P.BUILD, {"prompt": "Fix finding f1"}, engine=E, cycle=2)
        self.add(K.TURN_COMPLETED, P.BUILD, {"tokens": 1980, "output": "..."}, engine=E, cycle=2)
        self.add(
            K.FINDING_RESOLVED,
            P.REVIEW,
            {"finding_id": "f1", "resolution": "Cancel is now idempotent; test added."},
            cycle=2,
        )
        self.add(
            K.TRANSCRIPT_RECORDED,
            P.REVIEW,
            {"text": "text from outside"},
            provenance=Provenance.UNTRUSTED,
            cycle=2,
        )
        self.add(
            K.VERDICT_RENDERED,
            P.REVIEW,
            {"complete": True, "success": True, "remaining_work": []},
            cycle=2,
        )
        self.add(
            K.PHASE_TRANSITIONED,
            P.REVIEW,
            {"from": "review", "to": "done", "cycle": 2, "guard": "verdict_complete"},
            cycle=2,
        )


class NoDatabase:
    """The exporter's ledger reader, unused here: `shard()` takes its events directly."""

    async def all_for_project(self, project_id: UUID) -> list[LedgerEvent]:
        raise RuntimeError(f"the sample is built from events in memory, not project {project_id}")


class SampleWriter:
    def write(self) -> None:
        ledger = SampleLedger()
        ledger.build()
        exporter = LedgerExporter(
            ledger=NoDatabase(), store=SHARD_STORE, policy=PUBLIC_POLICY, chain=LEDGER_CHAIN
        )
        shard = exporter.shard(ledger.project_id, PROJECT_NAME, ledger.events())
        OUT.mkdir(parents=True, exist_ok=True)
        shard_path = OUT / "shard.jsonl"
        SHARD_STORE.write(shard, shard_path)
        LedgerSiteBuilder(store=SHARD_STORE, writer=SITE_WRITER).build(shard_path, OUT)
        print(
            f"wrote {shard.header.published_count} published, "
            f"{shard.header.events_withheld} withheld, "
            f"chain findings {shard.header.chain_findings} -> {OUT.relative_to(REPO)}"
        )


if __name__ == "__main__":
    SampleWriter().write()
