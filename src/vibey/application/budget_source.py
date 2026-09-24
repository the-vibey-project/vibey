# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The production BudgetSource: per-cycle spend summed from the ledger,
with the caps the project was configured with.

This is the runaway brake for unattended runs. The repair storms burned
real money precisely because nothing capped cycle spend -- every engine
session reports its cost into the ledger, so the ledger is the one
durable, replay-safe place to enforce a ceiling from.

Two event shapes carry spend, and both must count:

- TURN_COMPLETED: what the engines actually write. Each completed turn
  is one turn spent, and claudeloop-family engines attach the turn's
  real ``cost_usd``. The greeter4 live run proved this is the ONLY
  place real dollars land -- the brake was blind until it read them.
- BUDGET_SPENT with explicit ``dollars``/``turns``: the vendor-neutral
  shape (grant adjustments, replays, synthetic corrections). Production
  engine translation also maps capacity/usage chatter to BUDGET_SPENT
  with neither key; those sum as zero rather than erroring.

Which events are spend, and how much, is ``domain/phase_timing.py``'s
``LedgerSpendRule`` -- not a copy of it. The phase-timing projection and the
per-engine spend meter (``application/engine_selection.py``) apply the same
rule, so the brake, the per-visit spend of the phase timeline and the engine
health record's per-engine figure cannot disagree about what a dollar is
(issue #209, ADR-0017). One consequence is deliberate: a ``bool`` in a numeric field
(``cost_usd: true``, ``turns: true``) counts as nothing, where the brake's
old inline copy counted it as 1.

The caps themselves come from one place too: ``caps_from_config``. Issue
#210 was ``vibey cost`` reading a ``budget`` table that nothing writes and
printing $40 / $250 fallbacks as if they were caps, while the worker
enforced ``max_cycle_dollars`` from a second, private parse. Two readers of
one setting is how the report and the enforcement drift apart. And they are
read when the brake checks, not when the worker starts: a cap is something a
person changes (``vibey budget``), and a brake holding a copy from its start
would enforce a cap nobody has any longer.
"""

from collections.abc import Mapping
from uuid import UUID

from vibey.application.interfaces import LedgerReader, ProjectLookup
from vibey.domain.budget import BudgetLedger
from vibey.domain.interfaces.phase_timing_interface import (
    LedgerSpendRuleInterface,
    PhaseSpendInterface,
)
from vibey.domain.phase_timing import LEDGER_SPEND_RULE, NO_SPEND


class LedgerBudgetSource:
    """Declared by ``interfaces/budget_source_interface.py::LedgerBudgetSourceInterface``."""

    @staticmethod
    def caps_from_config(config: Mapping[str, object]) -> tuple[float | None, int | None]:
        """The brake's caps from a project's stored config: ``(max_dollars, max_turns)``.

        The keys are the top-level ``max_cycle_dollars`` / ``max_cycle_turns``
        that ``vibey new --max-cycle-dollars/--max-cycle-turns`` and the
        Kubernetes operator's ``spec.maxCycleDollars/maxCycleTurns`` write, and
        ``vibey budget set`` / ``clear`` change afterwards. A
        key that is absent or not a number is no cap (``None``) rather than a
        default: opting in to the brake is explicit, never a silent limit that
        would surprise an existing project.

        ``bool`` is rejected before the numeric check because
        ``isinstance(True, int)`` holds in Python, so a stored
        ``max_cycle_turns: true`` would otherwise be a cap of one turn. A
        legacy ``budget`` table (``max_dollars_per_cycle`` and friends) is not
        read: nothing enforces it, so showing it would be the #210 bug again.
        """
        raw_dollars = config.get("max_cycle_dollars")
        raw_turns = config.get("max_cycle_turns")
        max_dollars = (
            float(raw_dollars)
            if isinstance(raw_dollars, int | float) and not isinstance(raw_dollars, bool)
            else None
        )
        max_turns = (
            raw_turns if isinstance(raw_turns, int) and not isinstance(raw_turns, bool) else None
        )
        return max_dollars, max_turns

    def __init__(
        self,
        ledger_reader: LedgerReader,
        *,
        max_turns: int | None = None,
        max_dollars: float | None = None,
        spend_rule: LedgerSpendRuleInterface = LEDGER_SPEND_RULE,
        projects: ProjectLookup | None = None,
    ) -> None:
        """``max_turns`` / ``max_dollars`` are the caps this source was built with.

        With ``projects``, the caps are read instead from the project's stored
        config at every ``current()`` call -- the worker's brake is built that way,
        once, when the worker starts, so a cap ``vibey budget`` sets or clears while
        it runs binds the next BUILD session rather than the next restart, and a
        project created uncapped can be capped later. A project that is gone
        falls back to the caps given here.
        """
        self._ledger_reader = ledger_reader
        self._max_turns = max_turns
        self._max_dollars = max_dollars
        self._spend_rule = spend_rule
        self._projects = projects

    async def current(self, project_id: UUID, cycle: int) -> BudgetLedger:
        max_dollars, max_turns = await self._caps(project_id)
        spent: PhaseSpendInterface = NO_SPEND
        for event in await self._ledger_reader.all_for_project(project_id):
            if event.cycle != cycle:
                continue
            spend = self._spend_rule.spend_of(event)
            if spend is not None:
                spent = spent.plus(spend)
        # Every TurnCompleted event is one turn to the brake, as it always
        # was; phase_timing's caveat about that count applies here too.
        return BudgetLedger(
            turns_spent=spent.turn_completed_events + spent.budget_turns,
            dollars_spent=spent.dollars,
            max_turns=max_turns,
            max_dollars=max_dollars,
        )

    async def _caps(self, project_id: UUID) -> tuple[float | None, int | None]:
        if self._projects is not None:
            project = await self._projects.get(project_id)
            if project is not None:
                return self.caps_from_config(project.config)
        return self._max_dollars, self._max_turns
