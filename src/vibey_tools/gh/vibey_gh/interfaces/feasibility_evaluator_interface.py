# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for deciding whether a state can carry a run through its stages (ADR-0016).

`feasible(o) ⟺ x ⪰ r_o` from the governance-dilemma calculus (docs/paper.md), evaluated
at every stage the run must pass rather than only the next one, and three-valued: a
coordinate nobody measured makes the answer `unknown`, never `yes` (doctrine 10).

`StateVector`, `Stage` and `PipelineVerdict` are imported for typing only -- frozen data,
the same standing `Machine` has in the memory seam.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey_gh.feasibility import PipelineVerdict, Stage, StateVector


@runtime_checkable
class FeasibilityEvaluatorInterface(Protocol):
    """Judges one state against the requirement vector of every stage a run passes."""

    def evaluate(self, state: StateVector, stages: Sequence[Stage]) -> PipelineVerdict:
        """`yes` only when every required coordinate is measured and meets its minimum;
        `no` as soon as one measured coordinate falls short anywhere on the path;
        `unknown` otherwise. Shortfalls are reported in the evaluator's priority order,
        agency first by default -- a run that cannot merge is infeasible however healthy
        everything else is."""
        ...
