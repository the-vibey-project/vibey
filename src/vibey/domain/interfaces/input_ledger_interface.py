# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam that holds a store's index rows to the ledger's record of adds (SP-LOOPS Phase 3c, fix
round 1: review I2, I3).

Implemented by `domain/input_ledger.py`. Interfaces declare; they never consume.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.domain.input_ledger import Reconciled, RecordedInputs
    from vibey.domain.run_input import RunInput


@runtime_checkable
class InputLedgerInterface(Protocol):
    def recorded(self, events: Iterable[tuple[int, Mapping[str, object]]]) -> RecordedInputs:
        """The adds a ledger records, from `(seq, payload)` pairs of its input events: each
        `vibey_run_input` add in `seq` order, less each add a later `vibey_run_input_failed`
        correction with the same digest, kind, size and name digest cancels (the latest such
        add before it). A payload that is not one of these, or is malformed, is ignored."""
        ...

    def reconcile(self, rows: Sequence[RunInput], recorded: RecordedInputs) -> Reconciled:
        """Matches index rows to recorded adds one to one: each add takes the first unused row
        with its digest, kind, size and (when the add records one) name digest. Adds with a
        name digest choose first, then adds recorded before names were; `given` is in ledger
        order either way. `given` is the matched rows in ledger order; `unrecorded` counts rows no add
        took; `missing` lists the adds no row matched."""
        ...
