# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey driver`: the driver session's failover and handback (ADR-0070).

- `vibey driver hook` is the command Claude Code's `StopFailure` hook runs. It reads
  the hook's JSON from stdin; on `rate_limit` or `billing_error` it gates a brief into
  the worktree and starts the sovereign engine at ULTRA. Claude Code ignores this
  hook's exit code (code.claude.com/docs/en/hooks#stopfailure), so the outcome is
  printed as JSON and recorded in the driver's ledger.
- `vibey driver probe` is what the timer runs: when a probe is due it asks the paid
  model for one word, records the answer, and only on a recorded success hands the
  work back to the same session with `claude -p --resume <session-id>`.
- `vibey driver status`, `vibey driver timer` and `vibey driver hook-config` show the
  state, write the timer's units, and print the hook's settings block.
"""

import json
import shutil
import sys
from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Final, TextIO

import typer

from vibey.application.driver_failover import DriverFailoverService
from vibey.application.dto import DriverOutcome, DriverSignal
from vibey.application.interfaces.driver import DriverFailoverServiceInterface
from vibey.domain.failover import FailoverSettings, FailoverStatus
from vibey.infrastructure.driver.file_ledger import JsonlDriverLedger
from vibey.infrastructure.driver.processes import SubprocessPort
from vibey.infrastructure.driver.settings_loader import FailoverSettingsLoader
from vibey.infrastructure.driver.timer_units import TimerUnitRenderer
from vibey.infrastructure.driver.workspace import DRIVER_DIR, LocalDriverWorkspace

HOOK_EVENT: Final = "StopFailure"
PARKED_EXIT: Final = 3


class _UtcClock:
    """The wall clock, in UTC; the one the driver's records are stamped with."""

    def now(self) -> datetime:
        return datetime.now(UTC)


class DriverCommand:
    """Builds the one driver service for a worktree and prints what it did."""

    def __init__(
        self,
        *,
        make_service: Callable[[Path, FailoverSettings], DriverFailoverServiceInterface]
        | None = None,
        loader: FailoverSettingsLoader | None = None,
        units: TimerUnitRenderer | None = None,
        which: Callable[[str], str | None] = shutil.which,
    ) -> None:
        self._make_service = make_service or self._default_service
        self._loader = loader or FailoverSettingsLoader()
        self._units = units or TimerUnitRenderer()
        self._which = which

    def hook(self, stdin: TextIO, config: Path | None) -> int:
        try:
            body = json.loads(stdin.read() or "{}")
        except ValueError:
            typer.echo(json.dumps({"result": "ignored", "detail": "stdin is not JSON"}))
            return 0
        if not isinstance(body, dict) or body.get("hook_event_name") != HOOK_EVENT:
            typer.echo(json.dumps({"result": "ignored", "detail": "not a StopFailure hook"}))
            return 0
        cwd = Path(str(body.get("cwd") or ".")).resolve()
        signal = DriverSignal(
            session_id=str(body.get("session_id", "")),
            transcript_path=str(body.get("transcript_path", "")),
            cwd=str(cwd),
            error=str(body.get("error", "")),
            detail=str(body.get("error_details") or ""),
            last_message=str(body.get("last_assistant_message") or ""),
        )
        outcome = self._service(cwd, config).fail_over(signal)
        return self._print(outcome)

    def probe(self, cwd: Path, config: Path | None) -> int:
        cwd = cwd.resolve()
        return self._print(self._service(cwd, config).probe(str(cwd)))

    def status(self, cwd: Path, config: Path | None) -> int:
        cwd = cwd.resolve()
        state = self._service(cwd, config).status()
        typer.echo(json.dumps(self._status(state), sort_keys=True))
        return 0

    def timer(self, cwd: Path, platform: str, out: Path, config: Path | None) -> int:
        cwd = cwd.resolve()
        settings = self._settings(cwd, config)
        vibey = self._which("vibey") or "vibey"
        argv = [vibey, "driver", "probe", "--cwd", str(cwd)]
        seconds = int(settings.probe_interval.total_seconds())
        label = self._units.label(str(cwd))
        out.mkdir(parents=True, exist_ok=True)
        if platform == "launchd":
            plist = out / f"{label}.plist"
            plist.write_text(
                self._units.launchd(argv=argv, cwd=str(cwd), interval_seconds=seconds),
                encoding="utf-8",
            )
            typer.echo(f"wrote {plist}\nload it with: launchctl load -w {plist}")
            return 0
        if platform == "systemd":
            service, timer = self._units.systemd(argv=argv, cwd=str(cwd), interval_seconds=seconds)
            (out / f"{label}.service").write_text(service, encoding="utf-8")
            (out / f"{label}.timer").write_text(timer, encoding="utf-8")
            typer.echo(
                f"wrote {out / label}.service and .timer\n"
                f"enable it with: systemctl --user daemon-reload && "
                f"systemctl --user enable --now {label}.timer"
            )
            return 0
        typer.echo(f"unknown platform {platform!r}: use launchd or systemd", err=True)
        return 2

    def hook_config(self) -> int:
        """No matcher: every StopFailure reaches the hook, and the classifier ignores
        each error type that is not a capacity rejection."""
        block = {
            "hooks": {
                HOOK_EVENT: [{"hooks": [{"type": "command", "command": "vibey driver hook"}]}]
            }
        }
        typer.echo(json.dumps(block, indent=2))
        return 0

    def _service(self, cwd: Path, config: Path | None) -> DriverFailoverServiceInterface:
        return self._make_service(cwd, self._settings(cwd, config))

    def _settings(self, cwd: Path, config: Path | None) -> FailoverSettings:
        return self._loader.load(config or cwd / "vibey.toml")

    @staticmethod
    def _default_service(cwd: Path, settings: FailoverSettings) -> DriverFailoverServiceInterface:
        return DriverFailoverService(
            settings=settings,
            workspace=LocalDriverWorkspace(),
            ledger=JsonlDriverLedger(cwd / DRIVER_DIR / "ledger.jsonl"),
            processes=SubprocessPort(),
            clock=_UtcClock(),
        )

    def _print(self, outcome: DriverOutcome) -> int:
        body: dict[str, object] = {
            "result": outcome.result,
            "detail": outcome.detail,
            "brief_path": outcome.brief_path,
        }
        if outcome.status is not None:
            body["status"] = self._status(outcome.status)
        typer.echo(json.dumps(body, sort_keys=True))
        return PARKED_EXIT if outcome.result == "parked" else 0

    @staticmethod
    def _status(state: FailoverStatus) -> dict[str, object]:
        def record(rec: object) -> object:
            if rec is None:
                return None
            data = asdict(rec)  # type: ignore[call-overload]
            data["kind"] = str(data["kind"])
            data["at"] = data["at"].isoformat()
            return data

        return {
            "active": state.active,
            "may_hand_back": state.may_hand_back,
            "failover": record(state.failover),
            "probe_ok": record(state.probe_ok),
        }


