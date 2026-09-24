# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A project's cycle caps: what a change to them is, and the record of every change.

The caps live in the project's stored config, `max_cycle_dollars` and
`max_cycle_turns`, the one place the budget brake reads them
(`application/budget_source.py::LedgerBudgetSource.caps_from_config`). `vibey budget set`
and `clear` change them after the project exists. This module is the pure half of that:

- **A cap is a positive number.** Dollars are a finite number above zero; turns a whole
  number above zero. A bool is refused although `isinstance(True, int)` holds, as the
  brake's parser refuses it. Clearing a cap leaves the project uncapped, exactly as if
  the cap had never been set.
- **A change is one cap, from old to new.** `CapChange` names the cap, the value it had
  and the value it has now, where `None` is uncapped; each becomes one `BudgetCapChanged`
  event. A request that would leave a cap as it is changes nothing and records nothing,
  so replaying a `set` or a `clear` is a no-op.
- **Who changed it is a label, not an authority.** `by` is the account that ran the
  command unless the caller names itself (the VS Code extension says `vibey-vscode`);
  `account` is always the account, so the record says who ran it whatever the label.
- **The history is the ledger's.** `BudgetCapHistory` reads `BudgetCapChanged` events back
  in the order they were appended, and only those vibey wrote as `trusted`: no engine
  event is mapped onto the kind, but a kind is a string, and an event that did not come
  from the operator's own command is not a change anyone made to the caps.
"""

import math
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from operator import attrgetter
from types import MappingProxyType
from typing import ClassVar, Final

from vibey.domain.errors import InvalidBudgetChange
from vibey.domain.interfaces.budget_caps_interface import (
    BudgetCapHistoryInterface,
    CapChangePlannerInterface,
    CapRequestInterface,
    CycleCapsInterface,
)
from vibey.domain.ledger import EventKind, LedgerEvent, Provenance


class CapField(StrEnum):
    """A cap a project's config carries, named by the key it is stored under."""

    MAX_CYCLE_DOLLARS = "max_cycle_dollars"
    MAX_CYCLE_TURNS = "max_cycle_turns"


type CapValue = float | int | None
"""A cap's value: dollars are a float, turns an int, and `None` is no cap."""


@dataclass(frozen=True, slots=True)
class CycleCaps:
    """The caps in force for each of a project's cycles. `None` is uncapped."""

    max_dollars: float | None = None
    max_turns: int | None = None

    def value_of(self, cap: CapField) -> CapValue:
        return self.max_dollars if cap is CapField.MAX_CYCLE_DOLLARS else self.max_turns


@dataclass(frozen=True, slots=True)
class CapChange:
    """One cap, from the value it had to the value it has now. `None` is uncapped."""

    field: CapField
    old: CapValue
    new: CapValue

    def payload(self, *, by: str, account: str) -> dict[str, object]:
        """The `BudgetCapChanged` event's payload: what changed, the name the change was
        made under, and the account that made it."""
        return {
            "field": self.field.value,
            "old": self.old,
            "new": self.new,
            "by": by,
            "account": account,
        }


@dataclass(frozen=True, slots=True)
class CapRequest:
    """What a person asked for: caps to set to a value, and caps to clear.

    Built by `CapChangePlanner.setting` or `.clearing`, which refuse any value that is
    not a cap. The two sets never overlap: a cap is set or cleared, never both.
    """

    set_to: Mapping[CapField, float | int]
    clear: frozenset[CapField] = frozenset()

    def __post_init__(self) -> None:
        both = self.clear & self.set_to.keys()
        if both:
            names = ", ".join(sorted(cap.value for cap in both))
            raise InvalidBudgetChange(f"{names} cannot be both set and cleared")
        # A copy the caller cannot change after the check.
        object.__setattr__(self, "set_to", MappingProxyType(dict(self.set_to)))


