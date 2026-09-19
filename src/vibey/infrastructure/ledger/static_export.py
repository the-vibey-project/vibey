# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The published ledger on disk: the shard file, and the static site written from it.

**The shard** (`JsonlShardStore`) is one JSON Lines file a repository commits --
sub-doctrine 7.a's "the shard the repository holds". Its first line is the header,
``{"shard": {...}}``: the format, the project, how much of the ledger it covers, the
ledger's chain head, the policy's fingerprint, and every count of what the policy
withheld. Every later line is one published record in the handoff ledger's format
(`full_ledger_writer.LedgerLines`), in seq order. The same ledger and the same policy
always write the same bytes -- nothing in the file depends on when it was written --
so re-exporting an unchanged ledger is not a diff.

**The site** (`StaticSiteWriter`) writes the documents a `LedgerSitePlan` lays out,
each through `HtmlSafeJson`: sorted keys, ASCII only, and `<`, `>` and `&` escaped
inside strings, so a payload that says ``<script>`` is served as data and stays data
even when a page inlines the JSON. In every subdirectory the plan writes into, `.json`
files the plan does not contain are removed, so a record that left the shard leaves
the site; files at the top of the site directory are never touched.
"""

import json
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Final
from uuid import UUID

from vibey.application.interfaces.ledger_publication_interface import (
    LedgerShardInterface,
    LedgerSitePlanInterface,
    ShardHeaderInterface,
)
from vibey.application.ledger_publication import (
    InvalidLedgerShard,
    LedgerShard,
    ShardHeader,
    ShardHolding,
)
from vibey.domain.interfaces.publication_policy_interface import TrimCountsInterface
from vibey.domain.ledger import LedgerEvent
from vibey.domain.ledger_record import InvalidLedgerRecord
from vibey.domain.publication_policy import TrimCounts, WithheldReason
from vibey.infrastructure.ledger.full_ledger_writer import LEDGER_LINES
from vibey.infrastructure.ledger.interfaces.full_ledger_writer_interface import (
    LedgerLinesInterface,
)
from vibey.infrastructure.ledger.interfaces.static_export_interface import (
    HtmlSafeJsonInterface,
    ShardHeaderCodecInterface,
)

DEFAULT_HEADER_KEY: Final = "shard"
"""The one key of a shard's first line. No record carries it, so the header can
never be mistaken for a record or a record for the header."""

_TRIM_FIELDS: Final = ("fields", "paths", "emails", "credentials")


class ShardHeaderCodec:
    """The header on a shard's first line, as a JSON object and back."""

    def to_document(self, header: ShardHeaderInterface) -> dict[str, object]:
        return {
            "format": header.format,
            "project_id": str(header.project_id),
            "project_name": header.project_name,
            "holds": header.holds.value,
            "tier": header.tier,
            "ledger": {
                "first_seq": header.ledger_first_seq,
                "last_seq": header.ledger_last_seq,
                "event_count": header.ledger_event_count,
            },
            "chain": {
                "scheme": header.chain_scheme,
                "head": header.chain_head,
                "findings": header.chain_findings,
            },
            "policy": {"scheme": header.policy_scheme, "fingerprint": header.policy_fingerprint},
            "published": {
                "count": header.published_count,
                "digest_range": header.published_digest_range,
            },
            "withheld": {
                "events": {
                    reason.value: header.withheld.get(reason, 0) for reason in WithheldReason
                },
                **self._trim_document(header.trimmed),
            },
            "trims": {
                str(event_id): self._trim_document(trim) for event_id, trim in header.trims.items()
            },
        }

    def from_document(self, document: object) -> ShardHeader:
        root = self._object(document, "shard")
        ledger = self._object(root.get("ledger"), "shard.ledger")
        chain = self._object(root.get("chain"), "shard.chain")
        policy = self._object(root.get("policy"), "shard.policy")
        published = self._object(root.get("published"), "shard.published")
        withheld = self._object(root.get("withheld"), "shard.withheld")
        trims = self._object(root.get("trims"), "shard.trims")
        return ShardHeader(
            format=self._text(root, "format", "shard"),
            project_id=self._uuid(self._text(root, "project_id", "shard"), "shard.project_id"),
            project_name=self._text(root, "project_name", "shard"),
            holds=self._holding(self._text(root, "holds", "shard")),
            tier=self._text(root, "tier", "shard"),
            ledger_first_seq=self._optional_count(ledger, "first_seq", "shard.ledger"),
            ledger_last_seq=self._optional_count(ledger, "last_seq", "shard.ledger"),
            ledger_event_count=self._count(ledger, "event_count", "shard.ledger"),
            chain_scheme=self._text(chain, "scheme", "shard.chain"),
            chain_head=self._text(chain, "head", "shard.chain"),
            chain_findings=self._count(chain, "findings", "shard.chain"),
            policy_scheme=self._text(policy, "scheme", "shard.policy"),
            policy_fingerprint=self._text(policy, "fingerprint", "shard.policy"),
            published_count=self._count(published, "count", "shard.published"),
            published_digest_range=self._text(published, "digest_range", "shard.published"),
            withheld=self._reasons(withheld.get("events")),
            trimmed=self._trim(withheld, "shard.withheld"),
            trims=MappingProxyType(
                {
                    self._uuid(key, f"shard.trims key {key!r}"): self._trim(
                        self._object(value, f"shard.trims.{key}"), f"shard.trims.{key}"
                    )
                    for key, value in trims.items()
                }
            ),
        )

    @staticmethod
    def _trim_document(trim: TrimCountsInterface) -> dict[str, int]:
        return {name: getattr(trim, name) for name in _TRIM_FIELDS}

    def _trim(self, table: dict[str, object], where: str) -> TrimCounts:
        return TrimCounts(**{name: self._count(table, name, where) for name in _TRIM_FIELDS})

    def _reasons(self, value: object) -> MappingProxyType[WithheldReason, int]:
        events = self._object(value, "shard.withheld.events")
        known = {reason.value for reason in WithheldReason}
        if set(events) != known:
            raise InvalidLedgerShard(
                "shard.withheld.events must count exactly these reasons: "
                f"{', '.join(sorted(known))}; it has {', '.join(sorted(events)) or 'none'}"
            )
        return MappingProxyType(
            {
                reason: self._count(events, reason.value, "shard.withheld.events")
                for reason in WithheldReason
            }
        )

    @staticmethod
    def _object(value: object, where: str) -> dict[str, object]:
        if not isinstance(value, dict):
            raise InvalidLedgerShard(f"{where} must be a JSON object")
        return value

    @staticmethod
    def _text(table: dict[str, object], key: str, where: str) -> str:
        value = table.get(key)
        if not isinstance(value, str):
            raise InvalidLedgerShard(f"{where}.{key} must be a string")
        return value

    @staticmethod
    def _count(table: dict[str, object], key: str, where: str) -> int:
        value = table.get(key)
        # bool is an int subclass; `true` is not a count.
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise InvalidLedgerShard(f"{where}.{key} must be a whole number, 0 or more")
        return value

    def _optional_count(self, table: dict[str, object], key: str, where: str) -> int | None:
        return None if table.get(key) is None else self._count(table, key, where)

    @staticmethod
    def _uuid(text: str, where: str) -> UUID:
        try:
            return UUID(text)
        except ValueError as exc:
            raise InvalidLedgerShard(f"{where} is not a UUID: {text!r}") from exc

    @staticmethod
    def _holding(text: str) -> ShardHolding:
        try:
            return ShardHolding(text)
        except ValueError as exc:
            raise InvalidLedgerShard(
                f"shard.holds is {text!r}; it must be one of "
                f"{', '.join(holding.value for holding in ShardHolding)}"
            ) from exc


