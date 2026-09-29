# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Telling a person a gate is waiting -- and recording whether anyone was told.

A human gate parks a job until a person answers (ADR-0009). Before this, a gate's one
notification went out when it was raised, only if the project had opted in, and a
notification that could not go out -- the default, since `[notifications] enabled` is
false -- left no trace at all: 39 gates sat open for up to five weeks with nothing to say
that nobody had been told.

`GateNoticeService` sends one notice and records what became of it, always: delivered on
at least one channel (`GateNotified`), or undeliverable with the reason
(`GateNoticeUndeliverable`) and a warning. `GateReminder` sweeps open gates on each
project's declared schedule: a gate with no raise notice on record gets one, and a gate
still open after `remind_after_seconds` is reminded every `remind_every_seconds`, at most
`max_reminders` times. A project nobody can hear is said once per gate, at its raise
notice, and not reminded about. The worker's idle loop runs the sweep; `vibey gates
--remind` runs it on demand, so a supervisor can schedule it.

Each notice is recorded at most once per gate and notice number, fleet-wide: the ledger,
not the process, is the record, so a replayed sweep records nothing new. Delivery itself
is at-least-once -- two sweeps racing on one gate may both send before either records --
and the record is deduplicated by that identity (10.g).
"""

from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Final
from uuid import UUID

from vibey.application.dto import (
    GateReminderReport,
    HumanGateRecord,
    PlannedNotice,
    ProjectRecord,
)
from vibey.application.interfaces.gate_notices import (
    GateNoticeServiceInterface,
    GateNoticeStore,
)
from vibey.application.interfaces.gates import HumanGateRepository
from vibey.application.interfaces.observability import Logger, NotificationSink
from vibey.application.interfaces.projects import ProjectReader
from vibey.application.interfaces.system import Clock
from vibey.domain.config import ConfigError, NotificationsConfig
from vibey.domain.gate_notice import (
    DEFAULT_SWEEP_INTERVAL_SECONDS,
    NOTICE_CHANNELS,
    RAISED_NOTICE,
    GateNotice,
    NoticeReason,
    ReminderSchedule,
)
from vibey.domain.interfaces.gate_notice_interface import (
    NoticeChannelsInterface,
    ReminderScheduleInterface,
)

BUDGET_GATE_KIND: Final = "budget_exhausted"
"""The one gate kind whose notice is worded as a budget decision."""

SILENCE_DETAIL: Final[Mapping[NoticeReason, str]] = {
    NoticeReason.DISABLED: (
        "[notifications] enabled is false, so nobody will be told this gate is waiting; "
        "enable a channel, or watch `vibey gates`"
    ),
    NoticeReason.NO_CHANNEL: (
        "[notifications] is enabled with desktop alerts off and no webhook, so there is "
        "nowhere to send a notice"
    ),
    NoticeReason.UNWIRED: "this process was composed without a notification sink",
}
"""What each silent reason means, in the words the warning and the ledger carry."""


class GateNoticeService:
    """Sends one notice about one gate and records what became of it."""

    def __init__(
        self,
        *,
        sink: NotificationSink | None,
        store: GateNoticeStore | None,
        logger: Logger,
        channels: NoticeChannelsInterface = NOTICE_CHANNELS,
    ) -> None:
        self._sink = sink
        self._store = store
        self._log = logger
        self._channels = channels

    async def deliver(
        self,
        gate: HumanGateRecord,
        *,
        notice: int,
        config: Mapping[str, object] | None,
        waited_seconds: float = 0.0,
    ) -> GateNotice:
        outcome = await self._send(gate, notice=notice, config=config, waited=waited_seconds)
        await self._record(outcome)
        self._say(outcome)
        return outcome

    async def _send(
        self,
        gate: HumanGateRecord,
        *,
        notice: int,
        config: Mapping[str, object] | None,
        waited: float,
    ) -> GateNotice:
        base = GateNotice(
            project_id=gate.project_id,
            gate_id=gate.gate_id,
            gate_kind=gate.kind,
            job_id=gate.job_id,
            notice=notice,
        )
        try:
            settings = NotificationsConfig.from_data(config or {})
        except ConfigError as exc:
            return self._undeliverable(base, NoticeReason.CONFIG_INVALID, str(exc))
        silence = self._channels.silence(settings)
        if silence is not None:
            return self._undeliverable(base, silence, SILENCE_DETAIL[silence])
        if self._sink is None:
            return self._undeliverable(
                base, NoticeReason.UNWIRED, SILENCE_DETAIL[NoticeReason.UNWIRED]
            )
        kind, title, message = self._wording(gate.kind, notice=notice, waited=waited)
        try:
            result = await self._sink.notify(
                project_id=gate.project_id,
                kind=kind,
                title=title,
                message=message,
                payload={
                    "gate_id": str(gate.gate_id),
                    "gate_kind": gate.kind,
                    "job_id": str(gate.job_id) if gate.job_id is not None else None,
                    "notice": notice,
                },
                config=config,
            )
        except Exception as exc:  # noqa: BLE001 - a notification failure cannot lose a gate
            return self._undeliverable(base, NoticeReason.FAILED, repr(exc))
        failure = self._channels.undelivered(result, settings)
        if failure is not None:
            return self._undeliverable(base, NoticeReason.FAILED, failure, channels=result)
        return GateNotice(
            project_id=base.project_id,
            gate_id=base.gate_id,
            gate_kind=base.gate_kind,
            job_id=base.job_id,
            notice=notice,
            channels=dict(result),
        )

    @staticmethod
    def _undeliverable(
        base: GateNotice,
        reason: NoticeReason,
        detail: str,
        *,
        channels: Mapping[str, object] | None = None,
    ) -> GateNotice:
        return GateNotice(
            project_id=base.project_id,
            gate_id=base.gate_id,
            gate_kind=base.gate_kind,
            job_id=base.job_id,
            notice=base.notice,
            reason=reason,
            detail=detail,
            channels=dict(channels or {}),
        )

    async def _record(self, outcome: GateNotice) -> None:
        """Onto the ledger. A store that fails is said, never raised: the gate stands
        whether or not its notice's record does."""
        if self._store is None:
            return
        try:
            await self._store.record(outcome)
        except Exception as exc:  # noqa: BLE001 - recording cannot lose a gate either
            self._log.warning("gate.notice_unrecorded", **self._fields(outcome), error=repr(exc))

    def _say(self, outcome: GateNotice) -> None:
        if outcome.delivered:
            self._log.info("gate.notified", **self._fields(outcome))
            return
        self._log.warning(
            "gate.notice_undeliverable",
            **self._fields(outcome),
            reason=str(outcome.reason),
            error=outcome.detail,
        )

    def _fields(self, outcome: GateNotice) -> dict[str, object]:
        kind, _, _ = self._wording(outcome.gate_kind, notice=outcome.notice, waited=0.0)
        return {
            "project_id": str(outcome.project_id),
            "gate_id": str(outcome.gate_id),
            "gate_kind": outcome.gate_kind,
            "job_id": str(outcome.job_id) if outcome.job_id is not None else None,
            "notice": outcome.notice,
            "notification_kind": kind,
        }

    @classmethod
    def _wording(cls, gate_kind: str, *, notice: int, waited: float) -> tuple[str, str, str]:
        """The notification's kind, title and message. Gate prompts can carry model and
        tool output, so a notice never quotes one: it is a short, privacy-safe cue."""
        budget = gate_kind == BUDGET_GATE_KIND
        kind = "budget_exceeded" if budget else "human_gate_raised"
        if notice == RAISED_NOTICE:
            title = "Budget Exceeded" if budget else "Human Gate Raised"
            message = (
                "A budget decision is needed to continue."
                if budget
                else "Your response is needed to continue."
            )
            return kind, title, message
        title = "Budget Decision Still Waiting" if budget else "Human Gate Still Waiting"
        needed = "A budget decision" if budget else "Your response"
        return (
            kind,
            title,
            f"{needed} has been needed for {cls._age(waited)}; `vibey gates` lists it "
            f"(reminder {notice}).",
        )

    @staticmethod
    def _age(seconds: float) -> str:
        days = int(seconds // 86_400)
        if days >= 1:
            return f"{days} day{'' if days == 1 else 's'}"
        hours = int(seconds // 3_600)
        if hours >= 1:
            return f"{hours} hour{'' if hours == 1 else 's'}"
        return "under an hour"


class GateReminder:
    """Sweeps open gates and sends each the notice now due on its project's schedule."""

    def __init__(
        self,
        *,
        gates: HumanGateRepository,
        projects: ProjectReader,
        store: GateNoticeStore,
        notices: GateNoticeServiceInterface,
        clock: Clock,
        logger: Logger,
        interval_seconds: int = DEFAULT_SWEEP_INTERVAL_SECONDS,
        channels: NoticeChannelsInterface = NOTICE_CHANNELS,
    ) -> None:
        self._gates = gates
        self._projects = projects
        self._store = store
        self._notices = notices
        self._clock = clock
        self._log = logger
        self._interval = interval_seconds
        self._channels = channels
        self._last: dict[UUID, datetime] = {}

    async def run_if_due(self, project_id: UUID) -> GateReminderReport | None:
        now = self._clock.now()
        last = self._last.get(project_id)
        if last is not None and (now - last).total_seconds() < self._interval:
            return None
        # Claimed before the first await, so parallel drive loops sharing this sweep
        # cannot both find it due.
        self._last[project_id] = now
        return await self.run(project_id)

    async def run(
        self, project_id: UUID | None = None, *, dry_run: bool = False
    ) -> GateReminderReport:
        now = self._clock.now()
        try:
            gates, projects = await self._read(project_id)
        except Exception as exc:
            report = GateReminderReport(
                project_id=project_id, dry_run=dry_run, unreadable=(f"open gates: {exc}",)
            )
            self._log_report(report)
            return report
        named = {project.project_id: project for project in projects}
        grouped: dict[UUID, list[HumanGateRecord]] = defaultdict(list)
        for gate in gates:
            # A gate whose project was deleted between the two reads went with it.
            if gate.project_id in named:
                grouped[gate.project_id].append(gate)
        sent: list[GateNotice] = []
        planned: list[PlannedNotice] = []
        unreadable: list[str] = []
        for pid, waiting in grouped.items():
            project = named[pid]
            try:
                recorded = await self._store.recorded(pid)
            except Exception as exc:
                # 10.g: an unreadable record is reported, and nothing is sent on a guess.
                unreadable.append(f"project {project.name}: notices on record: {exc}")
                continue
            schedule, silent = self._schedule(project)
            for gate in waiting:
                waited = max((now - gate.raised_at).total_seconds(), 0.0)
                due = schedule.due(
                    waited_seconds=waited,
                    recorded=recorded.get(gate.gate_id, frozenset()),
                    silent=silent,
                )
                if due is None:
                    continue
                if dry_run:
                    planned.append(
                        PlannedNotice(
                            project_id=pid,
                            gate_id=gate.gate_id,
                            gate_kind=gate.kind,
                            notice=due,
                            waited_seconds=waited,
                        )
                    )
                    continue
                sent.append(
                    await self._notices.deliver(
                        gate, notice=due, config=project.config, waited_seconds=waited
                    )
                )
        report = GateReminderReport(
            project_id=project_id,
            dry_run=dry_run,
            waiting=sum(len(waiting) for waiting in grouped.values()),
            sent=tuple(sent),
            planned=tuple(planned),
            unreadable=tuple(unreadable),
        )
        self._log_report(report)
        return report

    async def _read(
        self, project_id: UUID | None
    ) -> tuple[Sequence[HumanGateRecord], Sequence[ProjectRecord]]:
        if project_id is None:
            # Gates first: a gate never outlives its project, so every project a gate
            # read here names is still there to be read next.
            return await self._gates.open_all(), await self._projects.list_all()
        gates = await self._gates.open_for_project(project_id)
        project = await self._projects.get(project_id)
        return gates, (project,) if project is not None else ()

    def _schedule(self, project: ProjectRecord) -> tuple[ReminderScheduleInterface, bool]:
        """The project's schedule, and whether nobody can hear it. A configuration that
        does not parse is silent: its raise notice says so (`config_invalid`)."""
        try:
            settings = NotificationsConfig.from_data(project.config)
        except ConfigError:
            return ReminderSchedule(), True
        return settings.reminders(), self._channels.silence(settings) is not None

    def _log_report(self, report: GateReminderReport) -> None:
        scope = str(report.project_id) if report.project_id is not None else "all"
        for source in report.unreadable:
            self._log.warning("gate.remind_unreadable", project_id=scope, source=source)
        if report.planned:
            self._log.info("gate.reminders_planned", project_id=scope, planned=len(report.planned))
