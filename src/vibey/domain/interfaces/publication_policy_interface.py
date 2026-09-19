# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts for the publication policy: what of the ledger the public may see.

Mirrors `vibey/domain/publication_policy.py` (ADR-0016). Interfaces declare; they
never consume. The domain types the seams are declared over are imported under
TYPE_CHECKING only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from uuid import UUID

    from vibey.domain.ledger import EventKind, LedgerEvent, Provenance
    from vibey.domain.publication_policy import WithheldReason


@runtime_checkable
class CredentialRedactorInterface(Protocol):
    """Replaces credential-shaped values in a payload. Pure: no I/O.

    The domain declares the seam; `infrastructure/ledger/redact.py` fills it, so the
    credential patterns stay in one place and the policy can still run them last.
    """

    def redact(self, payload: Mapping[str, object]) -> Mapping[str, object]:
        """The payload with every credential replaced by a marker."""
        ...


@runtime_checkable
class PublicationRulesInterface(Protocol):
    """The data the policy applies. One place, so widening it is one change."""

    @property
    def allowed(self) -> Mapping[EventKind, frozenset[str]]:
        """The kinds that may be published, and the payload fields each may keep."""
        ...

    @property
    def chatter(self) -> frozenset[EventKind]:
        """Engine traffic -- prompts, model output, tool calls -- withheld whole."""
        ...

    @property
    def withheld_provenance(self) -> frozenset[Provenance]:
        """Provenances whose events are withheld whole."""
        ...

    @property
    def never_published(self) -> frozenset[str]:
        """Field names no rule set can publish, whatever `allowed` says."""
        ...

    @property
    def path_token(self) -> str:
        """What an absolute path in a published string becomes."""
        ...

    @property
    def email_token(self) -> str:
        """What an email address in a published string becomes."""
        ...

    @property
    def scheme(self) -> str:
        """The name of the policy family these rules belong to."""
        ...

    @property
    def fingerprint(self) -> str:
        """SHA-256 over every rule, so a shard names the exact rules that made it."""
        ...


@runtime_checkable
class TrimCountsInterface(Protocol):
    """What the policy removed from inside published records."""

    @property
    def fields(self) -> int:
        """Payload fields withheld: not allowlisted, never published, or keyed by a
        path or an address."""
        ...

    @property
    def paths(self) -> int:
        """Absolute paths replaced in published strings."""
        ...

    @property
    def emails(self) -> int:
        """Email addresses replaced in published strings."""
        ...

    @property
    def credentials(self) -> int:
        """Records the credential redactor changed."""
        ...

    @property
    def total(self) -> int:
        """All four, summed."""
        ...

    def plus(self, other: TrimCountsInterface) -> TrimCountsInterface:
        """The two counts added field by field."""
        ...


@runtime_checkable
class PublicationDecisionInterface(Protocol):
    """What the policy did with one event."""

    @property
    def record(self) -> LedgerEvent | None:
        """The event as published, or None when it was withheld."""
        ...

    @property
    def withheld(self) -> WithheldReason | None:
        """Why the event was withheld, or None when it was published."""
        ...

    @property
    def trim(self) -> TrimCountsInterface:
        """What was removed from inside the published record."""
        ...


@runtime_checkable
class PublicationOutcomeInterface(Protocol):
    """What the policy did with a ledger: the records, and a count of all it withheld."""

    @property
    def records(self) -> tuple[LedgerEvent, ...]:
        """The published records, in seq order."""
        ...

    @property
    def trims(self) -> Mapping[UUID, TrimCountsInterface]:
        """By event id, what was removed from each record the policy changed."""
        ...

    @property
    def withheld(self) -> Mapping[WithheldReason, int]:
        """Events withheld, by reason; every reason present, zero included."""
        ...

    @property
    def trimmed(self) -> TrimCountsInterface:
        """What was removed from inside published records, summed."""
        ...

    @property
    def events_withheld(self) -> int:
        """Events withheld for any reason."""
        ...


@runtime_checkable
class PublicationPolicyInterface(Protocol):
    """Projects ledger events onto what a public shard may carry."""

    @property
    def rules(self) -> PublicationRulesInterface: ...

    def decide(self, event: LedgerEvent) -> PublicationDecisionInterface:
        """Withhold the event, or publish what the rules allow of it."""
        ...

    def apply(self, events: Sequence[LedgerEvent]) -> PublicationOutcomeInterface:
        """Decide every event and count everything withheld."""
        ...
