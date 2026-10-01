# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract `scripts/requirements_math.py` implements. Interfaces declare; they never consume.

The models the minimum-requirements derivations fit to measured figures, and the closed
forms solved on them: a least-squares line (memory against context), Amdahl's law
(throughput against cores) with its marginal-gain knee and its rate floor, and the integral
of a linearly growing rate (ledger bytes over a retention horizon).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol


class RequirementsMathInterface(Protocol):
    """Pure arithmetic: no I/O, no clock. The same inputs always give the same outputs."""

    def least_squares(self, xs: Sequence[float], ys: Sequence[float]) -> Any:
        """The line y = a + b*x minimising squared residuals, with R^2 and the residuals."""
        ...

    def amdahl(self, cores: Sequence[float], rates: Sequence[float]) -> Any:
        """T(n) = T1 / ((1 - p) + p / n) fitted to measured rates at each core count."""
        ...

    def knee(self, fit: Any, threshold: float) -> float:
        """The core count where dT/dn falls to `threshold` (tokens/s per added core)."""
        ...

    def cores_for_rate(self, fit: Any, floor: float) -> int | None:
        """The fewest cores with T(n) >= `floor`, or None when no count reaches it."""
        ...

    def integral_of_linear_rate(
        self, per_unit: float, rate0: float, rate1: float, horizon: float
    ) -> float:
        """The integral from 0 to `horizon` of per_unit * (rate0 + rate1 * t) dt."""
        ...
