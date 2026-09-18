# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey ledger search`: find ledger records by id, digest, actor, time, kind or text.

The first slice of sub-doctrine 7.a (the searchable ledger, #137): an operator's
search over one project's ledger, every criterion applied by Postgres. The human
reading comes first -- one line per event, oldest first, then a line that says how
many matched and whether older matches were cut -- and `--json` is the machine
reading of the same result, second, never shaping the human one (doctrine 7).

Everything the searcher typed is checked before a connection is opened, so a typo
is a usage error (exit 2) even when the database is unreachable.
"""

import asyncio
import json
from collections.abc import Callable, Iterable
from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime, tzinfo
from typing import Annotated, Final
from uuid import UUID

import typer

from vibey.application.interfaces import LedgerSearch
from vibey.bootstrap import AppResources, build_app
from vibey.cli.interfaces.ledger_search_interface import (
    LedgerSearchCommandInterface,
    LedgerSearchPresenterInterface,
    TimeBoundParserInterface,
)
from vibey.domain.interfaces.ledger_query_interface import (
    ActorResolverInterface,
    EventKindResolverInterface,
    LedgerQueryInterface,
    LedgerSearchResultInterface,
)
from vibey.domain.ledger import LedgerEvent, LedgerEventKind, UnrecognizedEventKind
from vibey.domain.ledger_query import (
    ACTORS,
    DEFAULT_SEARCH_LIMIT,
    EVENT_KINDS,
    SELF_ACTOR,
    InvalidLedgerQuery,
    LedgerQuery,
)
from vibey.infrastructure.db.ledger_search_repository import PostgresLedgerSearchRepository

DEFAULT_DIGEST_WIDTH: Final = 12
"""How many hex characters of a digest the human line shows. Enough to tell two
payloads apart at a glance; `--json` always carries the full digest."""


class TimeBoundParser:
    """Reads ISO-8601 dates and times. A value with no zone is read in `assume`
    (UTC by default), so the same command means the same window on every machine."""

    def __init__(self, assume: tzinfo = UTC) -> None:
        self._assume = assume

    def parse(self, value: str) -> datetime:
        try:
            moment = datetime.fromisoformat(value.strip())
        except ValueError as exc:
            raise InvalidLedgerQuery(
                f"{value!r} is not an ISO-8601 date or time (e.g. 2026-09-18 or "
                "2026-09-18T14:30:00+00:00)"
            ) from exc
        if moment.utcoffset() is None:
            return moment.replace(tzinfo=self._assume)
        return moment


class LedgerSearchPresenter:
    """Renders a result as lines for a person, or as JSON for a program."""

    def __init__(self, digest_width: int = DEFAULT_DIGEST_WIDTH) -> None:
        self._digest_width = digest_width

    def human(self, result: LedgerSearchResultInterface) -> list[str]:
        if not result.events:
            return ["no events match"]
        lines = [self._line(event) for event in result.events]
        count = len(result.events)
        if result.truncated:
            lines.append(
                f"showing the latest {count}; older matches were left out -- "
                "narrow the search or raise --limit"
            )
        else:
            lines.append(f"{count} matching event{'' if count == 1 else 's'}")
        return lines

    def machine(self, project_id: UUID, result: LedgerSearchResultInterface) -> str:
        document = {
            "project_id": str(project_id),
            "truncated": result.truncated,
            "events": [self._record(event) for event in result.events],
        }
        return json.dumps(document, indent=2, default=str)

    def kind_notes(self, kinds: Iterable[LedgerEventKind]) -> list[str]:
        unrecognized = sorted(k.value for k in kinds if isinstance(k, UnrecognizedEventKind))
        return [
            f"note: {value!r} is not an event kind this vibey knows; matching it exactly "
            "as written (a newer vibey may have recorded it)"
            for value in unrecognized
        ]

    def _line(self, event: LedgerEvent) -> str:
        stamp = event.produced_at.strftime("%Y-%m-%d %H:%M:%S")
        engine = f" [{event.engine_id.value}]" if event.engine_id is not None else ""
        return (
            f"#{event.seq:<4} {stamp} [{event.phase.name}] {event.kind.value}{engine} "
            f"id={event.event_id} digest={event.digest[: self._digest_width]}"
        )

    @staticmethod
    def _record(event: LedgerEvent) -> dict[str, object]:
        return {
            "event_id": str(event.event_id),
            "project_id": str(event.project_id),
            "seq": event.seq,
            "cycle": event.cycle,
            "phase": event.phase.value,
            "kind": event.kind.value,
            "engine_id": event.engine_id.value if event.engine_id is not None else None,
            "job_id": str(event.job_id) if event.job_id is not None else None,
            "causation_id": str(event.causation_id) if event.causation_id is not None else None,
            "correlation_id": str(event.correlation_id),
            "provenance": event.provenance.value,
            "produced_at": event.produced_at.isoformat(),
            "digest": event.digest,
            "payload": event.payload,
        }


TIME_BOUNDS: Final[TimeBoundParserInterface] = TimeBoundParser()
PRESENTER: Final[LedgerSearchPresenterInterface] = LedgerSearchPresenter()


class LedgerSearchCommand:
    """Checks the options, resolves the project, searches, prints."""

    def __init__(
        self,
        *,
        actors: ActorResolverInterface = ACTORS,
        kinds: EventKindResolverInterface = EVENT_KINDS,
        bounds: TimeBoundParserInterface = TIME_BOUNDS,
        presenter: LedgerSearchPresenterInterface = PRESENTER,
        open_app: Callable[[], AbstractAsyncContextManager[AppResources]] = build_app,
    ) -> None:
        self._actors = actors
        self._kinds = kinds
        self._bounds = bounds
        self._presenter = presenter
        self._open_app = open_app

    def query(
        self,
        *,
        event_id: UUID | None,
        digest: str | None,
        actor: str | None,
        since: str | None,
        until: str | None,
        kinds: list[str],
        text: str | None,
        limit: int,
    ) -> LedgerQuery:
        try:
            return LedgerQuery(
                event_id=event_id,
                digest=digest,
                actor=None if actor is None else self._actors.resolve(actor),
                since=None if since is None else self._bounds.parse(since),
                until=None if until is None else self._bounds.parse(until),
                kinds=frozenset(self._kinds.resolve(label) for label in kinds),
                text=text,
                limit=limit,
            )
        except InvalidLedgerQuery as exc:
            # A usage error, exit 2 -- the same code typer gives its own checks.
            raise typer.BadParameter(str(exc)) from exc

    async def run(
        self, project_id: UUID | None, query: LedgerQueryInterface, *, as_json: bool
    ) -> None:
        # To stderr, so `--json` stays one parseable document on stdout.
        for note in self._presenter.kind_notes(query.kinds):
            typer.echo(note, err=True)
        async with self._open_app() as resources:
            target = await self._project(resources, project_id)
            # The pool the ledger repository already holds, the way the other
            # read commands reach it; the search needs nothing else.
            searcher: LedgerSearch = PostgresLedgerSearchRepository(resources.ledger._pool)
            result = await searcher.search(target, query)
        if as_json:
            typer.echo(self._presenter.machine(target, result))
        else:
            typer.echo("\n".join(self._presenter.human(result)))

    @staticmethod
    async def _project(resources: AppResources, project_id: UUID | None) -> UUID:
        if project_id is None:
            latest = await resources.projects.get_latest()
            if latest is None:
                typer.echo("no projects found; create one with `vibey new` first")
                raise typer.Exit(1)
            return latest.project_id
        if await resources.projects.get(project_id) is None:
            typer.echo(f"unknown project {project_id}")
            raise typer.Exit(1)
        return project_id


LEDGER_SEARCH: Final[LedgerSearchCommandInterface] = LedgerSearchCommand()
"""The command `vibey ledger search` runs. Annotated with the interface so
`mypy --strict` checks the class against its declared seam."""


def ledger_search(
    project_id: Annotated[
        UUID | None, typer.Argument(help="Project to search; defaults to the latest.")
    ] = None,
    event_id: Annotated[UUID | None, typer.Option("--id", help="Exactly this record.")] = None,
    digest: Annotated[
        str | None,
        typer.Option(
            "--digest",
            help="Records whose payload has this full SHA-256 digest. A digest names "
            "a payload, not a record, so several records can match.",
        ),
    ] = None,
    actor: Annotated[
        str | None,
        typer.Option(
            "--actor",
            help="Who produced it: an engine id, a provenance (trusted, agent, "
            f"untrusted), or {SELF_ACTOR!r} for events vibey wrote itself.",
        ),
    ] = None,
    since: Annotated[
        str | None,
        typer.Option("--since", help="Produced at or after this ISO-8601 time; no zone = UTC."),
    ] = None,
    until: Annotated[
        str | None,
        typer.Option("--until", help="Produced before this ISO-8601 time; no zone = UTC."),
    ] = None,
    kind: Annotated[
        list[str] | None,
        typer.Option(
            "--kind",
            help="Event kind, by name or value, any case. Repeat for any of several. A "
            "kind this vibey does not know (a newer one wrote it) is matched exactly.",
        ),
    ] = None,
    text: Annotated[
        str | None,
        typer.Option("--text", help="Appears in the payload's JSON text, literally, any case."),
    ] = None,
    limit: Annotated[
        int, typer.Option("--limit", "-n", min=1, help="At most this many, the latest matches.")
    ] = DEFAULT_SEARCH_LIMIT,
    as_json: Annotated[
        bool, typer.Option("--json", help="Print JSON: every field of every event.")
    ] = False,
) -> None:
    """Search the ledger by record id, digest, actor, time, kind, or payload text."""
    # A module-level function because typer builds a command's options from a
    # plain function's signature. It holds no logic; the command class does.
    query = LEDGER_SEARCH.query(
        event_id=event_id,
        digest=digest,
        actor=actor,
        since=since,
        until=until,
        kinds=kind or [],
        text=text,
        limit=limit,
    )
    asyncio.run(LEDGER_SEARCH.run(project_id, query, as_json=as_json))