SHARD_HEADERS: Final[ShardHeaderCodecInterface] = ShardHeaderCodec()
"""The header codec. Annotated with the interface so `mypy --strict` checks the
class against its declared seam; stateless, so one instance serves."""


class JsonlShardStore:
    """Writes and reads a shard as JSON Lines: the header line, then one record per line."""

    def __init__(
        self,
        *,
        headers: ShardHeaderCodecInterface = SHARD_HEADERS,
        lines: LedgerLinesInterface = LEDGER_LINES,
        header_key: str = DEFAULT_HEADER_KEY,
    ) -> None:
        self._headers = headers
        self._lines = lines
        self._header_key = header_key

    def write(self, shard: LedgerShardInterface, path: Path) -> None:
        header = json.dumps(
            {self._header_key: self._headers.to_document(shard.header)},
            sort_keys=True,
            separators=(",", ":"),
        )
        body = [header, *(self._lines.encode(record) for record in shard.records)]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(body) + "\n", encoding="utf-8")

    def read(self, path: Path) -> LedgerShard:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise InvalidLedgerShard(f"cannot read {path}: {exc}") from exc
        numbered = [(number, line) for number, line in enumerate(text.splitlines(), 1) if line]
        if not numbered:
            raise InvalidLedgerShard("the file is empty; a shard starts with its header line")
        (first_number, first_line), *rest = numbered
        return LedgerShard(
            header=self._header(first_number, first_line),
            records=tuple(self._record(number, line) for number, line in rest),
        )

    def _header(self, number: int, line: str) -> ShardHeaderInterface:
        try:
            document = json.loads(line)
        except json.JSONDecodeError as exc:
            raise InvalidLedgerShard(f"line {number}: not JSON: {exc.msg}") from exc
        if not isinstance(document, dict) or set(document) != {self._header_key}:
            raise InvalidLedgerShard(
                f"line {number}: a shard starts with its header, "
                f'{{"{self._header_key}": {{...}}}}, and nothing else on that line'
            )
        return self._headers.from_document(document[self._header_key])

    def _record(self, number: int, line: str) -> LedgerEvent:
        try:
            return self._lines.decode(line)
        except InvalidLedgerRecord as exc:
            raise InvalidLedgerShard(f"line {number}: {exc}") from exc


