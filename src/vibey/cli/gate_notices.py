# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Gate notices at the command line: `vibey gates --remind`, and `vibey doctor`'s line.

`vibey gates --remind` runs one reminder sweep -- the one an idle worker runs every
`[notifications] sweep_interval_seconds` -- so a supervisor can schedule it where no worker
idles: every open gate with no raise notice on record gets one, and every gate its
project's schedule says is due a reminder gets it. Each notice is recorded as delivered or
undeliverable. `--dry-run` lists what is due and sends nothing. The human reading comes
first; `--json` is the same report for a program (doctrine 7). Exits 1 when any project's
notices could not be read: nothing was concluded, or sent, for it (10.g).

`vibey doctor` reports how many open gates are in projects nobody will be told about --
notifications off (the default), on with no channel, or a `[notifications]` table that does
not parse -- as `WARN`, beside the gates that will be. A report, not a failure: the gates
are still listed by `vibey gates`.
"""

import json
import os
from collections import Counter
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass
from typing import Final
from uuid import UUID

import asyncpg
import typer

from vibey.application.dto import GateReminderReport, ProjectRecord
from vibey.application.interfaces.gates import HumanGateRepository
from vibey.application.interfaces.projects import ProjectReader
from vibey.bootstrap import AppResources, build_app
from vibey.cli.interfaces.gate_notices_interface import (
    GateNoticeDoctorInterface,
    GateReadersOpenerInterface,
    GateRemindersCommandInterface,
    GateRemindersPresenterInterface,
)
from vibey.domain.config import ConfigError, NotificationsConfig
from vibey.domain.gate_notice import NOTICE_CHANNELS, NoticeReason
from vibey.domain.interfaces.gate_notice_interface import NoticeChannelsInterface
from vibey.infrastructure.db.human_gate_repository import PostgresHumanGateRepository
from vibey.infrastructure.db.project_repository import PostgresProjectRepository

CHECK_NAME: Final = "gate-notices"

REASON_WORDS: Final = {
    NoticeReason.DISABLED: "notifications disabled",
    NoticeReason.NO_CHANNEL: "notifications on, but no channel",
    NoticeReason.CONFIG_INVALID: "[notifications] does not parse",
}


class GateRemindersPresenter:
    """Renders one reminder sweep for a person, or as JSON for a program."""

    def lines(self, report: GateReminderReport) -> list[str]:
        verb = "due" if report.dry_run else "sent"
        count = len(report.planned) if report.dry_run else len(report.sent)
        lines = [
            f"{report.waiting} open gate{'' if report.waiting == 1 else 's'}; "
            f"{count} notice{'' if count == 1 else 's'} {verb}"
        ]
        for planned in report.planned:
            lines.append(
                f"  due     {self._label(planned.notice)} gate {planned.gate_id} "
                f"({planned.gate_kind}), waiting {int(planned.waited_seconds // 3600)}h"
            )
        for notice in report.sent:
            outcome = "told" if notice.delivered else f"UNDELIVERABLE ({notice.reason})"
            lines.append(
                f"  {outcome:<7} {self._label(notice.notice)} gate {notice.gate_id} "
                f"({notice.gate_kind})"
            )
            if not notice.delivered and notice.detail:
                lines.append(f"          {notice.detail}")
        for source in report.unreadable:
            lines.append(f"  UNREADABLE {source}: nothing was sent for it")
        return lines

    def json(self, report: GateReminderReport) -> str:
        return json.dumps(
            {
                "project_id": str(report.project_id) if report.project_id is not None else None,
                "dry_run": report.dry_run,
                "waiting": report.waiting,
                "sent": [
                    {
                        **notice.payload(),
                        "project_id": str(notice.project_id),
                        "delivered": notice.delivered,
                    }
                    for notice in report.sent
                ],
                "planned": [
                    {
                        "project_id": str(planned.project_id),
                        "gate_id": str(planned.gate_id),
                        "gate_kind": planned.gate_kind,
                        "notice": planned.notice,
                        "waited_seconds": planned.waited_seconds,
                    }
                    for planned in report.planned
                ],
                "unreadable": list(report.unreadable),
                "ok": report.ok,
            },
            indent=2,
        )

    @staticmethod
    def _label(notice: int) -> str:
        return "raise notice" if notice == 0 else f"reminder {notice}"


GATE_REMINDERS_PRESENTER: Final[GateRemindersPresenterInterface] = GateRemindersPresenter()


class GateRemindersCommand:
    """Runs one reminder sweep -- every project's, or one project's -- and prints it."""

    def __init__(
        self,
        *,
        presenter: GateRemindersPresenterInterface = GATE_REMINDERS_PRESENTER,
        open_app: Callable[[], AbstractAsyncContextManager[AppResources]] = build_app,
    ) -> None:
        self._presenter = presenter
        self._open_app = open_app

    async def run(self, project_id: UUID | None, *, as_json: bool, dry_run: bool) -> None:
        async with self._open_app() as resources:
            if project_id is not None and await resources.projects.get(project_id) is None:
                # stderr, so a `--json` reader's stdout is never anything but JSON.
                typer.echo(f"unknown project {project_id}", err=True)
                raise typer.Exit(1)
            report = await resources.gate_reminder.run(project_id, dry_run=dry_run)
        if as_json:
            typer.echo(self._presenter.json(report))
        else:
            typer.echo("\n".join(self._presenter.lines(report)))
        if not report.ok:
            raise typer.Exit(1)


GATE_REMINDERS: Final[GateRemindersCommandInterface] = GateRemindersCommand()


@dataclass(frozen=True, slots=True)
class GateReaders:
    """What the doctor line reads: the open gates and the projects they belong to."""

    gates: HumanGateRepository
    projects: ProjectReader


class GateReadersOpener:
    """Opens the two readers over a pool of their own. Not `build_app`: a doctor run must
    not migrate, start the bus's weekly benchmark, or compose anything else it will not
    use -- it reads two tables and closes."""

    @asynccontextmanager
    async def open(self, dsn: str) -> AsyncIterator[GateReaders]:
        pool = await asyncpg.create_pool(dsn, min_size=1, max_size=2)
        try:
            yield GateReaders(
                gates=PostgresHumanGateRepository(pool),
                projects=PostgresProjectRepository(pool),
            )
        finally:
            await pool.close()


GATE_READERS: Final[GateReadersOpenerInterface] = GateReadersOpener()


class GateNoticeDoctor:
    """`vibey doctor`'s gate-notices line: how many open gates nobody will be told about."""

    def __init__(
        self,
        *,
        readers: GateReadersOpenerInterface = GATE_READERS,
        channels: NoticeChannelsInterface = NOTICE_CHANNELS,
        environ: Callable[[], dict[str, str]] = lambda: dict(os.environ),
    ) -> None:
        self._readers = readers
        self._channels = channels
        self._environ = environ

    async def line(self) -> str:
        dsn = self._environ().get("VIBEY_PG_URL", "").strip()
        if not dsn:
            return f"UNKNOWN {CHECK_NAME:<20} VIBEY_PG_URL is not set; no gates to count"
        try:
            async with self._readers.open(dsn) as readers:
                gates = await readers.gates.open_all()
                projects = await readers.projects.list_all()
        except Exception as exc:
            return f"UNKNOWN {CHECK_NAME:<20} could not read the open gates: {exc}"
        names = {project.project_id: project.name for project in projects}
        waiting = [gate for gate in gates if gate.project_id in names]
        if not waiting:
            return f"PASS {CHECK_NAME:<20} no open gates"
        reasons: dict[UUID, NoticeReason] = {}
        for project in projects:
            reason = self._silence(project)
            if reason is not None:
                reasons[project.project_id] = reason
        silent = Counter(gate.project_id for gate in waiting if gate.project_id in reasons)
        total = len(waiting)
        if not silent:
            return (
                f"PASS {CHECK_NAME:<20} {total} gate{'' if total == 1 else 's'} waiting; "
                "every one's project has a notification channel"
            )
        count = sum(silent.values())
        told = total - count
        where = ", ".join(
            f"{names[pid]} {n} ({REASON_WORDS[reasons[pid]]})"
            for pid, n in sorted(silent.items(), key=lambda item: names[item[0]])
        )
        rest = f"; {told} more will be" if told else ""
        return (
            f"WARN {CHECK_NAME:<20} {count} gate{'' if count == 1 else 's'} waiting, "
            f"nobody will be told{rest}: {where}. Set [notifications] enabled = true with "
            "desktop alerts or a webhook, or watch `vibey gates`"
        )

    def _silence(self, project: ProjectRecord) -> NoticeReason | None:
        try:
            return self._channels.silence(NotificationsConfig.from_data(project.config))
        except ConfigError:
            return NoticeReason.CONFIG_INVALID


GATE_NOTICE_DOCTOR: Final[GateNoticeDoctorInterface] = GateNoticeDoctor()
