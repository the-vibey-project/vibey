# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What `vibey-gh estimate` found, as a record: the verdict, every basis, every unknown (#134).

Kept apart from `vibey_gh.operation_estimate`, which does the measuring, so the seam
that declares the estimator can name this record without reaching the code that reads
the machine, the runner and the fit journal (ADR-0016: interfaces declare, never
consume). Nothing here performs I/O; it only holds and renders.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from vibey_gh.estimation import Prediction
from vibey_gh.feasibility import NO, UNKNOWN, YES, Gap, PipelineVerdict, Stage, StateVector

__all__ = [
    "COST_REASON",
    "DEFAULT_PAYLOAD_BYTES",
    "EXIT_CODES",
    "REPAIR_REASON",
    "STAGE_DURATION_REASON",
    "OperationEstimate",
]

# The same default payload `vibey-gh fit` projects for, so the two commands answer about
# the same work unless told otherwise.
DEFAULT_PAYLOAD_BYTES = 8192

# 0 only when the whole path is known to be feasible. `unknown` is not success: a caller
# that branches on the exit status must not proceed on a coordinate nobody measured.
EXIT_CODES: Mapping[str, int] = {YES: 0, NO: 1, UNKNOWN: 3}

COST_REASON = (
    "no cost is measured yet — neither paid-lane spend nor local generation-seconds reach"
    " this command, and a number is never invented (doctrine 10)"
)
STAGE_DURATION_REASON = (
    "no stage timings are recorded in vibey-gh; phase timings live in the vibey ledger, and"
    " the forecast that reads them is a follow-up"
)
REPAIR_REASON = (
    "not computed — φ, the dilation each shortfall imposes on duration, is unspecified"
    " until measured, so the gradient -∇T cannot be taken; shortfalls are listed in"
    " priority order instead"
)


@dataclass(frozen=True)
class OperationEstimate:
    """Everything one estimate found, and the basis of every number in it."""

    operation: str
    start: str
    stages: tuple[Stage, ...]
    verdict: PipelineVerdict
    state: StateVector
    duration: Prediction
    payload_bytes: int
    model: str
    runner: str
    runner_read: bool
    offline: bool
    journal: Path | None

    @property
    def exit_code(self) -> int:
        return EXIT_CODES[self.verdict.verdict]

    def as_dict(self) -> dict[str, Any]:
        """The estimate as stable JSON: every number beside its source, every unknown as
        `null` beside the reason it is unknown."""
        return {
            "operation": self.operation,
            "from": self.start,
            "stages": [stage.name for stage in self.stages],
            "feasible": self.verdict.verdict,
            "blocked_at": self.verdict.blocked_at,
            "confidence": self.verdict.confidence,
            "measured": {
                "required": self.verdict.required,
                "required_measured": self.verdict.required_measured,
                "coordinates": self.state.measured,
                "of": len(self.state.coordinates),
            },
            "shortfalls": [self._gap(gap) for gap in self.verdict.shortfalls],
            "unknowns": [self._gap(gap) for gap in self.verdict.unknowns],
            "stage_verdicts": [
                {"stage": v.stage, "verdict": v.verdict, "gaps": [g.name for g in v.gaps]}
                for v in self.verdict.stages
            ],
            "state": [
                {
                    "coordinate": c.name,
                    "value": c.value,
                    "distance": c.distance,
                    "source": c.source,
                    "measured_at": c.measured_at,
                }
                for c in self.state.coordinates
            ],
            "duration": {
                "stages_s": None,
                "stages_reason": STAGE_DURATION_REASON,
                "local_service_s": self.duration.value,
                "basis": self.duration.basis,
                "n": self.duration.n,
                "reason": self.duration.reason,
                "payload_bytes": self.payload_bytes,
                "model": self.model,
                "journal": None if self.journal is None else str(self.journal),
            },
            "cost": {"value": None, "reason": COST_REASON},
            "repair": {"ranking": None, "reason": REPAIR_REASON},
            "runner": self.runner,
            "runner_read": self.runner_read,
            "offline": self.offline,
        }

    def lines(self) -> list[str]:
        """The estimate as a person reads it: verdict first, then every basis."""
        v = self.verdict
        say = "vibey-gh estimate:"
        out = [
            (
                f"{say} operation '{self.operation}' from '{self.start}' —"
                f" {' → '.join(stage.name for stage in self.stages)}"
            ),
            f"{say} feasible: {self._headline()}",
            f"{say} cost: unknown — {COST_REASON}",
            f"{say} duration: unknown for the stages — {STAGE_DURATION_REASON}",
            f"{say} local model service: {self._service()}",
            (
                f"{say} confidence: {v.confidence:g} — {v.required_measured} of {v.required}"
                f" required coordinate(s) measured; {self.state.measured} of"
                f" {len(self.state.coordinates)} in all"
            ),
        ]
        if v.shortfalls:
            out += [f"{say} shortfall — {gap.describe()}" for gap in v.shortfalls]
        else:
            out.append(f"{say} shortfalls: none measured")
        for name, stages in self._unknown_by_coordinate():
            out.append(f"{say} unknown — {name}, needed at {', '.join(stages)}")
        out.append(f"{say} repair ranking: {REPAIR_REASON}")
        out.append(f"{say} state (d = 1 - x is the distance from peak):")
        for c in self.state.coordinates:
            reading = "unknown" if c.value is None else f"{c.value:g}  d={c.distance:g}"
            when = "" if c.value is None else f"  at {self._utc(c.measured_at)}"
            out.append(f"  {c.material:<12} {c.prop:<13} {reading:<16} {c.source}{when}")
        out.append(f"{say} stages:")
        for stage in v.stages:
            gaps = ", ".join(g.name for g in stage.gaps) or "every requirement met"
            out.append(f"  {stage.stage:<20} {stage.verdict.upper():<8} {gaps}")
        return out

    def _headline(self) -> str:
        v = self.verdict
        if v.verdict == NO:
            return f"NO — blocked at stage '{v.blocked_at}'; first: {v.shortfalls[0].describe()}"
        if v.verdict == YES:
            return "YES — every coordinate the path requires is measured and meets its minimum"
        missing = v.required - v.required_measured
        return (
            f"UNKNOWN — {missing} of {v.required} required coordinate(s) unmeasured; none"
            " measured short"
        )

    def _service(self) -> str:
        d = self.duration
        if d.value is None:
            where = "no journal" if self.journal is None else f"journal {self.journal}"
            return f"unknown — {d.reason} ({where})"
        return (
            f"{d.value:.1f}s for {self.payload_bytes} bytes on {self.model}"
            f" ({d.basis}, n={d.n}: {d.reason})"
        )

    def _unknown_by_coordinate(self) -> list[tuple[str, list[str]]]:
        grouped: dict[str, list[str]] = {}
        for gap in self.verdict.unknowns:
            grouped.setdefault(gap.name, []).append(gap.stage)
        return list(grouped.items())

    @staticmethod
    def _gap(gap: Gap) -> dict[str, Any]:
        return {
            "stage": gap.stage,
            "coordinate": gap.name,
            "minimum": gap.minimum,
            "value": gap.value,
            "source": gap.source,
        }

    @staticmethod
    def _utc(at: float | None) -> str:
        if at is None:
            return "an unrecorded time"
        return datetime.fromtimestamp(at, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
