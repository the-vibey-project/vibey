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

The caps themselves come from one place too: ``caps_from_config``. Issue
#210 was ``vibey cost`` reading a ``budget`` table that nothing writes and
printing $40 / $250 fallbacks as if they were caps, while the worker
enforced ``max_cycle_dollars`` from a second, private parse. Two readers of
one setting is how the report and the enforcement drift apart.
"""

from collections.abc import Mapping
from uuid import UUID

from vibey.application.interfaces import LedgerReader
from vibey.domain.budget import BudgetLedger
from vibey.domain.ledger import EventKind


class LedgerBudgetSource:
    """Declared by ``interfaces/budget_source_interface.py::LedgerBudgetSourceInterface``."""

    @staticmethod
    def caps_from_config(config: Mapping[str, object]) -> tuple[float | None, int | None]:
        """The brake's caps from a project's stored config: ``(max_dollars, max_turns)``.

        The keys are the top-level ``max_cycle_dollars`` / ``max_cycle_turns``
        that ``vibey new --max-cycle-dollars/--max-cycle-turns`` and the
        Kubernetes operator's ``spec.maxCycleDollars/maxCycleTurns`` write. A
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
    ) -> None:
        self._ledger_reader = ledger_reader
        self._max_turns = max_turns
        self._max_dollars = max_dollars

    async def current(self, project_id: UUID, cycle: int) -> BudgetLedger:
        dollars = 0.0
        turns = 0
        for event in await self._ledger_reader.all_for_project(project_id):
            if event.cycle != cycle:
                continue
            if event.kind is EventKind.TURN_COMPLETED:
                turns += 1
                raw_cost = event.payload.get("cost_usd", 0.0)
                if isinstance(raw_cost, int | float):
                    dollars += float(raw_cost)
            elif event.kind is EventKind.BUDGET_SPENT:
                raw_dollars = event.payload.get("dollars", 0.0)
                raw_turns = event.payload.get("turns", 0)
                if isinstance(raw_dollars, int | float):
                    dollars += float(raw_dollars)
                if isinstance(raw_turns, int):
                    turns += raw_turns
        return BudgetLedger(
            turns_spent=turns,
            dollars_spent=dollars,
            max_turns=self._max_turns,
            max_dollars=self._max_dollars,
        )
