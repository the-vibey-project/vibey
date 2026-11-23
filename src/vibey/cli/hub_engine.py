# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey hub start | stop | status`: the one hub on this computer, from a command (#1186).

Every krypton UI offers the same three actions -- start, stop, status -- and they all end
up here, so the desktop app, the VS Code extension and a terminal agree on one rule:

- **There is one hub per user.** `vibey serve` refuses to start a second (it holds
  `<state_dir>/serve.lock`), and `start` here is idempotent: a hub that already runs is
  reported, not duplicated.
- **Closing a UI never stops the hub.** `start` launches it detached, in its own session,
  with its output in `<state_dir>/hub.log`. Only `stop` ends it, and `stop` sends SIGTERM
  so the hub shuts down cleanly and clears its own record. It never sends SIGKILL; a hub
  that is slow to stop is reported as still stopping.

- **Your own hub, never a folder's** (SP-ACP Task 11a). `[hub]` -- the state folder, so the
  tokens, the record and the lock -- comes from your own `vibey.toml`, in your configuration
  folder (`bootstrap.acp_user_config`), never the folder the command runs in, which may be a
  cloned repository's. `start` launches `vibey serve` in that configuration folder, so the hub
  reads the same `[hub]`.
- **A signal goes only to the hub's lock holder.** Whether a hub runs is read from
  `<state_dir>/serving.json` (the hub's record) and asked of the hub's own lock,
  `<state_dir>/serve.lock` (`ServeLock.held_by`), never of a pid alone, which may have been
  reused or planted: a record whose lock nobody holds is stale, one whose lock another process
  holds is refused (exit 1), and `stop` signals only the process that holds the lock and wrote
  the pid the record names. A record naming pid -1, 0 or 1, or a port outside 1..65535, is
  malformed (`LocalTokenStore.serving`).
- **A hub starting over a stale record is starting** (SP-ACP Task 11b). A hub takes its lock
  before it replaces an earlier hub's record, so for a moment the lock's holder and the record
  disagree. When the holder has not written its pid yet, or the record's pid is no longer alive,
  that is a hub starting, not a conflict: `status` says so (exit 3), `stop` signals nothing
  (exit 1), and `start` waits for that hub instead of launching another. A live pid in the
  record and another pid on the lock is still refused as a disagreement (exit 1).
"""

import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Final, NoReturn

import typer

from vibey.bootstrap import acp_user_config
from vibey.cli.interfaces.hub_engine_interface import HubEngineCommandInterface
from vibey.domain.config import ConfigError
from vibey.infrastructure.hub.interfaces.processes_interface import HubProcessesInterface
from vibey.infrastructure.hub.interfaces.settings_interface import HubSettingsLoaderInterface
from vibey.infrastructure.hub.local_token import LocalTokenStore, ServingRecord
from vibey.infrastructure.hub.processes import HUB_PROCESSES
from vibey.infrastructure.hub.serve_lock import ServeLock
from vibey.infrastructure.hub.settings import HUB_SETTINGS, HubSettings

EXIT_NOT_RUNNING: Final = 3
"""The exit code of `status` when no hub runs, as `vibey hub pair` uses for the same fact."""

LOG_FILE: Final = "hub.log"
POLL_SECONDS: Final = 0.1
DEFAULT_TIMEOUT: Final = 15.0


@dataclass(frozen=True, slots=True)
class HubStarting:
    """A hub holding the lock that has not yet replaced an earlier hub's record. A value type."""

    pid: int
    """The pid the holder wrote, or 0 while it has not written one."""

    def describe(self) -> str:
        if self.pid:
            return f"a hub (pid {self.pid}) is starting"
        return "a hub is starting (its pid is not written yet)"


class HubEngineCommand:
    """Starts, stops and reports the hub.

    Declared by `interfaces/hub_engine_interface.py::HubEngineCommandInterface`."""

    def __init__(
        self,
        *,
        settings: HubSettingsLoaderInterface = HUB_SETTINGS,
        config_path: Callable[[], Path] = lambda: acp_user_config(),
        processes: HubProcessesInterface = HUB_PROCESSES,
        argv: Sequence[str] = (
            sys.executable,
            "-c",
            "from vibey.cli.main import run; run(['serve'])",
        ),
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        holder: Callable[[Path], int | None] = lambda state: ServeLock(state).held_by(),
    ) -> None:
        self._holder = holder
        self._settings = settings
        self._config_path = config_path
        self._processes = processes
        self._argv = argv
        self._sleep = sleep
        self._clock = clock

    def status(self) -> None:
        running = self._running(self._load())
        if isinstance(running, HubStarting):
            typer.echo(f"{running.describe()}; it is not ready yet")
            raise typer.Exit(EXIT_NOT_RUNNING)
        if running is None:
            raise typer.Exit(EXIT_NOT_RUNNING)
        typer.echo(self._describe(running))

    def start(self, timeout: float) -> None:
        settings = self._load()
        running = self._running(settings)
        if isinstance(running, ServingRecord):
            typer.echo(f"hub already running: {self._describe(running)}")
            return
        if isinstance(running, HubStarting):
            # Another start launched it: wait for that hub, never launch a second.
            typer.echo(f"{running.describe()}; waiting for it")
            pid = running.pid
        else:
            # In your configuration folder: the hub reads the `[hub]` this command just read.
            pid = self._processes.spawn(
                self._argv, settings.state_dir / LOG_FILE, cwd=self._config_path().parent
            )
        # Waiting on a starting hub that had written no pid yet: its lock is all there is to
        # watch until it writes one (SP-ACP Task 11b, review N-3).
        unwritten = pid == 0
        deadline = self._clock() + timeout
        while self._clock() < deadline:
            running = self._running(settings, quiet=True)
            if isinstance(running, ServingRecord):
                note = "" if running.pid == pid else " (another process won the start)"
                typer.echo(f"hub started: {self._describe(running)}{note}")
                return
            if unwritten and not pid:
                holder = self._holder(settings.state_dir)
                if holder is None:
                    self._exited(settings)  # its lock dropped: the hub it named is gone
                pid = holder or 0  # 0 while the holder has still not written its pid
            if pid and not self._processes.alive(pid):
                self._exited(settings)
            self._sleep(POLL_SECONDS)
        still = f"pid {pid} is still starting" if pid else "the hub is still starting"
        typer.echo(
            f"the hub did not come up within {timeout:g}s ({still}); "
            f"see {settings.state_dir / LOG_FILE}",
            err=True,
        )
        raise typer.Exit(1)

    @staticmethod
    def _exited(settings: HubSettings) -> NoReturn:
        typer.echo(
            f"the hub exited before it was ready; see {settings.state_dir / LOG_FILE}", err=True
        )
        raise typer.Exit(1)

    def stop(self, timeout: float) -> None:
        settings = self._load()
        running = self._running(settings)
        if isinstance(running, HubStarting):
            typer.echo(
                f"{running.describe()} and has not written its record yet, so nothing was "
                "signalled; run `vibey hub stop` again once it is up",
                err=True,
            )
            raise typer.Exit(1)
        if running is None:
            typer.echo("hub is not running")
            return
        self._processes.terminate(running.pid)
        deadline = self._clock() + timeout
        while self._clock() < deadline:
            if not self._processes.alive(running.pid):
                typer.echo(f"hub stopped (pid {running.pid})")
                return
            self._sleep(POLL_SECONDS)
        typer.echo(
            f"the hub (pid {running.pid}) has not stopped within {timeout:g}s; it was asked to "
            "stop and is not being forced",
            err=True,
        )
        raise typer.Exit(1)

    def _load(self) -> HubSettings:
        try:
            return self._settings.load(self._config_path())
        except ConfigError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(2) from exc

    def _running(
        self, settings: HubSettings, *, quiet: bool = False
    ) -> ServingRecord | HubStarting | None:
        """The hub's record when the process holding the hub's lock is the one it names; None,
        saying why unless `quiet`, when there is no record, it is malformed, or no process holds
        the lock (stale). `HubStarting` when the lock's holder has not yet replaced an earlier
        hub's record: it has written no pid yet, or the record's pid is no longer alive. A lock
        held by another process while the record's pid lives is refused (exit 1) unless
        `quiet`."""
        try:
            record = LocalTokenStore(settings.state_dir).serving()
        except ValueError as exc:
            if not quiet:
                typer.echo(f"hub record unreadable: {exc}", err=True)
            return None
        if record is None:
            if not quiet:
                typer.echo("hub is not running")
            return None
        holder = self._holder(settings.state_dir)
        if holder is None:
            if not quiet:
                typer.echo(f"hub is not running (stale record from pid {record.pid})")
            return None
        if holder != record.pid:
            if holder == 0 or not self._processes.alive(record.pid):
                return HubStarting(holder)
            if quiet:
                return None  # a hub starting now holds the lock before it writes its record
            typer.echo(
                f"the hub's lock is held by pid {holder}, but its record names pid {record.pid}: "
                "the two disagree, so nothing was signalled or trusted",
                err=True,
            )
            raise typer.Exit(1)
        return record

    @staticmethod
    def _describe(record: ServingRecord) -> str:
        host = f"[{record.host}]" if ":" in record.host else record.host
        scheme = "https" if record.tls else "http"
        return f"{scheme}://{host}:{record.port}/api/v1 (pid {record.pid})"


HUB_ENGINE: Final[HubEngineCommandInterface] = HubEngineCommand()


def status() -> None:
    """Say whether the hub runs on this computer, and where. Exit 3 when it does not."""
    HUB_ENGINE.status()


def start(
    timeout: Annotated[
        float, typer.Option("--timeout", help="Seconds to wait for the hub to come up.")
    ] = DEFAULT_TIMEOUT,
) -> None:
    """Start the hub in the background if none runs. Closing a UI never stops it."""
    HUB_ENGINE.start(timeout)


def stop(
    timeout: Annotated[
        float, typer.Option("--timeout", help="Seconds to wait for the hub to stop.")
    ] = DEFAULT_TIMEOUT,
) -> None:
    """Stop the hub cleanly (SIGTERM). It is never forced."""
    HUB_ENGINE.stop(timeout)
