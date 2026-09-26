# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Failover to the sovereign engine, and handback after a recorded probe (ADR-0070).

When a paid engine -- a vibey BUILD engine, or the driver itself (the Claude Code
session steering the work) -- runs out of capacity, the work continues on the
sovereign engine at ULTRA effort instead of waiting. When the paid engine answers
again, the work goes back to it. This module is the pure half of both directions:

- **Classify.** Claude Code's `StopFailure` hook names the error type
  (code.claude.com/docs/en/hooks#stopfailure). `rate_limit` is a window that
  reopens -- `WindowExhausted`; `billing_error` is a credits balance --
  `CreditsExhausted`, which has no `resets_at` and never gains one. Every other type
  is not a capacity rejection and plans no failover.
- **Plan.** A capacity rejection plans a failover to the configured target at the
  configured effort, with the earliest time a probe may run. A window's stated
  `resets_at` only *schedules* that probe; nothing in it hands anything back.
- **Project.** The failover's state is read from its own records, never held
  elsewhere: the latest failover, and the probes and handbacks recorded after it.
  Only trusted records count.
- **Hand back only on evidence (sub-doctrine 10.f).** A handback is allowed only when
  a successful probe is recorded after the latest failover. A clock reaching
  `resets_at` is not evidence that the paid engine answers.
"""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Final

from vibey.domain.capacity import (
    AuthenticationFailed,
    Available,
    CapacityState,
    CreditsExhausted,
    WindowExhausted,
)
from vibey.domain.effort import Effort


class FailoverKind(StrEnum):
    """The three records a failover writes, in the order they happen."""

    FAILED_OVER = "EngineFailedOver"
    PROBED = "EngineProbed"
    HANDED_BACK = "EngineHandedBack"


class FailoverCause(StrEnum):
    WINDOW = "window"
    CREDITS = "credits"


DEFAULT_TARGET_ENGINE: Final = "gptossloop"
DEFAULT_PROBE_INTERVAL: Final = timedelta(minutes=30)


@dataclass(frozen=True, slots=True)
class FailoverSettings:
    """The `[failover]` keys (docs/reference/configuration.md). Every one is a key."""

    enabled: bool = True
    target_engine: str = DEFAULT_TARGET_ENGINE
    target_effort: Effort = Effort.ULTRA
    probe_interval: timedelta = DEFAULT_PROBE_INTERVAL
    # argv templates for the driver: {brief}, {cwd}, {run_id}, {session_id}, {prompt}
    sovereign_argv: tuple[str, ...] = (
        "gptossloop",
        "run",
        "{brief}",
        "--run-id",
        "{run_id}",
        "--cwd",
        "{cwd}",
    )
    sovereign_wind_down_argv: tuple[str, ...] = (
        "gptossloop",
        "wind-down",
        "{run_id}",
        "--cwd",
        "{cwd}",
    )
    probe_argv: tuple[str, ...] = (
        "claude",
        "-p",
        "Reply with the single word OK.",
        "--output-format",
        "json",
        "--max-turns",
        "1",
    )
    resume_argv: tuple[str, ...] = ("claude", "-p", "--resume", "{session_id}", "{prompt}")

    def __post_init__(self) -> None:
        if self.probe_interval <= timedelta(0):
            raise ValueError("[failover] probe_interval_seconds must be positive")
        if not self.target_engine:
            raise ValueError("[failover] target_engine must name an engine")


@dataclass(frozen=True, slots=True)
class FailoverPlan:
    target_engine: str
    effort: Effort
    cause: FailoverCause
    probe_not_before: datetime


@dataclass(frozen=True, slots=True)
class FailoverRecord:
    """One record of a failover, whichever ledger holds it."""

    kind: FailoverKind
    at: datetime
    payload: Mapping[str, object] = field(default_factory=dict)
    trusted: bool = True


@dataclass(frozen=True, slots=True)
class FailoverStatus:
    active: bool
    failover: FailoverRecord | None
    probe_ok: FailoverRecord | None
    """The first successful probe recorded after the latest failover, if any."""

    def probe_due(self, now: datetime) -> bool:
        """A probe may run: a failover is active and its scheduled time has come."""
        if not self.active or self.failover is None:
            return False
        not_before = self.failover.payload.get("probe_not_before")
        if not isinstance(not_before, str):
            return True
        return now >= datetime.fromisoformat(not_before)

    @property
    def may_hand_back(self) -> bool:
        return self.active and self.probe_ok is not None


class CapacitySignalClassifier:
    """Maps a Claude Code `StopFailure` error type onto a capacity state."""

    WINDOW_ERRORS: Final = frozenset({"rate_limit"})
    CREDIT_ERRORS: Final = frozenset({"billing_error"})
    AUTH_ERRORS: Final = frozenset(
        {"authentication_failed", "oauth_org_not_allowed", "account_on_hold"}
    )

    def classify(self, error: str, detail: str = "") -> CapacityState:
        if error in self.WINDOW_ERRORS:
            return WindowExhausted(resets_at=None, rate_limit_type=error)
        if error in self.CREDIT_ERRORS:
            # No resets_at: a credits balance has no clock (CLAUDE.md, non-negotiable).
            return CreditsExhausted()
        if error in self.AUTH_ERRORS:
            return AuthenticationFailed(detail=detail or error)
        return Available()


class FailoverPolicy:
    """Plans failovers and reads their state from records. Pure."""

    def plan(
        self, state: CapacityState, *, now: datetime, settings: FailoverSettings
    ) -> FailoverPlan | None:
        if not settings.enabled:
            return None
        match state:
            case WindowExhausted(resets_at=resets_at):
                # resets_at only schedules the probe; the probe decides the handback.
                not_before = resets_at if resets_at is not None else now + settings.probe_interval
                cause = FailoverCause.WINDOW
            case CreditsExhausted():
                not_before = now + settings.probe_interval
                cause = FailoverCause.CREDITS
            case _:
                return None
        return FailoverPlan(
            target_engine=settings.target_engine,
            effort=settings.target_effort,
            cause=cause,
            probe_not_before=not_before,
        )

    def status(self, records: Iterable[FailoverRecord]) -> FailoverStatus:
        failover: FailoverRecord | None = None
        probe_ok: FailoverRecord | None = None
        handed_back = False
        for record in records:
            if not record.trusted:
                continue
            if record.kind is FailoverKind.FAILED_OVER:
                failover, probe_ok, handed_back = record, None, False
            elif failover is None:
                continue
            elif record.kind is FailoverKind.PROBED:
                if (
                    probe_ok is None
                    and record.payload.get("ok") is True
                    and self._probed_the_exhausted_engine(failover, record)
                ):
                    probe_ok = record
            else:
                handed_back = True
        return FailoverStatus(
            active=failover is not None and not handed_back,
            failover=failover,
            probe_ok=probe_ok,
        )

    @staticmethod
    def _probed_the_exhausted_engine(failover: FailoverRecord, probe: FailoverRecord) -> bool:
        """When the failover names the engine that ran out, only a probe of that
        engine is evidence it answers again."""
        exhausted = failover.payload.get("from_engine")
        return exhausted is None or probe.payload.get("engine") == exhausted

    def outranks_completion(self, capacity: CapacityState) -> bool:
        """Whether this state overrides any completion claim made in the same turn:
        a capacity rejection always outranks a completion claim (CLAUDE.md)."""
        return isinstance(capacity, (WindowExhausted, CreditsExhausted))

    def read_rows(self, rows: Sequence[Mapping[str, object]]) -> tuple[FailoverRecord, ...]:
        """Reads stored rows into records; a kind this version does not know is skipped,
        as a newer vibey's row is kept but not interpreted (the ledger's own rule)."""
        known = {kind.value: kind for kind in FailoverKind}
        out: list[FailoverRecord] = []
        for row in rows:
            kind = known.get(str(row.get("kind")))
            at = row.get("at")
            payload = row.get("payload")
            if kind is None or not isinstance(at, str) or not isinstance(payload, Mapping):
                continue
            out.append(
                FailoverRecord(
                    kind=kind,
                    at=datetime.fromisoformat(at),
                    payload=dict(payload),
                    trusted=row.get("trusted", True) is True,
                )
            )
        return tuple(out)


FAILOVER_POLICY: Final = FailoverPolicy()
CAPACITY_SIGNALS: Final = CapacitySignalClassifier()
