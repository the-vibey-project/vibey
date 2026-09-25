# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Postgres-backed failover records (ADR-0070): `EngineFailedOver`, `EngineProbed` and
`EngineHandedBack`, each one trusted ledger event.

The ULTRA control store's transaction exactly -- lock the project's row
`FOR NO KEY UPDATE`, append on the same connection under the row's cycle and phase --
with its own three kinds; any other kind is refused before anything is opened.
"""

from typing import ClassVar, Final

from vibey.domain.ledger import EventKind
from vibey.infrastructure.db.ultra_control_store import PostgresUltraControlStore

FAILOVER_KINDS: Final = frozenset(
    {EventKind.ENGINE_FAILED_OVER, EventKind.ENGINE_PROBED, EventKind.ENGINE_HANDED_BACK}
)
"""The only kinds this store writes."""


class PostgresFailoverStore(PostgresUltraControlStore):
    """Declared by `interfaces/failover_store_interface.py`."""

    KINDS: ClassVar[frozenset[EventKind]] = FAILOVER_KINDS
    WHAT: ClassVar[str] = "a failover record"
