# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What `vibey loops` reports, assembled from data vibey already holds.

The family runs exactly two loops (sub-doctrine 8.c): `sovereignloop`, driving what runs on
the operator's own hardware, and `paidloop`, driving every paid engine. Canon 8.b makes the
sovereign loop the default and the paid loop declared-only, with Claude through claudeloop
as the paid default. That is the canon, reported as such: vibey's selector does not read a
paid declaration yet, and today picks a paid engine, by weighted round robin, whenever no
local engine is eligible. Each engine sits in the loop of its descriptor's tier -- reported
as the code says, and noted where the canon says otherwise. An engine the canon repeals
stays listed, and is left out of every by-effort view, so nothing selects it from there.

For every engine this lists all five efforts with the argv the engine passes, the effort it
really achieves, and the model: the value of a `--model` it passes, else the model vibey
hands it, else nothing -- and then the reason names what chooses it. Nothing here reads a
database, a network or a clock, so it answers on a machine with no PostgreSQL.
"""

from collections.abc import Mapping, Sequence
from types import MappingProxyType
from typing import Final

from vibey.application.dto import (
    EffortChoice,
    EffortLadder,
    EffortRun,
    EngineContext,
    LoopEngine,
    LoopsReport,
    LoopView,
)
from vibey.application.interfaces.loops import LoopCatalogInterface
from vibey.domain.effort import (
    BUILD_LADDER,
    BUILD_LADDER_EXHAUSTED,
    PHASE_BASE_EFFORT,
    Effort,
    forces_rotation,
)
from vibey.domain.engine import (
    DEFAULT_LOOP,
    LOOP_BY_TIER,
    PAID_DEFAULT_ENGINE,
    RENAMED_ENGINES,
    REPEALED_FROM_LOOPS,
    EngineDescriptor,
    Loop,
)
from vibey.domain.phase import Phase

MODEL_FLAG: Final = "--model"
"""The flag whose value names the model an effort runs."""
PRESET_FLAG: Final = "--preset"
"""claudeloop's and agyloop's model tier (`low`, `medium`, `high`)."""
PROFILE_FLAG: Final = "--profile"
"""claudeloop's backend profile, which maps each preset onto a model of its own."""


