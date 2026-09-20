# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Publishing a ledger: the shard a repository holds, and the static site built from it.

Sub-doctrine 7.a: the ledger always has a way for anyone to search it -- the full
public ledger where a deployment holds it, or the shard the repository holds. This
module is the second of those, in two steps split where the database stops being
needed:

1. **Export** (`LedgerExporter`) reads one project's whole ledger, derives the
   ledger's own hash chain over every event -- the withheld ones included -- runs
   every event through the publication policy (`domain/publication_policy.py`), and
   hands a `LedgerShard` to a `LedgerShardStore`: a header saying what the shard is,
   where it came from and everything the policy withheld, then the published records.
2. **Site** (`LedgerSiteBuilder`) reads a shard, checks it, and plans the static JSON
   surface: one document per record, a search index, and a manifest. It needs no
   database, so it runs wherever the shard is -- a docs build, a CI job, a laptop.

The chain head in a shard is the ledger's, not the shard's: the link at the ledger's
last seq, computed over every stored field of every event before the policy ran. Anyone
holding the full ledger -- the operator, an archival node (vibey#114) -- checks a
published shard against their own by recomputing it. The published records carry the
digest of what was published instead, so a public reader checks each record against its
digest and the whole shard against `digest_range`.
"""

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC
from enum import StrEnum
from operator import attrgetter
from pathlib import Path
from types import MappingProxyType
from typing import Final
from uuid import UUID

from vibey.application.interfaces.ledger import LedgerReader, LedgerShardStore, LedgerSiteWriter
from vibey.application.interfaces.ledger_publication_interface import (
    LedgerShardInterface,
    SearchTokenizerInterface,
    ShardHeaderInterface,
)
from vibey.domain.errors import VibeyError
from vibey.domain.interfaces.ledger_chain_interface import LedgerChainInterface
from vibey.domain.interfaces.ledger_record_interface import LedgerRecordCodecInterface
from vibey.domain.interfaces.publication_policy_interface import (
    PublicationPolicyInterface,
    TrimCountsInterface,
)
from vibey.domain.ledger import LedgerEvent, digest_event, digest_range
from vibey.domain.ledger_chain import LEDGER_CHAIN
from vibey.domain.ledger_query import SELF_ACTOR
from vibey.domain.ledger_record import LEDGER_RECORDS
from vibey.domain.publication_policy import NO_TRIM, WithheldReason

SHARD_FORMAT: Final = "vibey-ledger-shard/v1"
"""The shard format this build writes and reads."""

SITE_FORMAT: Final = "vibey-ledger-site/v1"
"""The format of every document the site build writes."""

UNTIERED: Final = "standard (untiered)"
"""The storage tier every event comes from until vibey#114 introduces tiers. Stated
rather than omitted, so a reader never has to guess which tier served a result."""

DEFAULT_RECORDS_DIR: Final = "records"
DEFAULT_INDEX_NAME: Final = "index.json"
DEFAULT_MANIFEST_NAME: Final = "manifest.json"
DEFAULT_MIN_TOKEN_LENGTH: Final = 2
"""Shorter words (`a`, `i`, single digits) match nearly everything and find nothing."""

_WORD: Final = re.compile(r"\w+")


class ShardHolding(StrEnum):
    """How much of the ledger a shard covers."""

    FULL = "full"
    """From the ledger's first event to its head when the shard was exported."""
    WINDOW = "window"
    """A stretch that does not start at the ledger's first event."""


class InvalidLedgerShard(VibeyError):
    """A file or value that is not a shard this build can publish. Says why.

    The exception remains the concrete type callers catch; its diagnostic
    surface is declared by ``InvalidLedgerShardInterface`` for code that only
    needs to inspect an error crossing the application boundary.
    """


@dataclass(frozen=True, slots=True)
class ShardHeader:
    """What a shard is, where it came from, and everything the policy withheld."""

    format: str
    project_id: UUID
    project_name: str
    holds: ShardHolding
    tier: str
    ledger_first_seq: int | None
    ledger_last_seq: int | None
    ledger_event_count: int
    chain_scheme: str
    chain_head: str
    chain_findings: int
    policy_scheme: str
    policy_fingerprint: str
    published_count: int
    published_digest_range: str
    withheld: Mapping[WithheldReason, int]
    trimmed: TrimCountsInterface
    trims: Mapping[UUID, TrimCountsInterface]

    @property
    def events_withheld(self) -> int:
        return sum(self.withheld.values())


@dataclass(frozen=True, slots=True)
class LedgerShard:
    """The shard a repository holds."""

    header: ShardHeaderInterface
    records: tuple[LedgerEvent, ...]


@dataclass(frozen=True, slots=True)
class LedgerSitePlan:
    """Every document of the static JSON surface, by relative path."""

    shard: LedgerShardInterface
    documents: Mapping[str, Mapping[str, object]]


class SearchTokenizer:
    """The words a client-side search can match in a payload: lower-cased runs of
    letters, digits and underscores from every string and number, each once, sorted
    so the same payload always indexes the same way."""

    def __init__(self, *, min_length: int = DEFAULT_MIN_TOKEN_LENGTH) -> None:
        self._min_length = min_length

    def tokens(self, payload: Mapping[str, object]) -> tuple[str, ...]:
        return tuple(sorted(self._words(payload)))

    def _words(self, value: object) -> set[str]:
        if value is None or isinstance(value, bool):
            return set()
        if isinstance(value, Mapping):
            return set().union(*(self._words(item) for item in value.values()))
        if isinstance(value, list | tuple):
            return set().union(*(self._words(item) for item in value))
        return {word for word in _WORD.findall(str(value).lower()) if len(word) >= self._min_length}


class LedgerExporter:
    """Reads one project's whole ledger and makes the shard the public may see."""

    def __init__(
        self,
        *,
        ledger: LedgerReader,
        store: LedgerShardStore,
        policy: PublicationPolicyInterface,
        chain: LedgerChainInterface = LEDGER_CHAIN,
        tier: str = UNTIERED,
        shard_format: str = SHARD_FORMAT,
    ) -> None:
        self._ledger = ledger
        self._store = store
        self._policy = policy
        self._chain = chain
        self._tier = tier
        self._format = shard_format

    def shard(
        self, project_id: UUID, project_name: str, events: Sequence[LedgerEvent]
    ) -> LedgerShard:
        ordered = tuple(sorted(events, key=attrgetter("seq")))
        # Over every event, before the policy: the head anchors the ledger itself.
        verification = self._chain.verify(project_id, ordered)
        outcome = self._policy.apply(ordered)
        first = ordered[0].seq if ordered else None
        header = ShardHeader(
            format=self._format,
            project_id=project_id,
            project_name=project_name,
            holds=ShardHolding.FULL if first in (None, 1) else ShardHolding.WINDOW,
            tier=self._tier,
            ledger_first_seq=first,
            ledger_last_seq=ordered[-1].seq if ordered else None,
            ledger_event_count=len(ordered),
            chain_scheme=self._chain.scheme,
            chain_head=verification.head,
            chain_findings=len(verification.findings),
            policy_scheme=self._policy.rules.scheme,
            policy_fingerprint=self._policy.rules.fingerprint,
            published_count=len(outcome.records),
            published_digest_range=digest_range(outcome.records),
            withheld=outcome.withheld,
            trimmed=outcome.trimmed,
            trims=outcome.trims,
        )
        return LedgerShard(header=header, records=outcome.records)

    async def export(self, project_id: UUID, project_name: str, out: Path) -> LedgerShard:
        events = await self._ledger.all_for_project(project_id)
        shard = self.shard(project_id, project_name, events)
        self._store.write(shard, out)
        return shard


class LedgerSiteBuilder:
    """Checks a shard and lays out its static JSON surface. Needs no database."""

    def __init__(
        self,
        *,
        store: LedgerShardStore,
        writer: LedgerSiteWriter,
        tokenizer: SearchTokenizerInterface | None = None,
        records: LedgerRecordCodecInterface = LEDGER_RECORDS,
        shard_format: str = SHARD_FORMAT,
        site_format: str = SITE_FORMAT,
        self_actor: str = SELF_ACTOR,
        records_dir: str = DEFAULT_RECORDS_DIR,
        index_name: str = DEFAULT_INDEX_NAME,
        manifest_name: str = DEFAULT_MANIFEST_NAME,
    ) -> None:
        self._store = store
        self._writer = writer
        self._tokenizer: SearchTokenizerInterface = (
            tokenizer if tokenizer is not None else SEARCH_TOKENIZER
        )
        self._records = records
        self._shard_format = shard_format
        self._site_format = site_format
        self._self_actor = self_actor
        self._records_dir = records_dir
        self._index_name = index_name
        self._manifest_name = manifest_name

    def build(self, source: Path, out: Path) -> LedgerSitePlan:
        plan = self.plan(self._store.read(source))
        self._writer.write(plan, out)
        return plan

    def plan(self, shard: LedgerShardInterface) -> LedgerSitePlan:
        self._check(shard)
        header = shard.header
        records = shard.records
        documents: dict[str, Mapping[str, object]] = {}
        for position, event in enumerate(records):
            before = records[position - 1] if position else None
            after = records[position + 1] if position + 1 < len(records) else None
            documents[self._record_path(event.event_id)] = {
                "format": self._site_format,
                "project_id": str(header.project_id),
                "record": self._records.to_fields(event),
                "withheld": self._counts(header.trims.get(event.event_id, NO_TRIM)),
                "previous": self._neighbour(before),
                "next": self._neighbour(after),
            }
        documents[self._index_name] = {
            "format": self._site_format,
            "project_id": str(header.project_id),
            "records": [self._entry(event) for event in records],
        }
        documents[self._manifest_name] = self._manifest(shard)
        return LedgerSitePlan(shard=shard, documents=MappingProxyType(documents))

    def _check(self, shard: LedgerShardInterface) -> None:
        header = shard.header
        if header.format != self._shard_format:
            raise InvalidLedgerShard(
                f"unsupported shard format {header.format!r}; this build reads "
                f"{self._shard_format!r}"
            )
        first, last = header.ledger_first_seq, header.ledger_last_seq
        seen: set[UUID] = set()
        previous: int | None = None
        for event in shard.records:
            where = f"record seq {event.seq}"
            if event.project_id != header.project_id:
                raise InvalidLedgerShard(
                    f"{where} belongs to project {event.project_id}, not {header.project_id}"
                )
            if previous is not None and event.seq <= previous:
                raise InvalidLedgerShard(
                    f"{where} follows seq {previous}; records must rise in seq order"
                )
            if first is None or last is None or not first <= event.seq <= last:
                raise InvalidLedgerShard(
                    f"{where} is outside the ledger range the header states ({first}..{last})"
                )
            if event.event_id in seen:
                raise InvalidLedgerShard(f"{where} repeats event id {event.event_id}")
            if digest_event(event.payload) != event.digest:
                raise InvalidLedgerShard(f"{where}: its digest is not its payload's digest")
            seen.add(event.event_id)
            previous = event.seq
        if header.published_count != len(shard.records):
            raise InvalidLedgerShard(
                f"the header states {header.published_count} published record(s); "
                f"the shard holds {len(shard.records)}"
            )
        if header.ledger_event_count != header.published_count + header.events_withheld:
            raise InvalidLedgerShard(
                f"the header's counts do not add up: {header.ledger_event_count} event(s) "
                f"covered, {header.published_count} published, "
                f"{header.events_withheld} withheld"
            )
        if digest_range(shard.records) != header.published_digest_range:
            raise InvalidLedgerShard(
                "the records' digest_range is not the one the header states; "
                "a record was changed, added or lost after export"
            )
        summed: TrimCountsInterface = NO_TRIM
        for trim in header.trims.values():
            summed = summed.plus(trim)
        if self._counts(summed) != self._counts(header.trimmed):
            raise InvalidLedgerShard(
                "the header's per-record trims do not add up to its trimmed total"
            )
        strays = set(header.trims) - seen
        if strays:
            raise InvalidLedgerShard(
                f"the header counts trims for event(s) the shard does not hold: "
                f"{', '.join(sorted(map(str, strays)))}"
            )

    def _record_path(self, event_id: UUID) -> str:
        return f"{self._records_dir}/{event_id}.json"

    def _entry(self, event: LedgerEvent) -> dict[str, object]:
        return {
            "id": str(event.event_id),
            "seq": event.seq,
            "kind": event.kind.value,
            "phase": event.phase.value,
            "actor": event.engine_id.value if event.engine_id is not None else self._self_actor,
            "time": event.produced_at.astimezone(UTC).isoformat(),
            "digest": event.digest,
            "tokens": list(self._tokenizer.tokens(event.payload)),
        }

    @staticmethod
    def _neighbour(event: LedgerEvent | None) -> dict[str, object] | None:
        if event is None:
            return None
        return {"event_id": str(event.event_id), "seq": event.seq, "digest": event.digest}

    @staticmethod
    def _counts(trim: TrimCountsInterface) -> dict[str, int]:
        return {
            "fields": trim.fields,
            "paths": trim.paths,
            "emails": trim.emails,
            "credentials": trim.credentials,
        }

    def _manifest(self, shard: LedgerShardInterface) -> dict[str, object]:
        header = shard.header
        records = shard.records
        withheld = header.events_withheld
        return {
            "format": self._site_format,
            "shard_format": header.format,
            "project": {"project_id": str(header.project_id), "name": header.project_name},
            "holds": header.holds.value,
            "tier": header.tier,
            "seq_range": {
                "first": header.ledger_first_seq,
                "last": header.ledger_last_seq,
                "events": header.ledger_event_count,
            },
            "published": {
                "records": header.published_count,
                "first_seq": records[0].seq if records else None,
                "last_seq": records[-1].seq if records else None,
            },
            "digest_range": header.published_digest_range,
            "chain": {
                "scheme": header.chain_scheme,
                "head": header.chain_head,
                "head_seq": header.ledger_last_seq,
                "verified": header.chain_findings == 0,
                "findings": header.chain_findings,
            },
            "policy": {"scheme": header.policy_scheme, "fingerprint": header.policy_fingerprint},
            "withheld": {
                "events": withheld,
                "by_reason": {
                    reason.value: header.withheld.get(reason, 0) for reason in WithheldReason
                },
                **self._counts(header.trimmed),
            },
            "statement": f"{withheld} event{'' if withheld == 1 else 's'} withheld by policy",
            "documents": {
                "index": self._index_name,
                "records": f"{self._records_dir}/{{event_id}}.json",
            },
        }


SEARCH_TOKENIZER: Final[SearchTokenizerInterface] = SearchTokenizer()
"""The default tokenizer. Annotated with the interface so `mypy --strict` checks the
class against its declared seam."""
