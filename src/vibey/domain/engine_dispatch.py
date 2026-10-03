# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Hybrid engine dispatch (ADR-0079, sub-doctrine 8.a's overflow clause).

Today's selection, `singleton`, offers SWRR the first tier in `TIER_PREFERENCE` that can
win a round -- the local tier whenever any local engine has weight, so every BUILD job
queues behind the one local model slot and a paid engine runs only when no local engine
can take the job at all. `hybrid` keeps sovereign the preference and adds one narrow
path: a paid engine may take a job as **overflow** when every eligible local engine's
declared slots are occupied, the job has waited at least the declared threshold, and the
project has recorded fewer paid overflows this UTC day than its declared cap.

Everything here is pure. The slots in use, how long the job has waited and how many
overflows today's ledger holds are counted by the infrastructure and handed in as a
`DispatchLoad`; the clock's reading arrives as a value. Nothing here reads a clock, a
table or the environment.

`auto` chooses between the two from a measurement of local-slot contention over the
project's own recorded BUILD sessions (`DispatchMeasurementJudge`). A missing, stale,
invalid or failed measurement resolves to `singleton`, as ADR-0074 requires of every
measured dispatch choice.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import TYPE_CHECKING, Final

from vibey.domain.config import (
    DEFAULT_LOCAL_ENGINE_SLOTS,
    DEFAULT_PAID_ENGINE_SLOTS,
    EngineDispatchConfig,
)
from vibey.domain.engine import ENGINE_ID_PARSER, EngineId, EngineTier
from vibey.domain.errors import VibeyError
from vibey.domain.rotation import Candidate, Selection, preferred_tier

if TYPE_CHECKING:
    from vibey.domain.interfaces.engine_dispatch_interface import (
        DispatchMeasurementJudgeInterface,
        EngineDispatcherInterface,
        UtcDayInterface,
    )

MEASUREMENT_ALGORITHM: Final = "local-slot-contention/1"
"""The version of `DispatchMeasurementJudge.measure`. Part of every fingerprint, so a
measurement taken by another algorithm is never read as this one's."""


class DispatchMode(StrEnum):
    SINGLETON = "singleton"
    HYBRID = "hybrid"
    AUTO = "auto"


class ModeSource(StrEnum):
    """Why the resolved mode is what it is -- recorded with every overflow (10.f)."""

    DECLARED = "declared"
    MEASURED = "measured"
    FALLBACK = "fallback"


@dataclass(frozen=True, slots=True)
class EngineDispatchPolicy:
    """The resolved policy one selection runs under: `mode` is never `auto` here."""

    mode: DispatchMode
    overflow_after_seconds: int
    paid_daily_cap: int
    slot_poll_seconds: int
    slots: Mapping[EngineId, int] = field(default_factory=dict)
    source: ModeSource = ModeSource.DECLARED
    reason: str = ""

    def __post_init__(self) -> None:
        if self.mode is DispatchMode.AUTO:
            raise ValueError("a resolved dispatch policy is singleton or hybrid, never auto")

    def slots_for(self, engine_id: EngineId, tier: EngineTier) -> int:
        """The engine's declared concurrent slots, or its tier's default."""
        declared = self.slots.get(engine_id)
        if declared is not None:
            return declared
        return DEFAULT_LOCAL_ENGINE_SLOTS if tier is EngineTier.LOCAL else DEFAULT_PAID_ENGINE_SLOTS

    @classmethod
    def from_config(
        cls,
        config: EngineDispatchConfig,
        mode: DispatchMode,
        *,
        source: ModeSource = ModeSource.DECLARED,
        reason: str = "",
    ) -> EngineDispatchPolicy:
        """The policy `config` declares, run in `mode`. Slots for an engine this vibey does
        not know are dropped: no candidate can carry that id."""
        slots = {
            engine: count
            for name, count in config.slots.items()
            if (engine := ENGINE_ID_PARSER.known(name)) is not None
        }
        return cls(
            mode=mode,
            overflow_after_seconds=config.overflow_after_seconds,
            paid_daily_cap=config.paid_daily_cap,
            slot_poll_seconds=config.slot_poll_seconds,
            slots=slots,
            source=source,
            reason=reason,
        )