class LoopCatalog:
    """Assembles the two loops, their engines at every effort, and the ladder."""

    def __init__(
        self,
        *,
        efforts: Sequence[Effort] = tuple(Effort),
        phase_base: Mapping[Phase, Effort] = PHASE_BASE_EFFORT,
        build_ladder: Sequence[Effort] = BUILD_LADDER,
        exhausted_after: int = BUILD_LADDER_EXHAUSTED,
    ) -> None:
        self._efforts = tuple(efforts)
        self._phase_base = phase_base
        self._build_ladder = tuple(build_ladder)
        self._exhausted_after = exhausted_after

    def report(self, engines: Sequence[EngineContext]) -> LoopsReport:
        order = (DEFAULT_LOOP, *(loop for loop in Loop if loop is not DEFAULT_LOOP))
        return LoopsReport(
            efforts=self._efforts,
            default_loop=DEFAULT_LOOP,
            paid_default_engine=PAID_DEFAULT_ENGINE,
            ladder=self._ladder(),
            loops=tuple(self._loop(loop, engines) for loop in order),
        )

    def _ladder(self) -> EffortLadder:
        rises = [(low, high) for low in self._efforts for high in self._efforts if high > low]
        return EffortLadder(
            phase_base=self._phase_base,
            build_attempts=self._build_ladder,
            exhausted_after=self._exhausted_after,
            rotates_when_effort_rises=all(forces_rotation(low, high) for low, high in rises),
        )

    def _loop(self, loop: Loop, engines: Sequence[EngineContext]) -> LoopView:
        (tier,) = (tier for tier, held_by in LOOP_BY_TIER.items() if held_by is loop)
        held = tuple(
            self._engine(context)
            for context in engines
            if LOOP_BY_TIER[context.descriptor.tier] is loop
        )
        return LoopView(
            loop=loop,
            tier=tier,
            default=loop is DEFAULT_LOOP,
            # Canon 8.b: everything but the sovereign default is reached only by declaration.
            # The selector does not read a declaration yet; this reports the canon.
            declared_only=loop is not DEFAULT_LOOP,
            engines=held,
            by_effort=self._by_effort(tuple(engine for engine in held if not engine.repealed)),
        )

    def _engine(self, context: EngineContext) -> LoopEngine:
        descriptor = context.descriptor
        repealed = descriptor.engine_id in REPEALED_FROM_LOOPS
        notes: tuple[str, ...] = ()
        if repealed:
            notes = (
                f"sub-doctrine 8.b repeals {descriptor.engine_id.value} from both loops; "
                f"reported here as its descriptor says, tier {descriptor.tier.value}",
            )
        renamed = RENAMED_ENGINES.get(descriptor.engine_id)
        if renamed is not None:
            notes = (*notes, renamed)
        return LoopEngine(
            descriptor=descriptor,
            enabled=context.enabled,
            switch=context.switch,
            on_by_default=context.on_by_default,
            default_model=context.model,
            efforts=tuple(
                self._effort(descriptor, effort, context.model) for effort in self._efforts
            ),
            run=context.run,
            repealed=repealed,
            notes=notes,
        )

    def _effort(
        self, descriptor: EngineDescriptor, effort: Effort, chosen_model: str | None
    ) -> EffortRun:
        invocation = descriptor.invoke(effort)
        model = self._value_of(invocation.argv, MODEL_FLAG) or chosen_model
        chosen_by = None if model is not None else self._chooser(descriptor, invocation.argv)
        return EffortRun(
            effort=effort,
            argv=invocation.argv,
            achieved=invocation.achieved,
            model=model,
            chosen_by=chosen_by,
            notes="; ".join(note for note in (invocation.notes, chosen_by) if note),
        )

    def _chooser(self, descriptor: EngineDescriptor, argv: Sequence[str]) -> str:
        """What picks the model when nothing in vibey names it."""
        preset = self._value_of(argv, PRESET_FLAG)
        profile = self._value_of(argv, PROFILE_FLAG)
        if preset is None:
            return f"{descriptor.binary}'s own configuration chooses the model"
        if profile is None:
            return f"{descriptor.binary} preset {preset}"
        return f"{descriptor.binary} profile {profile}, preset {preset}"

    @staticmethod
    def _value_of(argv: Sequence[str], flag: str) -> str | None:
        """The argument after `flag`, or None when `flag` is absent or ends the argv."""
        for index, token in enumerate(argv[:-1]):
            if token == flag:
                return argv[index + 1]
        return None

    def _by_effort(
        self, engines: Sequence[LoopEngine]
    ) -> Mapping[Effort, tuple[EffortChoice, ...]]:
        """For each effort, every engine: those achieving exactly it first, then higher, then
        lower; ties by output price, then engine id."""
        view: dict[Effort, tuple[EffortChoice, ...]] = {}
        for index, effort in enumerate(self._efforts):
            runs = sorted(
                ((engine, engine.efforts[index]) for engine in engines),
                key=lambda pair: (
                    self._distance(pair[1].achieved, effort),
                    pair[0].descriptor.cost_per_mtok_out,
                    pair[0].descriptor.engine_id.value,
                ),
            )
            view[effort] = tuple(
                EffortChoice(engine.descriptor.engine_id, run.model, run.achieved)
                for engine, run in runs
            )
        return MappingProxyType(view)

    @staticmethod
    def _distance(achieved: Effort, wanted: Effort) -> int:
        if achieved == wanted:
            return 0
        return 1 if achieved > wanted else 2


LOOP_CATALOG: Final[LoopCatalogInterface] = LoopCatalog()
"""The catalog `vibey loops` asks. Annotated with the interface so `mypy --strict` checks the
class against its declared seam."""
