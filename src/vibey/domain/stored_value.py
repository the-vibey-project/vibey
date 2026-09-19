# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reading a closed vocabulary back out of storage, forward-compatibly (vibey#287).

vibey keeps several closed vocabularies -- `EngineId`, `Phase`, `Provenance`,
`JobState`, `CircuitState` -- in database columns that the whole fleet shares. A
newer vibey can write a value an older one has no member for: an engine id needs no
migration at all (#281 adds `claudeloop-local`), and a Postgres enum is widened by a
migration that runs before the older pods of a rolling upgrade are gone. A rollback
leaves the rows behind; the tables are shared and the ledger is append-only.

Calling the enum on such a value raises `ValueError`, and one row then makes a
project unreadable to every older worker in the fleet. So the rule vibey#275 set for
`event.kind` holds for every stored vocabulary: **readers are forward compatible,
writers are strict.**

- A reader parses through a `StoredValueParser`. A value it knows is its member;
  anything else is an `UnrecognizedValue` carrying the stored text verbatim. It never
  raises and never drops the value.
- A consumer matches members by identity (`is Phase.BUILD`), so an unrecognized value
  matches none of them. Anything only a member has -- its `name`, a key of a
  `Mapping[Phase, ...]` -- needs an `isinstance` narrowing first, and the type checker
  insists on it.
- A writer takes the member type, so vibey only ever writes a value it knows.

`vibey/domain/ledger.py::UnrecognizedEventKind` (vibey#275) came first and predates
this module; it follows the same rule with its own parser.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar


@dataclass(frozen=True, slots=True)
class UnrecognizedValue:
    """A stored value this version of vibey has no member for.

    A newer vibey wrote it -- the newer pods of a rolling upgrade, or the release a
    rollback stepped back from -- or an older one did and a later release retired
    the member. Either way the row is real. A reader keeps it; what no reader can
    do is act on what it means.

    Each vocabulary has its own subclass (`UnrecognizedEngineId`,
    `UnrecognizedPhase`, ...), so an unknown phase is never equal to an unknown
    engine id with the same text, and `isinstance` narrows each field on its own.
    A subclass names its vocabulary in `members`; construction refuses a value that
    is one of them, so a known value can never hide behind this type and slip past
    an `is Member` check.
    """

    value: str
    """The value exactly as stored. A newer vibey reads the same text as its own
    member's value, so anything built from `.value` -- a hash-chain link, a JSON
    record, a SQL parameter -- comes out identical on both versions."""

    members: ClassVar[frozenset[str]] = frozenset()
    """The values the vocabulary's members carry; a subclass sets it."""

    def __post_init__(self) -> None:
        if self.value in self.members:
            raise ValueError(
                f"{self.value!r} is a known value; {type(self).__name__} holds only "
                "values this vibey has no member for"
            )

    def __str__(self) -> str:
        return self.value

    def __format__(self, spec: str) -> str:
        # A member is a str, so `f"{engine_id:<12}"` pads it; the stored text pads
        # the same way, so a table of mixed rows lines up.
        return format(self.value, spec)


class StoredValueParser[M: StrEnum, U: UnrecognizedValue]:
    """Reads the stored text of one closed vocabulary. Never raises.

    Matching is exact: the column holds a member's value verbatim, so a case variant
    is not that member, it is another value. One class for every vocabulary, so the
    rule cannot drift between them; each vocabulary gets one shared instance beside
    its enum (`ENGINE_ID_PARSER`, `PHASE_PARSER`, ...).
    """

    def __init__(self, members: type[M], unrecognized: Callable[[str], U]) -> None:
        self._members: Mapping[str, M] = {member.value: member for member in members}
        self._unrecognized = unrecognized

    def parse(self, raw: str) -> M | U:
        """The member, or the unrecognized text preserved."""
        member = self._members.get(raw)
        return member if member is not None else self._unrecognized(raw)

    def known(self, raw: str) -> M | None:
        """The member, or None for a value this vibey does not know -- for a
        consumer that can only ever act on a member."""
        return self._members.get(raw)
