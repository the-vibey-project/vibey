# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Feasibility over the six-materials state vector (#134; docs/paper.md, "six materials,
three properties").

The paper postulates that every dilemma in software delivery decomposes into six raw
materials -- network, hardware, software, agent, information, agency -- each carrying
three properties -- availability, stability, reliability. That is a state `x` of eighteen
coordinates, and an operation `o` with requirement vector `r_o` is feasible exactly when
`x ⪰ r_o`. This module is that sentence as code, with three things the paper leaves
implicit made explicit:

**Unknown is a value.** A coordinate nobody measured is not zero and not one; it is
`None`, carrying where it would have come from. Feasibility is therefore three-valued:
`no` as soon as one MEASURED coordinate falls short, `yes` only when every required one
is measured and meets its minimum, and `unknown` in between. An unmeasured coordinate can
lower confidence; it can never manufacture a `yes` (doctrine 10).

**The path, not the step.** A run that dies at stage seven wasted stages one through six,
so an operation is judged against every stage it must pass. The nine stages below are the
default path, and each declares its requirement vector as data an adopter can replace.

**Agency first.** A run that cannot merge is infeasible however healthy the hardware, and
that was the common killer when this was written. Shortfalls are therefore reported with
agency ahead of everything else, and which materials lead is configurable.

Defaulted decisions, recorded where they bind (#134 was opened while the operator was
away; each is overridable and listed in the pull request):

- coordinates are on a 0..1 scale where **1 is peak** -- `x* = 1`, so the dilemma
  coordinate is `d = 1 - x`;
- **φ is unspecified**: the dilation each shortfall imposes on duration is not measured
  yet, so nothing here computes `T(o)` or the repair gradient `-∇_d T`; the report says
  so rather than presenting a heuristic ordering as a gradient;
- **paid credit is agency** -- permission to act by spending -- not hardware or software;
- stability and reliability are **not gated** by the default stages: a shortfall there
  dilates duration through φ rather than making work impossible, and φ is unspecified.

Nothing here performs I/O. Coordinates arrive already measured; this module only judges
them.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from vibey_gh.config import EstimateConfig
from vibey_gh.interfaces.feasibility_evaluator_interface import FeasibilityEvaluatorInterface
from vibey_gh.interfaces.pipeline_interface import PipelineInterface

__all__ = [
    "DEFAULT_MINIMUM",
    "DEFAULT_REPORT_FIRST",
    "DEFAULT_STAGES",
    "MATERIALS",
    "MEASURED_BY",
    "NO",
    "PEAK",
    "PROPERTIES",
    "STAGE_NAMES",
    "UNKNOWN",
    "YES",
    "Coordinate",
    "FeasibilityEvaluator",
    "Gap",
    "Pipeline",
    "PipelineVerdict",
    "Requirement",
    "Stage",
    "StageVerdict",
    "StateVector",
]

# The paper's table, in the paper's order.
MATERIALS = ("network", "hardware", "software", "agent", "information", "agency")
PROPERTIES = ("availability", "stability", "reliability")

# 1 is long-term stable peak performance, so the dilemma vector is `d = PEAK - x`.
PEAK = 1.0

YES = "yes"
NO = "no"
UNKNOWN = "unknown"

# What a required coordinate must reach unless a stage says otherwise: present in full.
DEFAULT_MINIMUM = 1.0
DEFAULT_REPORT_FIRST = ("agency",)

# Where each coordinate would be read from. An unmeasured coordinate carries this as its
# source, so "unknown" always says what measuring it would take -- and the decision that
# paid credit is AGENCY (permission to act by spending), not hardware, lives in its row.
MEASURED_BY: Mapping[tuple[str, str], str] = {
    ("network", "availability"): "reachability of every endpoint the stage needs",
    ("network", "stability"): "variance of reachability and latency over time",
    ("network", "reliability"): "whether the network delivers what it claims (loss, corruption)",
    ("hardware", "availability"): (
        "the fit calculus: whether this machine's memory and paging can host the local model"
    ),
    ("hardware", "stability"): "drift in free memory, paging pressure and thermals over time",
    ("hardware", "reliability"): "whether the machine computes correctly (faults, wear)",
    ("software", "availability"): (
        "the fit calculus: whether the local runner holds the model; tool versions against pins"
    ),
    ("software", "stability"): "version and configuration drift",
    ("software", "reliability"): "whether the software behaves as specified",
    ("agent", "availability"): "a model or a human present to act, and their load",
    ("agent", "stability"): "turnover, fatigue and load over time",
    ("agent", "reliability"): "historical success rate when acting",
    ("information", "availability"): "required inputs at hand: specification, docs, credentials",
    ("information", "stability"): "staleness and drift of those inputs",
    ("information", "reliability"): "whether the inputs are true when consulted",
    ("agency", "availability"): (
        "permissions actually held: merge rights, token scopes, ruleset bypass, and paid"
        " credit — permission to act by spending is agency"
    ),
    ("agency", "stability"): "revocation risk of those permissions",
    ("agency", "reliability"): "whether each permission honours its grant when exercised",
}


