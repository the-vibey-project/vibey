# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for the runaway brake's ledger-backed spend source.

``BudgetSource`` (``interfaces/build.py``) is the narrow port the BUILD
handler consumes: "what has this cycle spent, against which caps". This
interface is the whole of ``application/budget_source.py``'s
``LedgerBudgetSource`` (ADR-0016's mirrored form): that port, plus the one
parser that turns a project's stored config into the caps. The worker that
enforces the brake and ``vibey cost`` that reports it both read through the
parser, so the cap a person is shown is the cap that is enforced.
"""

from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from vibey.application.interfaces.build import BudgetSource


@runtime_checkable
class LedgerBudgetSourceInterface(BudgetSource, Protocol):
    """A ``BudgetSource`` whose caps come from a project's stored config."""

    @staticmethod
    def caps_from_config(config: Mapping[str, object]) -> tuple[float | None, int | None]:
        """``(max_dollars, max_turns)`` from ``max_cycle_dollars`` /
        ``max_cycle_turns``. An absent or non-numeric value is no cap
        (``None``), never a default."""
        ...