class CapChangePlanner:
    """Refuses what is not a cap, and says what a request changes. Pure."""

    MAX_ACTOR_LENGTH: ClassVar[int] = 200
    """Long enough for any account or tool name; short enough for one line of output."""

    def setting(self, *, max_dollars: object = None, max_turns: object = None) -> CapRequest:
        """A request to set the dollar cap, the turn cap, or both. Raises
        `InvalidBudgetChange` for a value that is not a cap, or when neither is given."""
        if max_dollars is None and max_turns is None:
            raise InvalidBudgetChange("nothing to set: name a dollar cap, a turn cap, or both")
        values: dict[CapField, float | int] = {}
        if max_dollars is not None:
            values[CapField.MAX_CYCLE_DOLLARS] = self.dollars(max_dollars)
        if max_turns is not None:
            values[CapField.MAX_CYCLE_TURNS] = self.turns(max_turns)
        return CapRequest(set_to=values)

    def clearing(self, caps: Iterable[CapField]) -> CapRequest:
        """A request to remove caps, leaving the project uncapped for each. Raises
        `InvalidBudgetChange` when it names none."""
        cleared = frozenset(caps)
        if not cleared:
            raise InvalidBudgetChange(
                "nothing to clear: name the dollar cap, the turn cap, or both"
            )
        return CapRequest(set_to={}, clear=cleared)

    def plan(
        self, current: CycleCapsInterface, request: CapRequestInterface
    ) -> tuple[CapChange, ...]:
        """The changes `request` makes to `current`, dollars first. A cap the request
        would leave as it is -- set to the value it has, or cleared when already
        uncapped -- is not a change."""
        changes: list[CapChange] = []
        for cap in CapField:
            if cap in request.set_to:
                new: CapValue = request.set_to[cap]
            elif cap in request.clear:
                new = None
            else:
                continue
            old = current.value_of(cap)
            if new != old:
                changes.append(CapChange(field=cap, old=old, new=new))
        return tuple(changes)

    def actor(self, label: str | None, *, account: str) -> str:
        """Who a change is recorded as: `label` when the caller names itself, else the
        account. A label is recorded and printed as given, so it must be one line of
        visible text: not empty, not over `MAX_ACTOR_LENGTH`, and free of control and
        formatting characters, which could forge a line of output or reorder one."""
        if label is None:
            return account
        name = label.strip()
        if not name:
            raise InvalidBudgetChange("the name a change is recorded under cannot be empty")
        if len(name) > self.MAX_ACTOR_LENGTH:
            raise InvalidBudgetChange(
                f"the name a change is recorded under is over {self.MAX_ACTOR_LENGTH} characters"
            )
        if any(unicodedata.category(char).startswith("C") for char in name):
            raise InvalidBudgetChange(
                "the name a change is recorded under cannot contain control or formatting "
                "characters"
            )
        return name

    @staticmethod
    def dollars(value: object) -> float:
        """A dollar cap: a finite number above zero. Infinity and NaN are refused as
        well as zero and below: none is a cap, and the config's JSON cannot hold them."""
        amount = math.nan
        if isinstance(value, int | float) and not isinstance(value, bool):
            try:
                amount = float(value)
            except OverflowError:  # an int too large for a float is no amount either
                amount = math.nan
        if not math.isfinite(amount) or amount <= 0:
            raise InvalidBudgetChange(
                f"a dollar cap must be a number above zero, not {value!r}; "
                "clear the cap to remove it"
            )
        return amount

    @staticmethod
    def turns(value: object) -> int:
        """A turn cap: a whole number above zero."""
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise InvalidBudgetChange(
                f"a turn cap must be a whole number above zero, not {value!r}; "
                "clear the cap to remove it"
            )
        return value


CAP_CHANGE_PLANNER: Final[CapChangePlannerInterface] = CapChangePlanner()
"""The planner every change to a cap shares. Stateless, so one instance serves."""


@dataclass(frozen=True, slots=True)
class CapHistoryEntry:
    """One recorded change to a cap, as the ledger holds it: `old` and `new` are the
    stored values, `None` for uncapped."""

    at: datetime
    by: str | None
    field: str
    old: object
    new: object


class BudgetCapHistory:
    """Every change to a project's caps, oldest first, read back from its ledger. Pure."""

    def entries(self, events: Iterable[LedgerEvent]) -> tuple[CapHistoryEntry, ...]:
        recorded = sorted(
            (
                event
                for event in events
                if event.kind is EventKind.BUDGET_CAP_CHANGED
                and event.provenance is Provenance.TRUSTED
            ),
            key=attrgetter("seq"),
        )
        return tuple(self._entry(event) for event in recorded)

    @staticmethod
    def _entry(event: LedgerEvent) -> CapHistoryEntry:
        # Read as stored, not re-validated: the record is what was written, and a cap a
        # newer vibey added is still a change someone made (vibey#275's rule for readers).
        by = event.payload.get("by")
        field = event.payload.get("field")
        return CapHistoryEntry(
            at=event.produced_at,
            by=by if isinstance(by, str) else None,
            field=field if isinstance(field, str) else "",
            old=event.payload.get("old"),
            new=event.payload.get("new"),
        )


BUDGET_CAP_HISTORY: Final[BudgetCapHistoryInterface] = BudgetCapHistory()
"""The projection every reader of a project's cap history shares. Stateless."""