@dataclass(frozen=True)
class Coordinate:
    """One material-property pair: a value on 0..1, or `None` for unknown, and its source.

    `measured_at` is seconds since the epoch when the reading was taken. It may be set on
    an unknown coordinate too: an attempt that yielded nothing still happened at a time.
    """

    material: str
    prop: str
    value: float | None
    source: str
    measured_at: float | None = None

    def __post_init__(self) -> None:
        if self.material not in MATERIALS:
            raise ValueError(f"{self.material!r} is not a material; the six are {MATERIALS}")
        if self.prop not in PROPERTIES:
            raise ValueError(f"{self.prop!r} is not a property; the three are {PROPERTIES}")
        if self.value is not None and not (math.isfinite(self.value) and 0.0 <= self.value <= PEAK):
            raise ValueError(f"{self.name} must be unknown or from 0 to 1: {self.value!r}")

    @property
    def name(self) -> str:
        return f"{self.material}.{self.prop}"

    @property
    def known(self) -> bool:
        return self.value is not None

    @property
    def distance(self) -> float | None:
        """This coordinate of the dilemma vector, `d = x* - x`, or `None` when unknown."""
        return None if self.value is None else round(PEAK - self.value, 6)


@dataclass(frozen=True)
class StateVector:
    """All eighteen coordinates, exactly once each, in the paper's order."""

    coordinates: tuple[Coordinate, ...]

    def __post_init__(self) -> None:
        names = [c.name for c in self.coordinates]
        expected = [f"{m}.{p}" for m in MATERIALS for p in PROPERTIES]
        if sorted(names) != sorted(expected):
            raise ValueError("a state vector holds each of the eighteen coordinates exactly once")
        order = {name: index for index, name in enumerate(expected)}
        object.__setattr__(
            self, "coordinates", tuple(sorted(self.coordinates, key=lambda c: order[c.name]))
        )

    @classmethod
    def unknown(cls, measured_at: float | None = None) -> StateVector:
        """Every coordinate unknown, each naming what would measure it."""
        return cls(
            tuple(
                Coordinate(
                    material=m,
                    prop=p,
                    value=None,
                    source=f"unmeasured — would come from {MEASURED_BY[(m, p)]}",
                    measured_at=measured_at,
                )
                for m in MATERIALS
                for p in PROPERTIES
            )
        )

    def get(self, material: str, prop: str) -> Coordinate:
        for coordinate in self.coordinates:
            if coordinate.material == material and coordinate.prop == prop:
                return coordinate
        raise KeyError(f"{material}.{prop}")

    def with_measurements(self, measurements: Iterable[Coordinate]) -> StateVector:
        """This state with each given coordinate replacing its unknown (or older) reading."""
        replacing = {c.name: c for c in measurements}
        return StateVector(tuple(replacing.get(c.name, c) for c in self.coordinates))

    @property
    def measured(self) -> int:
        return sum(1 for c in self.coordinates if c.known)

    @property
    def confidence(self) -> float:
        """The fraction of the eighteen that were actually measured."""
        return round(self.measured / len(self.coordinates), 4)


@dataclass(frozen=True)
class Requirement:
    """A stage needs this coordinate to reach at least `minimum` (0..1, 1 is peak)."""

    material: str
    prop: str
    minimum: float = DEFAULT_MINIMUM

    def __post_init__(self) -> None:
        # A requirement names a real coordinate or it constrains nothing; building a
        # throwaway Coordinate reuses its vocabulary check instead of repeating it.
        Coordinate(self.material, self.prop, self.minimum, source="requirement")

    @property
    def name(self) -> str:
        return f"{self.material}.{self.prop}"

    @classmethod
    def parse(cls, coordinate: str, minimum: float = DEFAULT_MINIMUM) -> Requirement:
        """`"agency.availability"` and a minimum, as `[estimate.requirements]` writes them."""
        material, _, prop = coordinate.partition(".")
        return cls(material, prop, float(minimum))