@dataclass(frozen=True, slots=True)
class DispatchLoad:
    """What the queue and the ledger say right now, counted outside the domain.

    `in_flight` counts the unexpired leased jobs assigned to each engine, the job being
    selected excluded. `waited_seconds` is how long this job, on this attempt, has been
    held for a local slot (0.0 when it never was). `paid_overflow_today` is the number of
    `EngineOverflowSelected` events the project's ledger holds for the current UTC day.
    """

    in_flight: Mapping[EngineId, int] = field(default_factory=dict)
    waited_seconds: float = 0.0
    paid_overflow_today: int = 0


@dataclass(frozen=True, slots=True)
class SlotOccupancy:
    engine_id: EngineId
    in_flight: int
    slots: int


@dataclass(frozen=True, slots=True)
class OverflowGrounds:
    """Why a job may not have a local slot now, and what the cap allows -- the body of
    both the hold and the overflow records, so each states its own evidence (10.f)."""

    local: tuple[SlotOccupancy, ...]
    waited_seconds: float
    overflow_after_seconds: int
    paid_daily_cap: int
    paid_overflow_today: int

    @property
    def cap_remaining(self) -> int:
        """Overflows still allowed today, before this one."""
        return max(self.paid_daily_cap - self.paid_overflow_today, 0)

    def payload(self) -> dict[str, object]:
        return {
            "reason": "every eligible local slot is occupied",
            "local_slots": [
                {"engine": o.engine_id.value, "in_flight": o.in_flight, "slots": o.slots}
                for o in self.local
            ],
            "waited_seconds": round(self.waited_seconds, 3),
            "overflow_after_seconds": self.overflow_after_seconds,
            "paid_daily_cap": self.paid_daily_cap,
            "paid_overflow_today": self.paid_overflow_today,
            "cap_remaining": self.cap_remaining,
        }


@dataclass(frozen=True, slots=True)
class DispatchPlan:
    """The candidates SWRR may choose from. `overflow` is set only when they are paid
    engines taking the job because the local tier is saturated."""

    candidates: tuple[Candidate, ...]
    overflow: OverflowGrounds | None = None


@dataclass(frozen=True, slots=True)
class SlotHold:
    """Hold the job in the queue for a local slot, and look again after `retry_after_seconds`.

    Only ever planned when overflow could follow -- a paid engine with a free slot exists
    and the cap allows one -- so a job is never held for something that cannot happen.
    """

    retry_after_seconds: int
    grounds: OverflowGrounds

    @property
    def detail(self) -> str:
        occupied = ", ".join(
            f"{o.engine_id.value} {o.in_flight}/{o.slots}" for o in self.grounds.local
        )
        return (
            f"held for a local slot ({occupied}); waited "
            f"{self.grounds.waited_seconds:.0f}s of {self.grounds.overflow_after_seconds}s "
            f"before a paid engine may take it as overflow "
            f"({self.grounds.cap_remaining} of {self.grounds.paid_daily_cap} left today)"
        )


class SlotHeld(VibeyError):
    """Selection planned a hold: the job waits in the queue for a local slot."""

    def __init__(self, hold: SlotHold) -> None:
        super().__init__(hold.detail)
        self.hold = hold


@dataclass(frozen=True, slots=True)
class DispatchedSelection:
    """What a dispatched selection chose, and -- when it was paid overflow -- why."""

    engine_id: EngineId
    selection: Selection
    overflow: OverflowGrounds | None = None