driver_app = typer.Typer(help="The driver session's failover and handback (ADR-0070).")
_COMMAND = DriverCommand()

ConfigOption = Annotated[
    Path | None, typer.Option("--config", help="vibey.toml with [failover]; default <cwd>.")
]
CwdOption = Annotated[Path, typer.Option("--cwd", help="The worktree the driver steers.")]


@driver_app.command("hook")
def hook_cmd(config: ConfigOption = None) -> None:
    """Run by Claude Code's StopFailure hook; reads the hook's JSON on stdin."""
    raise typer.Exit(_COMMAND.hook(sys.stdin, config))


@driver_app.command("probe")
def probe_cmd(cwd: CwdOption = Path("."), config: ConfigOption = None) -> None:
    """Probe the paid model when due; hand back only after a recorded success."""
    raise typer.Exit(_COMMAND.probe(cwd, config))


@driver_app.command("status")
def status_cmd(cwd: CwdOption = Path("."), config: ConfigOption = None) -> None:
    """The driver's failover state, read from its ledger."""
    raise typer.Exit(_COMMAND.status(cwd, config))


@driver_app.command("timer")
def timer_cmd(
    out: Annotated[Path, typer.Option("--out", help="Directory to write the units to.")],
    platform: Annotated[str, typer.Option("--platform", help="launchd or systemd.")] = (
        "launchd" if sys.platform == "darwin" else "systemd"
    ),
    cwd: CwdOption = Path("."),
    config: ConfigOption = None,
) -> None:
    """Write the probe's launchd agent or systemd user timer."""
    raise typer.Exit(_COMMAND.timer(cwd, platform, out, config))


@driver_app.command("hook-config")
def hook_config_cmd() -> None:
    """Print the settings.json block that runs `vibey driver hook` on StopFailure."""
    raise typer.Exit(_COMMAND.hook_config())
