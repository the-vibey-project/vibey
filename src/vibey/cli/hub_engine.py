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

Whether a hub runs is read from `<state_dir>/serving.json` (the hub's own record) and a
process-existence check; a record whose process is gone is reported as stale, never as a
running hub.
"""

import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Annotated, Final

import typer

from vibey.cli.interfaces.hub_engine_interface import HubEngineCommandInterface
from vibey.domain.config import ConfigError
from vibey.infrastructure.hub.interfaces.processes_interface import HubProcessesInterface
from vibey.infrastructure.hub.interfaces.settings_interface import HubSettingsLoaderInterface
from vibey.infrastructure.hub.local_token import LocalTokenStore, ServingRecord
from vibey.infrastructure.hub.processes import HUB_PROCESSES
from vibey.infrastructure.hub.settings import HUB_SETTINGS, HubSettings

EXIT_NOT_RUNNING: Final = 3
"""The exit code of `status` when no hub runs, as `vibey hub pair` uses for the same fact."""

LOG_FILE: Final = "hub.log"
POLL_SECONDS: Final = 0.1
DEFAULT_TIMEOUT: Final = 15.0


class HubEngineCommand:
    """Starts, stops and reports the hub.

    Declared by `interfaces/hub_engine_interface.py::HubEngineCommandInterface`."""

    def __init__(
        self,
        *,
        settings: HubSettingsLoaderInterface = HUB_SETTINGS,
        config_path: Callable[[], Path] = lambda: Path.cwd() / "vibey.toml",
        processes: HubProcessesInterface = HUB_PROCESSES,
        argv: Sequence[str] = (
            sys.executable,
            "-c",
            "from vibey.cli.main import run; run(['serve'])",
        ),
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._settings = settings
        self._config_path = config_path
        self._processes = processes
        self._argv = argv
        self._sleep = sleep
        self._clock = clock

    def status(self) -> None:
        running = self._running(self._load())
        if running is None:
            raise typer.Exit(EXIT_NOT_RUNNING)
        typer.echo(self._describe(running))

    def start(self, timeout: float) -> None:
        settings = self._load()
        running = self._running(settings)
        if running is not None:
            typer.echo(f"hub already running: {self._describe(running)}")
            return
        pid = self._processes.spawn(self._argv, settings.state_dir / LOG_FILE)
        deadline = self._clock() + timeout
        while self._clock() < deadline:
            running = self._running(settings, quiet=True)
            if running is not None:
                note = "" if running.pid == pid else " (another process won the start)"
                typer.echo(f"hub started: {self._describe(running)}{note}")
                return
            if not self._processes.alive(pid):
                typer.echo(
                    f"the hub exited before it was ready; see {settings.state_dir / LOG_FILE}",
                    err=True,
                )
                raise typer.Exit(1)
            self._sleep(POLL_SECONDS)
        typer.echo(
            f"the hub did not come up within {timeout:g}s (pid {pid} is still starting); "
            f"see {settings.state_dir / LOG_FILE}",
            err=True,
        )
        raise typer.Exit(1)

    def stop(self, timeout: float) -> None:
        settings = self._load()
        running = self._running(settings)
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

    def _running(self, settings: HubSettings, *, quiet: bool = False) -> ServingRecord | None:
        """The hub's record when its process exists; None, saying why unless `quiet`, when
        there is no record, it is malformed, or its process is gone (stale)."""
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
        if not self._processes.alive(record.pid):
            if not quiet:
                typer.echo(f"hub is not running (stale record from pid {record.pid})")
            return None
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