class EngineDispatcher:
    """Plans which candidates a selection may offer SWRR. Pure; no state.

    Declared by `interfaces/engine_dispatch_interface.py::EngineDispatcherInterface`.
    """

    def plan(
        self,
        candidates: Sequence[Candidate],
        policy: EngineDispatchPolicy,
        load: DispatchLoad,
    ) -> DispatchPlan | SlotHold:
        if policy.mode is not DispatchMode.HYBRID:
            return DispatchPlan(preferred_tier(candidates))
        local = tuple(
            c for c in candidates if c.tier is EngineTier.LOCAL and c.effective_weight > 0
        )
        if not local:
            # No local engine can take the job at all: today's fallback, which 8.a's
            # floor already allows, unchanged and not counted as overflow.
            return DispatchPlan(preferred_tier(candidates))
        free_local = tuple(c for c in local if self._free(c, policy, load))
        if free_local:
            return DispatchPlan(free_local)
        grounds = OverflowGrounds(
            local=tuple(
                SlotOccupancy(
                    engine_id=c.engine_id,
                    in_flight=load.in_flight.get(c.engine_id, 0),
                    slots=policy.slots_for(c.engine_id, c.tier),
                )
                for c in local
            ),
            waited_seconds=load.waited_seconds,
            overflow_after_seconds=policy.overflow_after_seconds,
            paid_daily_cap=policy.paid_daily_cap,
            paid_overflow_today=load.paid_overflow_today,
        )
        paid_free = tuple(
            c
            for c in candidates
            if c.tier is not EngineTier.LOCAL
            and c.effective_weight > 0
            and self._free(c, policy, load)
        )
        if not paid_free or grounds.cap_remaining == 0:
            # Overflow cannot happen: the job waits for local, as it always has.
            return DispatchPlan(preferred_tier(candidates))
        if load.waited_seconds < policy.overflow_after_seconds:
            remaining = math.ceil(policy.overflow_after_seconds - load.waited_seconds)
            return SlotHold(
                retry_after_seconds=max(1, min(remaining, policy.slot_poll_seconds)),
                grounds=grounds,
            )
        return DispatchPlan(preferred_tier(paid_free), overflow=grounds)

    @staticmethod
    def _free(candidate: Candidate, policy: EngineDispatchPolicy, load: DispatchLoad) -> bool:
        taken = load.in_flight.get(candidate.engine_id, 0)
        return taken < policy.slots_for(candidate.engine_id, candidate.tier)


ENGINE_DISPATCHER: Final[EngineDispatcherInterface] = EngineDispatcher()
"""The one dispatcher everything shares. Stateless, so one instance serves."""


class UtcDay:
    """The UTC day an instant falls in. The cap is per UTC day (ADR-0079)."""

    def start(self, at: datetime) -> datetime:
        """Midnight UTC at the start of `at`'s day. A naive `at` is refused: a day
        boundary of an instant whose zone nobody knows is a guess."""
        if at.tzinfo is None:
            raise ValueError("a UTC day needs an aware instant")
        utc = at.astimezone(UTC)
        return utc.replace(hour=0, minute=0, second=0, microsecond=0)

    def label(self, at: datetime) -> str:
        return self.start(at).date().isoformat()


UTC_DAY: Final[UtcDayInterface] = UtcDay()


@dataclass(frozen=True, slots=True)
class LocalSession:
    """One local engine's BUILD session as the ledger recorded it: its first and last
    event for one job on that engine."""

    engine_id: EngineId
    started_at: datetime
    ended_at: datetime