@dataclass(frozen=True)
class Stage:
    """One step of the pipeline and the requirement vector `r` it places on the state."""

    name: str
    requirements: tuple[Requirement, ...] = ()
    summary: str = ""

    @classmethod
    def needing(cls, name: str, summary: str, *materials: str) -> Stage:
        """A stage that needs each named material fully available, and nothing else."""
        return cls(name, tuple(Requirement(m, "availability") for m in materials), summary)


# The pipeline #134 names, install through main-validation, and what each stage draws on.
# DATA, not law: `[estimate] stages` and `[estimate.requirements.<stage>]` replace any of
# it. Only availability is gated, for the reason the module docstring gives.
DEFAULT_STAGES: tuple[Stage, ...] = (
    Stage.needing(
        "install",
        "fetch the toolchain onto a machine that can host it, with permission to write it",
        "network",
        "hardware",
        "software",
        "agency",
    ),
    Stage.needing(
        "interview",
        "the operator and the design model, the ask, and the runner that serves the model",
        "agent",
        "information",
        "software",
    ),
    Stage.needing(
        "feature-branch",
        "build against the accepted specification and push a branch",
        "agent",
        "information",
        "hardware",
        "software",
        "agency",
    ),
    Stage.needing(
        "develop",
        "reviewed work merged into the integration branch",
        "agent",
        "network",
        "hardware",
        "software",
        "agency",
    ),
    Stage.needing(
        "develop-deployment",
        "deploy the integration branch with credentials that permit it",
        "network",
        "software",
        "agency",
    ),
    Stage.needing(
        "develop-validation",
        "check the deployment against its acceptance criteria",
        "agent",
        "information",
        "network",
    ),
    Stage.needing(
        "main",
        "promote the integration branch to the release branch: merge rights",
        "network",
        "agency",
    ),
    Stage.needing(
        "main-deployment",
        "deploy the release branch with credentials that permit it",
        "network",
        "software",
        "agency",
    ),
    Stage.needing(
        "main-validation",
        "check the release against its acceptance criteria",
        "agent",
        "information",
        "network",
    ),
)
STAGE_NAMES = tuple(stage.name for stage in DEFAULT_STAGES)


@dataclass(frozen=True)
class Gap:
    """A required coordinate that is either measured short (`no`) or unmeasured
    (`unknown`) at one stage."""

    stage: str
    material: str
    prop: str
    minimum: float
    value: float | None
    source: str

    @property
    def name(self) -> str:
        return f"{self.material}.{self.prop}"

    @property
    def verdict(self) -> str:
        return UNKNOWN if self.value is None else NO

    def describe(self) -> str:
        reading = "unknown" if self.value is None else f"{self.value:g}"
        return f"{self.name} {reading} < {self.minimum:g} at '{self.stage}' ({self.source})"


@dataclass(frozen=True)
class StageVerdict:
    stage: str
    verdict: str
    gaps: tuple[Gap, ...] = ()


@dataclass(frozen=True)
class PipelineVerdict:
    """The whole path judged: the verdict, where it first fails, and why."""

    verdict: str
    stages: tuple[StageVerdict, ...]
    blocked_at: str | None
    shortfalls: tuple[Gap, ...]
    unknowns: tuple[Gap, ...]
    required: int
    required_measured: int

    @property
    def confidence(self) -> float:
        """The fraction of the coordinates this path requires that were measured. A path
        that requires nothing is judged on nothing unknown, so it is fully confident."""
        if not self.required:
            return 1.0
        return round(self.required_measured / self.required, 4)


