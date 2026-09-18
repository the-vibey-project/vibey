# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The ledger's hash chain: tamper evidence derived from the rows, stored nowhere.

Each event's **link** is the SHA-256 of the link before it and every stored field
of the event: project, seq, event id, cycle, phase, kind, engine, job, causation,
correlation, provenance, the production instant in canonical UTC, and the payload
digest. The first event links from the project's **genesis**, a hash of the chain
scheme and the project id, so no two projects share a chain and no event can be
moved between them unnoticed. Changing any field of any event changes its link and
every link after it; changing a payload without its digest shows up as a digest
the payload no longer produces.

**Why derived and not a column.** The event table is append-only by `RULE ... DO
INSTEAD NOTHING` (migrations/0002_event.sql), so a migration that backfilled a
`prev_hash` column would be silently discarded, and a column written only by new
appends would leave every existing event outside the chain. A chain recomputed
from the rows covers all of history, needs no migration, and cannot drift from the
data it describes -- the cost is one pass over the events being checked.

**How the storage tiers fold over it (vibey#114).** A chunk covering seqs `a..b` is
identified by two links: the one before it (`link(a-1)`) and the one at its end
(`link(b)`). Verifying the chunk is a walk over the chunk alone --
``verify(project_id, chunk, prev_link=link(a-1), anchors={b: link(b)})`` -- with
nothing outside it decompressed. Because every link commits to the one before it,
an anchored newest link anchors the whole history behind it; a chunk manifest that
records the two links per chunk is the whole of the integration.

**Why not the family's chain.** `vibey_bootstrap.audit` ships a hash-chained audit
record (`AuditChain`, `verify_chain`), and ADR-0017 says use ours before writing
another. It cannot serve here, for two reasons, both capability gaps: `domain/` is
forbidden from importing `vibey_bootstrap` by name (`.importlinter`,
`domain-independence`), and `AuditChain` chains records it mints itself -- a fixed
seven-field schema, a `uuid4` id and a wall-clock timestamp per append, and a
stored `prev_hash` -- where this chain must be derived over rows that already
exist, start from an anchor mid-history, and report every mismatch rather than
return the first as `False`.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC
from enum import StrEnum
from hashlib import sha256
from operator import attrgetter
from types import MappingProxyType
from typing import Final
from uuid import UUID

from vibey.domain.interfaces.ledger_chain_interface import LedgerChainInterface
from vibey.domain.ledger import LedgerEvent, canonical_bytes, digest_event

CHAIN_SCHEME: Final = "vibey-ledger-chain/v1"
"""Folded into every hash so a link can never be mistaken for a hash of anything
else, and so a later scheme cannot collide with this one. A deployment that needs
a chain of its own passes another scheme to `LedgerChain` (ADR-0018)."""

_NO_ANCHORS: Final[Mapping[int, str]] = MappingProxyType({})


class ChainFindingKind(StrEnum):
    """Every way a walk can disagree with what it was given."""

    DIGEST_MISMATCH = "digest_mismatch"
    """The stored digest is not the digest of the stored payload."""
    FOREIGN_PROJECT = "foreign_project"
    """The event belongs to a different project than the chain being walked."""
    SEQ_DUPLICATE = "seq_duplicate"
    """Two events claim the same seq."""
    SEQ_GAP = "seq_gap"
    """Seqs skip; events are missing between two that are present."""
    UNANCHORED_WINDOW = "unanchored_window"
    """The walk starts after seq 1 with no link to start from, so it began at
    genesis and its links are not the ledger's own."""
    ANCHOR_MISMATCH = "anchor_mismatch"
    """A link the caller already trusts differs from the recomputed one."""
    ANCHOR_UNREACHED = "anchor_unreached"
    """The caller trusts a link at a seq the walk never reached, so it was not
    checked -- reported rather than silently passed."""


@dataclass(frozen=True, slots=True)
class ChainLink:
    """The link computed for one event."""

    seq: int
    event_id: UUID
    link: str


@dataclass(frozen=True, slots=True)
class ChainFinding:
    """One disagreement, at the seq where it was found."""

    kind: ChainFindingKind
    seq: int
    detail: str


@dataclass(frozen=True, slots=True)
class ChainVerification:
    """The outcome of one walk: every link, every finding, and the two ends."""

    project_id: UUID
    start: str
    """The link the walk began from: the project's genesis, or `prev_link`."""
    head: str
    """The link after the last event walked; `start` when there were none."""
    links: tuple[ChainLink, ...]
    findings: tuple[ChainFinding, ...]

    @property
    def ok(self) -> bool:
        """Nothing disagreed. Says nothing about events that were not given."""
        return not self.findings


class LedgerChain:
    """Computes and verifies a project's hash chain. Stateless beyond its scheme."""

    def __init__(self, scheme: str = CHAIN_SCHEME) -> None:
        self._scheme = scheme

    @property
    def scheme(self) -> str:
        """The domain-separation tag folded into every hash."""
        return self._scheme

    def genesis(self, project_id: UUID) -> str:
        """The link before seq 1: the scheme and the project, and nothing else."""
        return self._hash({"scheme": self._scheme, "genesis": str(project_id)})

    def link(self, prev_link: str, event: LedgerEvent) -> str:
        """The link for `event`, given the link before it.

        Raises `ValueError` for a naive `produced_at`: there is no canonical UTC
        form of an instant whose zone is unknown, and guessing one would make the
        link depend on the machine computing it.
        """
        offset = event.produced_at.utcoffset()
        if offset is None:
            raise ValueError(
                f"event seq {event.seq} has a naive produced_at "
                f"({event.produced_at.isoformat()}); a link needs a real instant"
            )
        instant = event.produced_at.astimezone(UTC).isoformat(timespec="microseconds")
        return self._hash(
            {
                "scheme": self._scheme,
                "prev": prev_link,
                "project_id": str(event.project_id),
                "seq": event.seq,
                "event_id": str(event.event_id),
                "cycle": event.cycle,
                "phase": event.phase.value,
                "kind": event.kind.value,
                "engine_id": event.engine_id.value if event.engine_id is not None else None,
                "job_id": str(event.job_id) if event.job_id is not None else None,
                "causation_id": (
                    str(event.causation_id) if event.causation_id is not None else None
                ),
                "correlation_id": str(event.correlation_id),
                "provenance": event.provenance.value,
                "produced_at": instant,
                "digest": event.digest,
            }
        )

    def verify(
        self,
        project_id: UUID,
        events: Sequence[LedgerEvent],
        *,
        prev_link: str | None = None,
        anchors: Mapping[int, str] = _NO_ANCHORS,
    ) -> ChainVerification:
        """Walk `events` in seq order and report every disagreement.

        `prev_link` is the trusted link before the first event -- needed when the
        events are a window that does not start at seq 1. `anchors` maps a seq to
        the link the caller already trusts for it (a published head, a chunk
        boundary); each is checked, and one the walk never reaches is reported,
        not passed.
        """
        ordered = sorted(events, key=attrgetter("seq"))
        genesis = self.genesis(project_id)
        start = genesis if prev_link is None else prev_link
        findings: list[ChainFinding] = []

        if ordered:
            first = ordered[0].seq
            if prev_link is None and first != 1:
                findings.append(
                    ChainFinding(
                        ChainFindingKind.UNANCHORED_WINDOW,
                        first,
                        f"the events start at seq {first} but no link for seq "
                        f"{first - 1} was given, so the walk began at genesis",
                    )
                )
            if prev_link is not None and first == 1 and prev_link != genesis:
                findings.append(
                    ChainFinding(
                        ChainFindingKind.ANCHOR_MISMATCH,
                        0,
                        "the link given before seq 1 is not this project's genesis",
                    )
                )

        links: list[ChainLink] = []
        current = start
        previous: int | None = None
        for event in ordered:
            findings.extend(self._event_findings(project_id, event, previous))
            current = self.link(current, event)
            links.append(ChainLink(seq=event.seq, event_id=event.event_id, link=current))
            previous = event.seq

        at_seq: dict[int, str] = {}
        for computed in links:
            at_seq.setdefault(computed.seq, computed.link)
        for seq, expected in sorted(anchors.items()):
            actual = at_seq.get(seq)
            if actual is None:
                findings.append(
                    ChainFinding(
                        ChainFindingKind.ANCHOR_UNREACHED,
                        seq,
                        f"an anchor was given for seq {seq}, which the walk never reached",
                    )
                )
            elif actual != expected:
                findings.append(
                    ChainFinding(
                        ChainFindingKind.ANCHOR_MISMATCH,
                        seq,
                        f"the recomputed link at seq {seq} is {actual}, "
                        f"not the anchored {expected}",
                    )
                )

        return ChainVerification(
            project_id=project_id,
            start=start,
            head=current,
            links=tuple(links),
            findings=tuple(findings),
        )

    def _event_findings(
        self, project_id: UUID, event: LedgerEvent, previous: int | None
    ) -> list[ChainFinding]:
        found: list[ChainFinding] = []
        if event.project_id != project_id:
            found.append(
                ChainFinding(
                    ChainFindingKind.FOREIGN_PROJECT,
                    event.seq,
                    f"event {event.event_id} belongs to project {event.project_id}",
                )
            )
        if previous is not None and event.seq == previous:
            found.append(
                ChainFinding(
                    ChainFindingKind.SEQ_DUPLICATE,
                    event.seq,
                    f"event {event.event_id} repeats seq {event.seq}",
                )
            )
        elif previous is not None and event.seq != previous + 1:
            found.append(
                ChainFinding(
                    ChainFindingKind.SEQ_GAP,
                    event.seq,
                    f"seq {event.seq} follows seq {previous}; "
                    f"{event.seq - previous - 1} event(s) missing between them",
                )
            )
        recomputed = digest_event(event.payload)
        if recomputed != event.digest:
            found.append(
                ChainFinding(
                    ChainFindingKind.DIGEST_MISMATCH,
                    event.seq,
                    f"event {event.event_id} stores digest {event.digest} but its "
                    f"payload digests to {recomputed}",
                )
            )
        return found

    @staticmethod
    def _hash(fields: Mapping[str, object]) -> str:
        # canonical_bytes is the ledger's own canonical JSON (sorted keys, no
        # whitespace), so the link preimage is encoded exactly as payloads are.
        return sha256(canonical_bytes(fields)).hexdigest()


LEDGER_CHAIN: Final[LedgerChainInterface] = LedgerChain()
"""The default chain. Annotated with the interface so `mypy --strict` checks that
`LedgerChain` satisfies the declared seam; stateless, so one instance serves."""