@dataclass(frozen=True, slots=True)
class DispatchMeasurement:
    """One recorded measurement of local-slot contention, and the mode it chose."""

    winner: DispatchMode
    measured_at: datetime
    window_seconds: int
    sessions: int
    contended_sessions: int
    p50_contended_wait_seconds: float
    fingerprint: str
    reason: str
    algorithm: str = MEASUREMENT_ALGORITHM

    @property
    def contention(self) -> float:
        return self.contended_sessions / self.sessions if self.sessions else 0.0

    def payload(self) -> dict[str, object]:
        return {
            "winner": self.winner.value,
            "measured_at": self.measured_at.isoformat(),
            "window_seconds": self.window_seconds,
            "sessions": self.sessions,
            "contended_sessions": self.contended_sessions,
            "contention": round(self.contention, 6),
            "p50_contended_wait_seconds": round(self.p50_contended_wait_seconds, 3),
            "fingerprint": self.fingerprint,
            "reason": self.reason,
            "algorithm": self.algorithm,
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> DispatchMeasurement | None:
        """A stored measurement, or None for one this version cannot read -- an
        invalid measurement is no measurement (ADR-0074)."""
        try:
            winner = DispatchMode(str(payload["winner"]))
            measured_at = datetime.fromisoformat(str(payload["measured_at"]))
            window, sessions, contended, wait = (
                cls._number(payload[key])
                for key in (
                    "window_seconds",
                    "sessions",
                    "contended_sessions",
                    "p50_contended_wait_seconds",
                )
            )
            fingerprint = payload["fingerprint"]
            algorithm = payload["algorithm"]
        except (KeyError, ValueError):
            return None
        if (
            winner is DispatchMode.AUTO
            or measured_at.tzinfo is None
            or window is None
            or sessions is None
            or contended is None
            or wait is None
            or not isinstance(fingerprint, str)
            or not isinstance(algorithm, str)
        ):
            return None
        return cls(
            winner=winner,
            measured_at=measured_at,
            window_seconds=int(window),
            sessions=int(sessions),
            contended_sessions=int(contended),
            p50_contended_wait_seconds=wait,
            fingerprint=fingerprint,
            reason=str(payload.get("reason", "")),
            algorithm=algorithm,
        )

    @staticmethod
    def _number(value: object) -> float | None:
        # bool is an int to isinstance; a count stored as `true` is not a count.
        if isinstance(value, bool) or not isinstance(value, int | float):
            return None
        return float(value)


class DispatchMeasurementJudge:
    """Measures local-slot contention from recorded sessions, and decides whether a
    measurement is current. Pure; no state.

    The measurement is passive, over the project's own BUILD history, because the only
    experiment that could compare the two modes live is one that spends money on paid
    engines to find out -- which no unattended default may do (8.a, 8.b). A session is
    **contended** when it began while no local engine had a free slot: under `singleton`
    it queued behind the slot, and under `hybrid` it is a job that could have overflowed.
    Its **would-wait** is how long until a slot freed. `hybrid` wins only when enough
    sessions were seen, enough of them were contended, and the median contended session
    would have waited at least the overflow threshold -- otherwise hybrid would hold jobs
    and buy nothing, and `singleton` stands.
    """

    def fingerprint(
        self,
        config: EngineDispatchConfig,
        local_slots: Mapping[EngineId, int],
        implementation: str,
    ) -> str:
        """What a measurement is valid for: the local engines and their slots, every
        threshold the decision reads, the algorithm and the vibey that ran it. A change
        to any of them invalidates the measurement (ADR-0074)."""
        body = {
            "local_slots": sorted((e.value, n) for e, n in local_slots.items()),
            "overflow_after_seconds": config.overflow_after_seconds,
            "auto_window_hours": config.auto_window_hours,
            "auto_min_sessions": config.auto_min_sessions,
            "auto_min_contention": config.auto_min_contention,
            "algorithm": MEASUREMENT_ALGORITHM,
            "implementation": implementation,
        }
        encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()

    def measure(
        self,
        sessions: Sequence[LocalSession],
        *,
        local_slots: Mapping[EngineId, int],
        config: EngineDispatchConfig,
        window_end: datetime,
        fingerprint: str,
    ) -> DispatchMeasurement:
        window_seconds = config.auto_window_hours * 3600
        counted = tuple(
            s for s in sessions if s.engine_id in local_slots and s.ended_at >= s.started_at
        )
        waits = tuple(
            wait for s in counted if (wait := self._would_wait(s, counted, local_slots)) is not None
        )
        p50 = self._lower_median(waits)
        contended = len(waits)
        contention = contended / len(counted) if counted else 0.0
        if len(counted) < config.auto_min_sessions:
            winner = DispatchMode.SINGLETON
            reason = f"{len(counted)} sessions recorded, fewer than {config.auto_min_sessions}"
        elif contention < config.auto_min_contention:
            winner = DispatchMode.SINGLETON
            reason = (
                f"contention {contention:.3f} below {config.auto_min_contention:.3f}: "
                "local slots were seldom all occupied"
            )
        elif p50 < config.overflow_after_seconds:
            winner = DispatchMode.SINGLETON
            reason = (
                f"median contended wait {p50:.0f}s below the {config.overflow_after_seconds}s "
                "overflow threshold: hybrid would hold jobs and overflow none"
            )
        else:
            winner = DispatchMode.HYBRID
            reason = (
                f"contention {contention:.3f} and median contended wait {p50:.0f}s: "
                "jobs waited past the overflow threshold for a local slot"
            )
        return DispatchMeasurement(
            winner=winner,
            measured_at=window_end,
            window_seconds=window_seconds,
            sessions=len(counted),
            contended_sessions=contended,
            p50_contended_wait_seconds=p50,
            fingerprint=fingerprint,
            reason=reason,
        )

    def current(
        self,
        measurement: DispatchMeasurement | None,
        *,
        now: datetime,
        fingerprint: str,
        max_age: timedelta,
    ) -> DispatchMeasurement | None:
        """`measurement` if it may still decide, else None: missing, for another
        workload or implementation, from the future, or older than `max_age`."""
        if measurement is None or measurement.fingerprint != fingerprint:
            return None
        if measurement.algorithm != MEASUREMENT_ALGORITHM:
            return None
        age = now - measurement.measured_at
        if age < timedelta(0) or age > max_age:
            return None
        return measurement

    @staticmethod
    def _would_wait(
        session: LocalSession,
        sessions: Sequence[LocalSession],
        local_slots: Mapping[EngineId, int],
    ) -> float | None:
        """How long `session` would have waited for a local slot, or None when one was free
        as it began."""
        at = session.started_at
        frees: list[datetime] = []
        for engine_id, slots in local_slots.items():
            open_ends = sorted(
                other.ended_at
                for other in sessions
                if other is not session
                and other.engine_id is engine_id
                and other.started_at <= at < other.ended_at
            )
            if len(open_ends) < slots:
                return None
            # With n sessions open on s slots, one slot frees when n - s + 1 have ended.
            frees.append(open_ends[len(open_ends) - slots])
        # Never empty: a session is only measured when its engine is one of local_slots.
        return (min(frees) - at).total_seconds()

    @staticmethod
    def _lower_median(values: Sequence[float]) -> float:
        if not values:
            return 0.0
        ordered = sorted(values)
        return ordered[(len(ordered) - 1) // 2]


DISPATCH_MEASUREMENT_JUDGE: Final[DispatchMeasurementJudgeInterface] = DispatchMeasurementJudge()
"""The one judge everything shares. Stateless, so one instance serves."""


__all__ = [
    "DISPATCH_MEASUREMENT_JUDGE",
    "ENGINE_DISPATCHER",
    "MEASUREMENT_ALGORITHM",
    "UTC_DAY",
    "DispatchLoad",
    "DispatchMeasurement",
    "DispatchMeasurementJudge",
    "DispatchMode",
    "DispatchPlan",
    "DispatchedSelection",
    "EngineDispatchPolicy",
    "EngineDispatcher",
    "LocalSession",
    "ModeSource",
    "OverflowGrounds",
    "SlotHeld",
    "SlotHold",
    "SlotOccupancy",
    "UtcDay",
]
