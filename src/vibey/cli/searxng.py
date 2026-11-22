# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey searxng`: the local SearXNG search asks first, installed and run by vibey (ADR-0102).

- `vibey searxng install` does what the editor's bootstrap offers, from a terminal: it says what
  it will download and run and asks (`--yes` is the person's own answer in advance), pulls the
  pinned image, writes the settings and the record in the person's configuration folder, writes
  and loads the user-level unit `<[supervisor] label_prefix>.searxng`, and waits until the
  SearXNG answers as vibey's own.
- `vibey searxng status` says what is here: the runtime, what vibey installed, the image, the
  unit and whether it answers.
- `vibey searxng uninstall` unloads the unit, removes its file (only while it is what vibey wrote)
  and the container; `--purge` also removes the image, the settings and the record.
- `vibey searxng serve` (hidden) is what the unit runs (`SearxngServe`).

Everything is read from the person's own `vibey.toml` and configuration folder, never the folder
this runs in. `vibey doctor` prints `doctor_line` in its web-search section.

Declared by `interfaces/searxng_interface.py`.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path, PurePath
from typing import Annotated, Final

import typer

from vibey.application.acp.acp_searxng_step import NO_RUNTIME
from vibey.application.acp.doctor_checks import DoctorChecks
from vibey.application.acp.dto import UnitOutcome
from vibey.application.acp.interfaces.bootstrap_lock_interface import BootstrapLockInterface
from vibey.application.acp.interfaces.searxng_provisioner_interface import (
    SearxngProvisionerInterface,
)
from vibey.application.acp.interfaces.service_loader_interface import ServiceLoaderInterface
from vibey.application.acp.interfaces.service_units_interface import ServiceUnitsInterface
from vibey.bootstrap import AcpMachine, acp_machine, acp_user_config, searxng_serve
from vibey.cli.interfaces.searxng_interface import SearxngCommandInterface
from vibey.domain.acp.settings import AcpSettings
from vibey.domain.config import ConfigError
from vibey.domain.searxng import SearxngPlan
from vibey.domain.supervisor import SEARXNG
from vibey.infrastructure.acp.acp_settings_loader import AcpSettingsLoader
from vibey.infrastructure.acp.interfaces.acp_settings_loader_interface import (
    AcpSettingsLoaderInterface,
)
from vibey.infrastructure.searxng.interfaces.searxng_serve_interface import SearxngServeInterface

EXIT_CONFIG: Final = 78
INSTALL_COMMAND: Final = "vibey searxng install"
NAME: Final = "searxng"
_WIDTH: Final = 26
WRITTEN: Final = frozenset({"created", "unchanged", "updated"})


class SearxngCommand:
    """Declared by `SearxngCommandInterface`. Every collaborator is a seam."""

    def __init__(
        self,
        *,
        machine: Callable[..., AcpMachine] = acp_machine,
        serve: Callable[..., SearxngServeInterface] = searxng_serve,
        settings: AcpSettingsLoaderInterface | None = None,
        user_config: Callable[[], Path] = acp_user_config,
        echo: Callable[[str], object] = typer.echo,
        confirm: Callable[[str], bool] = lambda question: typer.confirm(question, default=False),
        sleep: Callable[[float], object] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._machine = machine
        self._serve = serve
        self._settings = settings if settings is not None else AcpSettingsLoader()
        self._user_config = user_config
        self._echo = echo
        self._confirm = confirm
        self._sleep = sleep
        self._clock = clock
        self._plan = SearxngPlan()

    # -- the commands --------------------------------------------------------------------------

    def serve(self) -> int:
        settings = self._read_settings()
        if settings is None:
            return EXIT_CONFIG
        return self._serve(settings, user_config=self._user_config()).run()

    def status(self) -> int:
        parts = self._parts()
        if parts is None:
            return EXIT_CONFIG
        _, units, loader, searxng, _ = parts
        found = searxng.offer()
        record = searxng.record()
        refusal = searxng.refusal()
        label = self._label(units)
        self._echo(f"runtime     {found.runtime or 'none: install Podman or Docker'}")
        if found.own_url:
            self._echo(f"your own    {found.own_url} names your SearXNG; search asks it instead")
        if refusal:
            self._echo(f"refused     {refusal}")
        if record is None:
            self._echo("installed   no (`vibey searxng install` installs it)")
        else:
            self._echo(
                f"installed   searxng/searxng@sha256:{self._plan.short(record.image)} on "
                f"127.0.0.1:{record.port}, unit {label}"
            )
            self._echo(f"image       {'here' if searxng.image_present() else 'not here'}")
            if label is not None:
                self._echo(f"unit        {self._state(loader, label)}")
        if found.outdated:
            self._echo(
                f"update      a newer pinned image is available ({found.outdated}); "
                f"`{INSTALL_COMMAND}` updates it"
            )
        if found.disabled:
            self._echo(f"stopped     for good; `{INSTALL_COMMAND}` starts it again")
        answering = searxng.answering() if record is not None else found.answering
        said = "yes" if answering else "no"
        self._echo(f"answering   {said}{' (as vibey own)' if answering and record else ''}")
        return 0

    def install(self, *, yes: bool) -> int:
        parts = self._parts()
        if parts is None:
            return EXIT_CONFIG
        settings, units, loader, searxng, lock = parts
        refused = loader.refused()
        if refused:
            self._echo(f"vibey searxng install: {refused}")
            return 1
        return self._holding(lock, lambda: self._install(settings, units, loader, searxng, yes))

    def _install(
        self,
        settings: AcpSettings,
        units: ServiceUnitsInterface,
        loader: ServiceLoaderInterface,
        searxng: SearxngProvisionerInterface,
        yes: bool,
    ) -> int:
        found = searxng.offer()
        if found.own_url:
            self._echo(
                f"{found.own_url} names your own SearXNG, which search asks instead; unset it to "
                "use one vibey installs. Nothing was installed."
            )
            return 1
        if found.runtime is None:
            self._echo(NO_RUNTIME)
            return 1
        busy = searxng.busy()
        if busy:
            self._echo(f"{busy}. Nothing was installed.")
            return 1
        question = (
            f"Download and run SearXNG (searxng/searxng@sha256:{found.short}) in a container on "
            f"127.0.0.1:{found.port} with {PurePath(found.runtime).name}? It is downloaded once "
            "and a container keeps running."
        )
        if yes:
            self._echo(f"{question} [--yes: yes]")  # the question is said, answered in advance
        elif not self._confirm(question):
            self._echo("Nothing was installed.")
            return 1
        prepared = searxng.prepare()
        self._echo(prepared.detail)
        if not prepared.ok:
            return 1
        try:
            (unit,) = units.write((SEARXNG,), settings.restart)
        except (OSError, ValueError) as exc:
            self._echo(f"No unit was written: {exc}")
            return 1
        if not self._load(loader, unit):
            return 1
        return 0 if self._wait(settings, searxng) else 1

    def uninstall(self, *, purge: bool) -> int:
        parts = self._parts()
        if parts is None:
            return EXIT_CONFIG
        _, units, loader, searxng, lock = parts
        refused = loader.refused()
        if refused:
            self._echo(f"vibey searxng uninstall: {refused}")
            return 1
        return self._holding(lock, lambda: self._uninstall(units, loader, searxng, purge))

    def _uninstall(
        self,
        units: ServiceUnitsInterface,
        loader: ServiceLoaderInterface,
        searxng: SearxngProvisionerInterface,
        purge: bool,
    ) -> int:
        # The label is this configuration's, never the record's: a record naming another label
        # can never make this unload the hub (or anything but vibey's SearXNG).
        label = self._label(units)
        failed = label is not None and not self._unload(loader, units, label)
        why = searxng.remove_container()
        if why:
            failed = True
            self._echo(f"the container was not removed: {why}")
        else:
            self._echo("the container is removed (or there was none)")
        if purge:
            for kept in searxng.purge():
                failed = True
                self._echo(kept)
            self._echo("the settings and the record are removed")
        else:
            self._echo("the settings, the record and the image are kept; --purge removes them")
        try:
            searxng.disable()
        except (OSError, ValueError) as exc:
            failed = True
            self._echo(
                f"it could not be marked stopped for good ({DoctorChecks.cleaned(str(exc))}); "
                "an editor session may load it again"
            )
        else:
            self._echo(
                f"it is stopped for good: no editor session loads or offers it again until "
                f"`{INSTALL_COMMAND}`"
            )
        return 1 if failed else 0

    def doctor_line(self) -> str:
        try:
            return self._doctor_line()
        except Exception as exc:  # noqa: BLE001 - the line never breaks doctor
            reason = DoctorChecks.cleaned(f"{type(exc).__name__}: {exc}")
            return f"UNKNOWN {NAME:<{_WIDTH}} could not check vibey's SearXNG ({reason})"

    def _doctor_line(self) -> str:
        parts = self._parts(quiet=True)
        if parts is None:
            return f"UNKNOWN {NAME:<{_WIDTH}} could not read your own vibey.toml"
        _, units, loader, searxng, _ = parts
        refusal = searxng.refusal()
        if refusal:
            return f"WARN {NAME:<{_WIDTH}} vibey's SearXNG: {DoctorChecks.cleaned(refusal)}"
        if searxng.disabled():
            return (
                f"UNKNOWN {NAME:<{_WIDTH}} vibey's SearXNG is stopped for good; "
                f"`{INSTALL_COMMAND}` starts it again"
            )
        record = searxng.record()
        if record is None:
            found = searxng.offer()
            if found.own_url:
                return (
                    f"UNKNOWN {NAME:<{_WIDTH}} you run your own SearXNG ({found.own_url}); "
                    "vibey installs none"
                )
            runtime = (
                f"{PurePath(found.runtime).name} found"
                if found.runtime
                else "no podman or docker in vibey's trusted folders"
            )
            return (
                f"WARN {NAME:<{_WIDTH}} not installed by vibey ({runtime}): `vibey searxng "
                f"install` runs one on 127.0.0.1:{found.port}"
            )
        where = f"127.0.0.1:{record.port}"
        label = self._label(units) or "its unit"
        if not searxng.image_present():
            problem = "its image is not here: `vibey searxng install` downloads it"
        elif (state := self._state(loader, label)) != "running":
            problem = f"unit {label} is {state}: `vibey searxng status` says more"
        elif not searxng.answering():
            problem = f"it does not answer as vibey's own on {where}; its unit log says why"
        else:
            return (
                f"PASS {NAME:<{_WIDTH}} vibey's SearXNG answering as its own on {where} "
                f"(searxng/searxng@sha256:{self._plan.short(record.image)}, unit {label})"
            )
        return f"WARN {NAME:<{_WIDTH}} vibey's SearXNG: {problem}"

    # -- helpers -------------------------------------------------------------------------------

    def _read_settings(self, *, quiet: bool = False) -> AcpSettings | None:
        try:
            return self._settings.load(self._user_config())
        except ConfigError as exc:
            if not quiet:
                self._echo(f"vibey searxng: {exc}")
            return None

    def _parts(
        self, *, quiet: bool = False
    ) -> (
        tuple[
            AcpSettings,
            ServiceUnitsInterface,
            ServiceLoaderInterface,
            SearxngProvisionerInterface,
            BootstrapLockInterface,
        ]
        | None
    ):
        settings = self._read_settings(quiet=quiet)
        if settings is None:
            return None
        machine = self._machine(settings, user_config=self._user_config())
        units, loader, searxng = machine.units, machine.loader, machine.searxng
        if units is None or loader is None or searxng is None:
            if not quiet:
                self._echo("vibey searxng: this computer has no user-level services")
            return None
        return settings, units, loader, searxng, machine.lock

    def _holding(self, lock: BootstrapLockInterface, work: Callable[[], int]) -> int:
        """Run `work` holding the one setup lock per person that `vibey acp` holds, so an
        editor's install and this command never write the same files at once."""
        try:
            held = lock.acquire()
        except OSError as exc:
            self._echo(f"vibey searxng: the setup lock could not be taken ({exc})")
            return 1
        if not held:
            self._echo(
                "vibey searxng: another vibey (an editor's `vibey acp`, or this command) is "
                "changing this computer now; try again when it is done"
            )
            return 1
        try:
            return work()
        finally:
            lock.release()

    @staticmethod
    def _label(units: ServiceUnitsInterface) -> str | None:
        try:
            return units.label(SEARXNG)
        except ValueError:
            return None

    @staticmethod
    def _state(loader: ServiceLoaderInterface, label: str) -> str:
        if not loader.available():
            return "unknown: no service manager to ask"
        return loader.state(label)

    def _load(self, loader: ServiceLoaderInterface, unit: UnitOutcome) -> bool:
        if unit.action == "kept-differing":
            self._echo(
                f"{unit.path} differs from what vibey renders, so it is kept as you edited it; "
                "vibey neither loads nor restarts it"
            )
            return False
        if unit.action not in WRITTEN:
            self._echo(f"{unit.label}: the unit was not written: {unit.detail}")
            return False
        if not loader.available():
            self._echo(
                f"{loader.domain()} cannot be reached here, so nothing keeps SearXNG running; "
                "run `vibey searxng serve` yourself to start it"
            )
            return False
        running = loader.state(unit.label) == "running"
        done = loader.restart(unit.label) if running else loader.load(unit.label, unit.path)
        if done.action == "failed":
            self._echo(f"{unit.label}: could not be started: {done.detail}")
            return False
        self._echo(
            f"{unit.label}: {done.action} into {loader.domain()}. `vibey searxng uninstall` "
            "stops it for good; by hand, the unit alone: "
            + "; ".join(loader.unload_commands([unit.label]))
        )
        return True

    def _wait(self, settings: AcpSettings, searxng: SearxngProvisionerInterface) -> bool:
        deadline = self._clock() + settings.bootstrap_timeout_seconds
        while not searxng.answering():
            if self._clock() >= deadline:
                self._echo(
                    f"SearXNG did not answer as vibey's own within "
                    f"{settings.bootstrap_timeout_seconds} s; `vibey searxng status` and its unit "
                    "log say why"
                )
                return False
            self._sleep(settings.live_poll_seconds)
        self._echo("SearXNG answers as vibey's own; search asks it first")
        return True

    def _unload(
        self, loader: ServiceLoaderInterface, units: ServiceUnitsInterface, label: str
    ) -> bool:
        unloaded = loader.unload(label)
        if unloaded.action == "failed":
            self._echo(f"{label}: not unloaded ({unloaded.detail}); its unit file is kept")
            return False
        removed = units.remove(label)
        self._echo(f"{label}: {unloaded.action}; unit file {removed.action}")
        if removed.action == "removed":
            forgotten = loader.forget_unit_files()
            if forgotten.action == "failed":
                self._echo(f"the service manager did not reload its units: {forgotten.detail}")
                return False
        return removed.action != "failed"


SEARXNG_COMMAND: Final[SearxngCommandInterface] = SearxngCommand()

searxng_app = typer.Typer(
    help="The local SearXNG vibey's search asks first: install, status, uninstall (ADR-0102)."
)


@searxng_app.command("install")
def install_cmd(
    yes: Annotated[
        bool, typer.Option("--yes", help="Answer yes to the question; it is still printed.")
    ] = False,
) -> None:
    """Download the pinned SearXNG image and keep it running on 127.0.0.1, as a user-level unit."""
    raise typer.Exit(SEARXNG_COMMAND.install(yes=yes))


@searxng_app.command("status")
def status_cmd() -> None:
    """What is here: the runtime, what vibey installed, the image, the unit, and whether it
    answers as vibey's own."""
    raise typer.Exit(SEARXNG_COMMAND.status())


@searxng_app.command("uninstall")
def uninstall_cmd(
    purge: Annotated[
        bool, typer.Option("--purge", help="Also remove the image, the settings and the record.")
    ] = False,
) -> None:
    """Stop the unit and remove it and the container; keep the settings unless --purge."""
    raise typer.Exit(SEARXNG_COMMAND.uninstall(purge=purge))


@searxng_app.command("serve", hidden=True)
def serve_cmd() -> None:
    """What the SearXNG unit runs: check, then exec the container runtime. Never downloads."""
    raise typer.Exit(SEARXNG_COMMAND.serve())