class HtmlSafeJson:
    """JSON for serving: the same document always encodes to the same text, and
    nothing in it can end a `<script>` element or open a tag when inlined."""

    def __init__(self, *, indent: int | None = 2) -> None:
        self._indent = indent

    def dumps(self, document: object) -> str:
        text = json.dumps(
            document, sort_keys=True, indent=self._indent, ensure_ascii=True, allow_nan=False
        )
        # JSON syntax has no <, > or &, so each one here is inside a string, where a
        # \u escape means the same character to every JSON reader.
        return text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026") + "\n"


HTML_SAFE_JSON: Final[HtmlSafeJsonInterface] = HtmlSafeJson()
"""The encoder every site document goes through. Annotated with the interface so
`mypy --strict` checks the class against its declared seam."""


class StaticSiteWriter:
    """Writes a site plan's documents into a directory."""

    def __init__(self, *, encoder: HtmlSafeJsonInterface = HTML_SAFE_JSON) -> None:
        self._encoder = encoder

    def write(self, plan: LedgerSitePlanInterface, directory: Path) -> None:
        targets = {
            self._target(directory, relative): document
            for relative, document in plan.documents.items()
        }
        directory.mkdir(parents=True, exist_ok=True)
        for folder in sorted({target.parent for target in targets} - {directory}):
            folder.mkdir(parents=True, exist_ok=True)
            for stale in folder.glob("*.json"):
                if stale not in targets:
                    stale.unlink()
        for target, document in targets.items():
            target.write_text(self._encoder.dumps(document), encoding="utf-8")

    @staticmethod
    def _target(directory: Path, relative: str) -> Path:
        pure = PurePosixPath(relative)
        if pure.is_absolute() or ".." in pure.parts or not pure.parts:
            raise InvalidLedgerShard(f"refusing to write outside the site directory: {relative!r}")
        return directory.joinpath(*pure.parts)
