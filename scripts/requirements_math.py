# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The models behind vibey's derived requirements, fitted only to what was measured.

Three models, each chosen because the mechanism predicts its shape, and each fitted in
closed form so `scripts/minimum_specs.py check` can recompute it from the committed record
and get the same digits:

* **Memory against context is a line.** The weights are a constant; the KV cache and the
  compute buffers grow in proportion to the context window. So M(c) = M0 + k*c, fitted by
  ordinary least squares, with R^2 and the residuals reported so a bend shows.
* **CPU throughput against cores follows Amdahl's law.** T(n) = T1 / ((1 - p) + p / n), where
  p is the parallel fraction. Its reciprocal is linear in 1/n --
  1/T = (1 - p)/T1 + (p/T1) * (1/n) -- so the same least squares on (1/n, 1/T) gives
  a = (1 - p)/T1 and b = p/T1, hence T1 = 1/(a + b) and p = b/(a + b). The marginal gain is
  dT/dn = T1*p / ((1 - p)*n + p)^2, which falls monotonically, so the knee where it drops
  to a threshold theta solves exactly: n* = (sqrt(T1*p/theta) - p) / (1 - p). The fewest
  cores meeting a floor F solve T(n) >= F: n >= p / (T1/F - (1 - p)), which has a solution
  only when F is below the asymptote T1 / (1 - p).
* **Ledger bytes over a horizon are the integral of the rate.** With b bytes per job and a
  job rate r(t) = r0 + r1*t per day, the bytes after H days are the integral from 0 to H of
  b*r(t) dt = b*(r0*H + r1*H^2/2).

Pure: no I/O, no clock (the methods are on a class with an interface beside it, ADR-0016).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

try:
    from scripts.interfaces.requirements_math_interface import RequirementsMathInterface
except ModuleNotFoundError:  # Direct execution keeps the script directory on sys.path.
    from interfaces.requirements_math_interface import (  # type: ignore[import-not-found,no-redef]
        RequirementsMathInterface,
    )


@dataclass(frozen=True)
class LinearFit:
    """y = intercept + slope * x, and how well it fits the points it came from."""

    intercept: float
    slope: float
    r2: float
    residuals: tuple[float, ...]

    def at(self, x: float) -> float:
        return self.intercept + self.slope * x

    def solve(self, y: float) -> float:
        """The x at which the line reaches y (the inverse of `at`)."""
        if self.slope == 0:
            raise ValueError("a flat line reaches no other value")
        return (y - self.intercept) / self.slope

    @property
    def max_abs_residual(self) -> float:
        return max((abs(r) for r in self.residuals), default=0.0)


@dataclass(frozen=True)
class AmdahlFit:
    """T(n) = t1 / ((1 - p) + p / n): single-core rate t1, parallel fraction p."""

    t1: float
    p: float
    r2: float
    residuals: tuple[float, ...]

    def rate(self, n: float) -> float:
        return self.t1 / ((1 - self.p) + self.p / n)

    def marginal(self, n: float) -> float:
        """dT/dn, in closed form."""
        return self.t1 * self.p / ((1 - self.p) * n + self.p) ** 2

    @property
    def asymptote(self) -> float:
        """The rate as n grows without bound: t1 / (1 - p), infinite when p is 1."""
        return math.inf if self.p >= 1 else self.t1 / (1 - self.p)


class RequirementsMath(RequirementsMathInterface):
    """Closed-form fits and solutions. Every method raises ValueError on inputs it cannot
    fit, rather than returning a number the data does not support."""

    @staticmethod
    def _r2(observed: Sequence[float], predicted: Sequence[float]) -> float:
        mean = sum(observed) / len(observed)
        total = sum((y - mean) ** 2 for y in observed)
        residual = sum((y - f) ** 2 for y, f in zip(observed, predicted, strict=True))
        if total == 0:
            return 1.0 if residual == 0 else 0.0
        return 1 - residual / total

    def least_squares(self, xs: Sequence[float], ys: Sequence[float]) -> LinearFit:
        if len(xs) != len(ys):
            raise ValueError("x and y differ in length")
        if len(xs) < 2:
            raise ValueError("a line needs at least two points")
        n = len(xs)
        mean_x, mean_y = sum(xs) / n, sum(ys) / n
        sxx = sum((x - mean_x) ** 2 for x in xs)
        if sxx == 0:
            raise ValueError("every x is the same, so no slope can be fitted")
        sxy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
        slope = sxy / sxx
        intercept = mean_y - slope * mean_x
        predicted = [intercept + slope * x for x in xs]
        return LinearFit(
            intercept=intercept,
            slope=slope,
            r2=self._r2(ys, predicted),
            residuals=tuple(y - f for y, f in zip(ys, predicted, strict=True)),
        )

    def amdahl(self, cores: Sequence[float], rates: Sequence[float]) -> AmdahlFit:
        if len(cores) < 3:
            raise ValueError("Amdahl's two parameters need at least three core counts")
        if any(n <= 0 for n in cores) or any(t <= 0 for t in rates):
            raise ValueError("core counts and rates must be positive")
        line = self.least_squares([1 / n for n in cores], [1 / t for t in rates])
        a, b = line.intercept, line.slope
        if a + b <= 0:
            raise ValueError("the fitted single-core time is not positive")
        t1, p = 1 / (a + b), b / (a + b)
        if not 0 <= p <= 1:
            raise ValueError(f"the fitted parallel fraction {p:.3f} is outside [0, 1]")
        fit = AmdahlFit(t1=t1, p=p, r2=0.0, residuals=())
        predicted = [fit.rate(n) for n in cores]
        return AmdahlFit(
            t1=t1,
            p=p,
            r2=self._r2(rates, predicted),
            residuals=tuple(t - f for t, f in zip(rates, predicted, strict=True)),
        )

    def knee(self, fit: AmdahlFit, threshold: float) -> float:
        if threshold <= 0:
            raise ValueError("the knee threshold must be positive")
        if fit.p <= 0:
            return 1.0  # no core after the first adds anything
        if fit.p >= 1:
            return math.inf  # linear scaling: the marginal gain never falls
        n = (math.sqrt(fit.t1 * fit.p / threshold) - fit.p) / (1 - fit.p)
        return max(1.0, n)

    def cores_for_rate(self, fit: AmdahlFit, floor: float) -> int | None:
        if floor <= fit.t1:
            return 1
        gap = fit.t1 / floor - (1 - fit.p)
        if gap <= 1e-12:  # rounding must not turn the asymptote itself into a core count
            return None  # the floor is at or above the asymptote t1 / (1 - p)
        return max(1, math.ceil(fit.p / gap - 1e-9))

    def integral_of_linear_rate(
        self, per_unit: float, rate0: float, rate1: float, horizon: float
    ) -> float:
        if horizon < 0:
            raise ValueError("the horizon cannot be negative")
        return per_unit * (rate0 * horizon + rate1 * horizon**2 / 2)
