# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey state`: this database and its sealed copy on GitHub, kept the same (ADR-0086).

- `vibey state sync` merges this database with the repository's `vibey-state` branch, both
  ways, and writes the result to each end that differs; `--every N` does so every N seconds
  and is what `vibey supervisor` keeps running; `--no-push` writes only here.
- `vibey state status` says what a sync would pull and push, and writes nothing.
- `vibey state export --out FILE` / `vibey state import FILE` carry a sealed copy of this
  database, with the commit it last synced with, to an empty one (a runner's).
- `vibey state forget` drops the commit this database last synced with, so the next sync
  merges the two ends as a first one would. Only for a branch that was rewritten.
- `vibey state key` says where the state key is; `--new` makes one; `--show` prints it, to
  give to another machine or to the repository's `VIBEY_STATE_KEY` secret.

Settings are `VIBEY_STATE_*` (`StateSyncSettingsLoader`). Exit codes: 0 done or in sync; 1
a conflict, a refusal or a failure, each said on stderr; 2 a setting that cannot be used.
"""

import asyncio
import json
import os
import sys
import time
from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Final, TextIO, TypeVar

import typer

from vibey.application.interfaces.state_sync import StateSyncServiceInterface
from vibey.application.state_sync import StateSyncService
from vibey.cli.interfaces.state_interface import StateCommandInterface
from vibey.domain.errors import VibeyError
from vibey.domain.state_sync import SnapshotCodec, SyncReport, SyncState
from vibey.infrastructure.state.aes_gcm_cipher import AesGcmStateCipher
from vibey.infrastructure.state.gh_state_remote import GhStateRemote
from vibey.infrastructure.state.interfaces.state_key_interface import StateKeyStoreInterface
from vibey.infrastructure.state.postgres_state_store import PostgresStateStore
from vibey.infrastructure.state.settings import StateSyncSettingsLoader
from vibey.infrastructure.state.state_key import StateKeyStore

EXIT_FAILED: Final = 1
EXIT_SETTING: Final = 2

T = TypeVar("T")
ServiceFactory = Callable[[Mapping[str, str]], Awaitable[StateSyncServiceInterface]]
KeyStoreFactory = Callable[[Mapping[str, str]], StateKeyStoreInterface]


async def default_service(environ: Mapping[str, str]) -> StateSyncServiceInterface:
    """The service over this machine's database, key and branch. Module-level: it is the
    composition the command class is given by default, and replaced in its tests."""
    settings = StateSyncSettingsLoader().load(environ)
    cipher = AesGcmStateCipher(StateKeyStore(settings).load())
    remote = await GhStateRemote.resolve(settings)
    return StateSyncService(
        PostgresStateStore(settings.pg_url, specs=settings.tables),
        remote,
        cipher,
        codec=SnapshotCodec(settings.tables),
        attempts=settings.attempts,
    )


def default_key_store(environ: Mapping[str, str]) -> StateKeyStoreInterface:
    """This machine's key store. Module-level for the same reason as `default_service`."""
    return StateKeyStore(StateSyncSettingsLoader().load(environ))


class StateCommand(StateCommandInterface):
    """Implements `interfaces/state_interface.py::StateCommandInterface`."""

    def __init__(
        self,
        *,
        environ: Mapping[str, str] | None = None,
        service: ServiceFactory = default_service,
        key_store: KeyStoreFactory = default_key_store,
        out: TextIO | None = None,
        err: TextIO | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._environ = environ
        self._service = service
        self._key_store = key_store
        self._out = out
        self._err = err
        self._sleep = sleep
        self._clock = clock

    @property
    def _stdout(self) -> TextIO:
        return self._out or sys.stdout

    @property
    def _stderr(self) -> TextIO:
        return self._err or sys.stderr

    def _env(self) -> Mapping[str, str]:
        return self._environ if self._environ is not None else os.environ

    def _with_service(
        self, act: Callable[[StateSyncServiceInterface], Awaitable[T]]
    ) -> tuple[int, T | None]:
        """Runs `act` on a fresh service; a refusal or a bad setting is said, not raised."""

        async def go() -> T:
            return await act(await self._service(self._env()))

        try:
            return 0, asyncio.run(go())
        except ValueError as bad:
            print(f"vibey state: {bad}", file=self._stderr)
            return EXIT_SETTING, None
        except VibeyError as refused:
            print(f"vibey state: {refused}", file=self._stderr)
            return EXIT_FAILED, None

    def _said(self, report: SyncReport) -> int:
        stream = self._stderr if report.state is SyncState.CONFLICT else self._stdout
        print(report.describe(), file=stream)
        return EXIT_FAILED if report.state is SyncState.CONFLICT else 0

    def sync(self, *, push: bool = True, every: float | None = None, rounds: int = 0) -> int:
        """One sync, or with `every`, one every `every` seconds: `rounds` of them, or for as
        long as the process lives. A failed round is said and the next one runs."""
        if every is not None and every <= 0:
            print("vibey state: --every is a number of seconds above 0", file=self._stderr)
            return EXIT_SETTING
        done = 0
        while True:
            code, report = self._with_service(lambda service: service.sync(push=push))
            if report is not None:
                if every is not None:
                    print(self._clock().isoformat(timespec="seconds"), end=" ", file=self._stdout)
                code = self._said(report)
            done += 1
            if every is None or done == rounds:
                return code
            self._sleep(every)

    def status(self, *, as_json: bool = False) -> int:
        code, report = self._with_service(lambda service: service.status())
        if report is None:
            return code
        if not as_json:
            return self._said(report)
        print(
            json.dumps(
                {
                    "state": report.state.value,
                    "remote": report.remote,
                    "commit": report.commit,
                    "rows": report.rows,
                    "to_pull": report.pulled,
                    "to_push": report.to_push,
                    "conflicts": [c.describe() for c in report.conflicts],
                },
                sort_keys=True,
            ),
            file=self._stdout,
        )
        return EXIT_FAILED if report.state is SyncState.CONFLICT else 0

    def export(self, path: Path) -> int:
        code, sealed = self._with_service(lambda service: service.export())
        if sealed is None:
            return code
        path.parent.mkdir(parents=True, exist_ok=True)
        partial = path.with_name(path.name + ".partial")
        descriptor = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(sealed)
        partial.replace(path)
        print(f"vibey state: exported, sealed, to {path}", file=self._stdout)
        return 0

    def import_(self, path: Path) -> int:
        if not path.is_file():
            print(f"vibey state: no export at {path}", file=self._stderr)
            return EXIT_FAILED
        sealed = path.read_bytes()
        code, report = self._with_service(lambda service: service.restore(sealed))
        return code if report is None else self._said(report)

    def forget(self) -> int:
        async def forgotten(service: StateSyncServiceInterface) -> bool:
            await service.forget()
            return True

        code, done = self._with_service(forgotten)
        if done:
            print(
                "vibey state: forgot the commit this database last synced with; the next sync "
                "merges both ends as a first one",
                file=self._stdout,
            )
        return code

    def key(self, *, new: bool = False, show: bool = False) -> int:
        try:
            store = self._key_store(self._env())
            if new:
                where = store.create()
                print(
                    f"vibey state: made a state key, kept in {where}. Give it to another "
                    "machine as VIBEY_STATE_KEY, or to a private repository's runners with "
                    "`vibey state key --show | gh secret set VIBEY_STATE_KEY`. Losing it loses "
                    "every state sealed under it.",
                    file=self._stderr,
                )
                return 0
            if show:
                print(store.text(), file=self._stdout)
                return 0
            where = store.where()
        except ValueError as bad:
            print(f"vibey state: {bad}", file=self._stderr)
            return EXIT_SETTING
        except VibeyError as missing:
            print(f"vibey state: {missing}", file=self._stderr)
            return EXIT_FAILED
        if not where:
            print(
                "vibey state: no state key here; `vibey state key --new` makes one",
                file=self._stderr,
            )
            return EXIT_FAILED
        print(f"vibey state: the state key is in {where}", file=self._stdout)
        return 0


STATE: Final[StateCommandInterface] = StateCommand()
"""What `vibey state` runs. Annotated with the interface so `mypy --strict` checks the class
against its declared seam."""

state_app = typer.Typer(
    name="state",
    help="Keep this database and its sealed copy on GitHub the same (ADR-0086).",
    no_args_is_help=True,
)


@state_app.command("sync")
def sync_cmd(
    no_push: Annotated[
        bool, typer.Option("--no-push", help="Pull and merge here; never write the branch.")
    ] = False,
    every: Annotated[
        float | None,
        typer.Option("--every", help="Sync every this many seconds, for as long as it runs."),
    ] = None,
) -> None:
    """Merge this database with the state branch, both ways, and write each end that differs."""
    raise typer.Exit(STATE.sync(push=not no_push, every=every))


@state_app.command("status")
def status_cmd(
    as_json: Annotated[bool, typer.Option("--json", help="One JSON object.")] = False,
) -> None:
    """What a sync would pull and push. Writes nothing."""
    raise typer.Exit(STATE.status(as_json=as_json))


@state_app.command("export")
def export_cmd(
    out: Annotated[Path, typer.Option("--out", help="Where to write the sealed export.")],
) -> None:
    """This database, sealed, with the commit it last synced with."""
    raise typer.Exit(STATE.export(out))


@state_app.command("import")
def import_cmd(path: Annotated[Path, typer.Argument(help="A sealed export.")]) -> None:
    """Load a sealed export into this database, which must hold no rows."""
    raise typer.Exit(STATE.import_(path))


@state_app.command("forget")
def forget_cmd() -> None:
    """Forget the commit this database last synced with."""
    raise typer.Exit(STATE.forget())


@state_app.command("key")
def key_cmd(
    new: Annotated[bool, typer.Option("--new", help="Make a key; refused if one exists.")] = False,
    show: Annotated[bool, typer.Option("--show", help="Print the key, and only the key.")] = False,
) -> None:
    """Where the state key is; or make one; or print it."""
    raise typer.Exit(STATE.key(new=new, show=show))
