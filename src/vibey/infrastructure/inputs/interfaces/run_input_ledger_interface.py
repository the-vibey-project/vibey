# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract of the run input ledger adapter, beside its class (ADR-0016).

Mirrors `infrastructure/inputs/run_input_ledger.py`. The runtime seam the run inputs service
consumes is `application/interfaces/run_input_ledger_interface.py::RunInputLedgerInterface`; it
is restated here with what the Postgres adapter promises. Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vibey.application.interfaces.run_input_ledger_interface import RunInputLedgerInterface


@runtime_checkable
class PostgresRunInputLedgerInterface(RunInputLedgerInterface, Protocol):
    """`RunInputLedgerInterface` over the one append-only event log: each event is appended as
    phase BUILD, with the given job id (none for an add), no engine and no causing run, provenance `trusted` (vibey wrote
    it), under the project's delivery correlation id. An event kind the ledger does not know is
    a `ValueError`, never a silently dropped record."""
