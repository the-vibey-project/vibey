# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for the ledger's derived hash chain.

Mirrors `vibey/domain/ledger_chain.py` (ADR-0016). Interfaces declare; they never
consume. The ledger types the seam is declared over are imported under
TYPE_CHECKING only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from uuid import UUID

    from vibey.domain.ledger import LedgerEvent
    from vibey.domain.ledger_chain import ChainFindingKind


@runtime_checkable
class ChainLinkInterface(Protocol):
    """The link computed for one event."""

    @property
    def seq(self) -> int: ...

    @property
    def event_id(self) -> UUID: ...

    @property
    def link(self) -> str:
        """SHA-256 hex over the previous link and every stored field of the event."""
        ...


@runtime_checkable
class ChainFindingInterface(Protocol):
    """One disagreement a walk found, at the seq where it found it."""

    @property
    def kind(self) -> ChainFindingKind: ...

    @property
    def seq(self) -> int: ...

    @property
    def detail(self) -> str:
        """A plain sentence naming what disagreed with what."""
        ...


@runtime_checkable
class ChainVerificationInterface(Protocol):
    """The outcome of one walk."""

    @property
    def project_id(self) -> UUID: ...

    @property
    def start(self) -> str:
        """The link the walk began from."""
        ...

    @property
    def head(self) -> str:
        """The link after the last event walked."""
        ...

    @property
    def links(self) -> tuple[ChainLinkInterface, ...]: ...

    @property
    def findings(self) -> tuple[ChainFindingInterface, ...]: ...

    @property
    def ok(self) -> bool:
        """True when nothing disagreed."""
        ...


@runtime_checkable
class LedgerChainInterface(Protocol):
    """Computes a project's chain and verifies events against it."""

    @property
    def scheme(self) -> str:
        """The domain-separation tag folded into every hash."""
        ...

    def genesis(self, project_id: UUID) -> str:
        """The link before seq 1."""
        ...

    def link(self, prev_link: str, event: LedgerEvent) -> str:
        """The link for `event`, given the one before it."""
        ...

    def verify(
        self,
        project_id: UUID,
        events: Sequence[LedgerEvent],
        *,
        prev_link: str | None = ...,
        anchors: Mapping[int, str] = ...,
    ) -> ChainVerificationInterface:
        """Walk `events` in seq order; report every disagreement, not the first."""
        ...