class Pipeline(PipelineInterface):
    """The ordered stages a run passes through. Nine by default; any order and any
    requirement vectors an adopter declares instead."""

    def __init__(self, stages: Sequence[Stage] = DEFAULT_STAGES) -> None:
        names = [stage.name for stage in stages]
        if not names or any(not name.strip() for name in names):
            raise ValueError("a pipeline needs at least one stage, and every stage a name")
        if len(set(names)) != len(names):
            raise ValueError(f"stage names must be unique: {names}")
        self._stages = tuple(stages)

    @classmethod
    def from_config(cls, config: EstimateConfig) -> Pipeline:
        """The pipeline `[estimate]` describes: its `stages` order (the defaults when
        empty), each stage's vector replaced by `[estimate.requirements.<stage>]` when that
        table exists. A stage with neither a default nor a table is refused by name, as is
        a table for a stage the pipeline never reaches -- silently ignoring either would
        let a typo change the verdict."""
        defaults = {stage.name: stage for stage in DEFAULT_STAGES}
        declared = {
            name: Stage(
                name,
                tuple(Requirement.parse(c, m) for c, m in needs),
                f"as declared in [estimate.requirements.{name}]",
            )
            for name, needs in config.requirements
        }
        order = config.stages or STAGE_NAMES
        stages: list[Stage] = []
        for name in order:
            if name in declared:
                stages.append(declared[name])
            elif name in defaults:
                stages.append(defaults[name])
            else:
                raise ValueError(
                    f"[estimate] stage {name!r} has no requirement vector: add"
                    f" [estimate.requirements.{name}] or use one of {STAGE_NAMES}"
                )
        stray = sorted(set(declared) - set(order))
        if stray:
            raise ValueError(
                f"[estimate.requirements] names stage(s) the pipeline never reaches: {stray}"
            )
        return cls(stages)

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(stage.name for stage in self._stages)

    def path(self, operation: str, start: str | None = None) -> tuple[Stage, ...]:
        names = self.names
        first = names[0] if start is None else start
        for name in (operation, first):
            if name not in names:
                raise ValueError(f"{name!r} is not a stage; the stages are {', '.join(names)}")
        begin, end = names.index(first), names.index(operation)
        if begin > end:
            raise ValueError(f"'{first}' comes after '{operation}' in the pipeline")
        return self._stages[begin : end + 1]


class FeasibilityEvaluator(FeasibilityEvaluatorInterface):
    """`x ⪰ r` at every stage of a path, three-valued, shortfalls in priority order.

    `report_first` names the materials whose gaps lead the report, in that order; every
    other gap follows in pipeline order, then in the paper's material and property order.
    """

    def __init__(self, *, report_first: Sequence[str] = DEFAULT_REPORT_FIRST) -> None:
        unknown = [m for m in report_first if m not in MATERIALS]
        if unknown:
            raise ValueError(f"report_first names no such material: {unknown}; see {MATERIALS}")
        self._first = tuple(report_first)

    def evaluate(self, state: StateVector, stages: Sequence[Stage]) -> PipelineVerdict:
        judged: list[StageVerdict] = []
        order = {stage.name: index for index, stage in enumerate(stages)}
        # Distinct coordinates, not requirement instances: agency needed at five stages is
        # one unknown to measure, not five, and confidence should say so.
        required: set[str] = set()
        measured: set[str] = set()
        for stage in stages:
            gaps: list[Gap] = []
            for need in stage.requirements:
                reading = state.get(need.material, need.prop)
                required.add(reading.name)
                if reading.known:
                    measured.add(reading.name)
                if reading.value is not None and reading.value >= need.minimum:
                    continue
                gaps.append(
                    Gap(
                        stage=stage.name,
                        material=need.material,
                        prop=need.prop,
                        minimum=need.minimum,
                        value=reading.value,
                        source=reading.source,
                    )
                )
            judged.append(
                StageVerdict(stage.name, self._combine(g.verdict for g in gaps), tuple(gaps))
            )
        gaps = [gap for verdict in judged for gap in verdict.gaps]
        ranked = sorted(gaps, key=lambda gap: self._rank(gap, order))
        blocked = next((v.stage for v in judged if v.verdict == NO), None)
        return PipelineVerdict(
            verdict=self._combine(v.verdict for v in judged),
            stages=tuple(judged),
            blocked_at=blocked,
            shortfalls=tuple(g for g in ranked if g.verdict == NO),
            unknowns=tuple(g for g in ranked if g.verdict == UNKNOWN),
            required=len(required),
            required_measured=len(measured),
        )

    @staticmethod
    def _combine(verdicts: Iterable[str]) -> str:
        """Kleene's AND: one `no` decides it, any `unknown` withholds a `yes`."""
        seen = set(verdicts)
        if NO in seen:
            return NO
        return UNKNOWN if UNKNOWN in seen else YES

    def _rank(self, gap: Gap, order: Mapping[str, int]) -> tuple[int, int, int, int]:
        lead = self._first.index(gap.material) if gap.material in self._first else len(self._first)
        return (lead, order[gap.stage], MATERIALS.index(gap.material), PROPERTIES.index(gap.prop))
