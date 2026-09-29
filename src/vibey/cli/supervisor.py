# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey supervisor`: keep the worker and the delivery bridge running (#1189).

- `vibey supervisor install` renders a launchd agent (macOS) or a systemd user service
  (Linux) for `vibey worker --all-projects` and for `scripts/triaged_delivery.py
  --interval N`, from `[supervisor]` in `vibey.toml`, and prints the operator's own
  command that loads them. vibey never loads a unit into the operator's session.
- `vibey supervisor status` asks the service manager whether each one runs.
- `vibey supervisor exec --env-file FILE -- ARGV...` is what every unit runs: it reads
  the declared environment file, then replaces itself with ARGV.
- `vibey doctor` prints one line per service, so a missing supervisor is said out loud.
"""

import os
import shutil
import subprocess  # nosec B404 -- fixed argv, never shell=True
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Annotated, Final

import typer

from vibey.cli.errors import EXIT_USAGE
from vibey.cli.interfaces.supervisor_interface import SupervisorCommandInterface
from vibey.domain.interfaces.supervisor_interface import (
    EnvFileParserInterface,
    SupervisorPlannerInterface,
)
from vibey.domain.supervisor import (
    DELIVERY_SCRIPT,
    EnvFileParser,
    SupervisorPaths,
    SupervisorPlanner,
    SupervisorSettings,
)
from vibey.infrastructure.driver.interfaces.timer_units_interface import (
    TimerUnitRendererInterface,
)
from vibey.infrastructure.driver.timer_units import TimerUnitRenderer
from vibey.infrastructure.interfaces.supervisor_interface import (
    SupervisorHostInterface,
    SupervisorSettingsLoaderInterface,
)
from vibey.infrastructure.supervisor import (
    LAUNCHD,
    SYSTEMD,
    SupervisorHost,
    SupervisorSettingsLoader,
)

EXIT_CONFIG: Final = 78
"""EX_CONFIG: a setting no supervised service could run with, as the storm tools use it."""

EXIT_NOT_FOUND: Final = 127

DEFAULT_PLATFORM: Final = LAUNCHD if sys.platform == "darwin" else SYSTEMD

ENV_TEMPLATE: Final = """\
# The environment of vibey's supervised services (#1189), read by `vibey supervisor exec`
# before it starts `vibey worker --all-projects` and the triaged-delivery bridge.
#
# KEY=VALUE, one per line. `#` starts a comment, `export ` is allowed, one pair of
# matching quotes around a value is removed, and nothing is expanded ($HOME stays $HOME).
# A value here wins over the service manager's own environment. Keep this file private:
# `vibey supervisor install` created it readable by you alone.
#
# VIBEY_PG_URL=postgresql://vibey_app@localhost:5432/vibey
# VIBEY_OLLAMA_URL=http://127.0.0.1:11434
# GH_TOKEN=            # the bridge's gh, if it cannot reach your login keychain here
"""

Execute = Callable[[str, list[str], Mapping[str, str]], object]


class SupervisorCommand(SupervisorCommandInterface):
    """Renders, reports and launches the supervised services for the command line."""

    def __init__(
        self,
        *,
        host_factory: Callable[[str], SupervisorHostInterface] | None = None,
        loader: SupervisorSettingsLoaderInterface | None = None,
        planner: SupervisorPlannerInterface | None = None,
        renderer: TimerUnitRendererInterface | None = None,
        parser: EnvFileParserInterface | None = None,
        which: Callable[[str], str | None] | None = None,
        python: str = sys.executable,
        environ: Mapping[str, str] | None = None,
        execute: Execute | None = None,
        root: Path | None = None,
    ) -> None:
        self._host_factory = host_factory or self._real_host
        self._loader = loader or SupervisorSettingsLoader()
        self._planner = planner or SupervisorPlanner()
        self._renderer = renderer or TimerUnitRenderer()
        self._parser = parser or EnvFileParser()
        self._which = which or shutil.which
        self._python = python
        self._environ = environ
        self._execute = execute or os.execvpe
        self._root = root

    # --- install ----------------------------------------------------------------------

    def install(self, *, platform: str, repo: Path, out: Path | None, config: Path | None) -> int:
        try:
            host = self._host_factory(platform)
        except ValueError as exc:
            typer.echo(str(exc), err=True)
            return EXIT_USAGE
        repo = repo.expanduser().resolve()
        try:
            settings = self._loader.load(config or repo / "vibey.toml")
            paths = self._paths(host, settings, repo)
            services = self._planner.services(settings, paths)
        except ValueError as exc:
            typer.echo(f"vibey supervisor install: {exc}", err=True)
            return EXIT_CONFIG

        Path(paths.log_dir).mkdir(parents=True, exist_ok=True)
        env_file = Path(paths.env_file)
        created = not env_file.exists()
        if created:
            env_file.parent.mkdir(parents=True, exist_ok=True)
            env_file.write_text(ENV_TEMPLATE, encoding="utf-8")
            env_file.chmod(0o600)

        target = (out.expanduser().resolve() if out is not None else None) or host.unit_dir()
        target.mkdir(parents=True, exist_ok=True)
        path_env = self._env().get("PATH", "")
        units: list[Path] = []
        for service in services:
            unit = host.unit_path(service.label, target)
            render = (
                self._renderer.launchd_service
                if host.platform == LAUNCHD
                else self._renderer.systemd_service
            )
            unit.write_text(
                render(service, path_env=path_env, restart_seconds=settings.restart_seconds),
                encoding="utf-8",
            )
            units.append(unit)
            typer.echo(f"wrote {unit}")

        state = "created from the template: fill it in" if created else "kept as it was"
        typer.echo(f"environment: {env_file} ({state})")
        typer.echo(f"logs: {paths.log_dir}")
        if target != host.unit_dir():
            typer.echo(f"note: the service manager reads {host.unit_dir()}, not {target}")
        typer.echo("load them with:")
        for line in host.load_commands([s.label for s in services], units):
            typer.echo(f"  {line}")
        return 0

    def _paths(
        self, host: SupervisorHostInterface, settings: SupervisorSettings, repo: Path
    ) -> SupervisorPaths:
        vibey = settings.vibey or self._which("vibey") or ""
        if not vibey:
            raise ValueError("vibey is not on PATH: set [supervisor] vibey to its full path")
        paths = SupervisorPaths(
            vibey=self._absolute(vibey),
            python=self._absolute(settings.python or self._python),
            repo=str(repo),
            env_file=self._absolute(settings.env_file or str(host.default_env_file())),
            log_dir=self._absolute(settings.log_dir or str(host.default_log_dir())),
        )
        roots = host.volatile_roots()
        for key, value in (
            ("log_dir", paths.log_dir),
            ("env_file", paths.env_file),
            ("vibey", paths.vibey),
            ("python", paths.python),
            ("--repo", paths.repo),
        ):
            root = self._planner.under(os.path.realpath(value), roots) or self._planner.under(
                value, roots
            )
            named = key if key.startswith("--") else f"[supervisor] {key}"
            if root:
                raise ValueError(
                    f"{value} is under {root}, which a reboot empties (sub-doctrine 10.h): "
                    f"move it somewhere durable with {named}"
                )
            worktree = self._linked_worktree(value)
            if worktree:
                raise ValueError(
                    f"{value} is inside the linked worktree {worktree}, which is deleted when "
                    f"its lane ends (sub-doctrine 10.h): use your main checkout or an "
                    f"installed vibey, with {named}"
                )
        if settings.delivery and not (repo / DELIVERY_SCRIPT).is_file():
            raise ValueError(
                f"no {DELIVERY_SCRIPT} under {repo}: pass --repo <your vibey checkout>, "
                "or set [supervisor] delivery = false to supervise the worker alone"
            )
        return paths

    @staticmethod
    def _linked_worktree(path: str) -> str:
        """The linked worktree `path` lies in, or "". A linked worktree's `.git` is a file
        naming the repository it belongs to; a main checkout's is a directory."""
        for parent in (Path(path), *Path(path).parents):
            if (parent / ".git").is_file():
                return str(parent)
        return ""

    @staticmethod
    def _absolute(path: str) -> str:
        return str(Path(path).expanduser().absolute())

    # --- status and doctor ------------------------------------------------------------

    def status(self, *, platform: str, config: Path | None) -> int:
        try:
            host = self._host_factory(platform)
            settings = self._loader.load(config or self._cwd() / "vibey.toml")
        except ValueError as exc:
            typer.echo(str(exc), err=True)
            return EXIT_CONFIG
        running = True
        for name, label, unit, state in self._states(host, settings):
            typer.echo(f"{name:<9} {state:<18} {label}  {unit}")
            running = running and state == "running"
        return 0 if running else 1

    def doctor_lines(self) -> tuple[list[str], bool]:
        """One line per supervised service: PASS when it runs, WARN when it is missing
        or stopped -- FAIL instead with `[supervisor] required = true` -- and FAIL when
        `[supervisor]` cannot be read. Never silent about a service nothing restarts."""
        try:
            host = self._host_factory(DEFAULT_PLATFORM)
            settings = self._loader.load(self._cwd() / "vibey.toml")
        except ValueError as exc:
            return [f"FAIL {'supervisor':<20} {exc}"], False
        mark = "FAIL" if settings.required else "WARN"
        lines: list[str] = []
        ok = True
        for name, label, unit, state in self._states(host, settings):
            check = f"supervisor-{name}"
            if state == "running":
                lines.append(f"PASS {check:<20} running ({label})")
                continue
            ok = ok and not settings.required
            if state == "not installed":
                lines.append(
                    f"{mark} {check:<20} not installed: nothing restarts it after a crash or a"
                    f" reboot -- `vibey supervisor install` renders {unit}"
                )
            else:
                lines.append(
                    f"{mark} {check:<20} installed but {state} ({label}) -- see its log"
                    " under [supervisor] log_dir"
                )
        return lines, ok

    def _states(
        self, host: SupervisorHostInterface, settings: SupervisorSettings
    ) -> list[tuple[str, str, Path, str]]:
        found: list[tuple[str, str, Path, str]] = []
        for name, label in self._planner.names(settings):
            unit = host.unit_path(label)
            state = host.state(label) if unit.exists() else "not installed"
            found.append((name, label, unit, state))
        return found

    # --- exec -------------------------------------------------------------------------

    def exec_(self, env_file: Path, argv: Sequence[str]) -> int:
        if not argv:
            typer.echo("vibey supervisor exec: nothing to run; give the command after --", err=True)
            return EXIT_USAGE
        try:
            declared = self._parser.parse(env_file.read_text(encoding="utf-8"))
        except FileNotFoundError:
            typer.echo(
                f"vibey supervisor exec: {env_file} does not exist; `vibey supervisor install`"
                " creates it from a template",
                err=True,
            )
            return EXIT_CONFIG
        except (OSError, ValueError) as exc:
            typer.echo(f"vibey supervisor exec: {env_file}: {exc}", err=True)
            return EXIT_CONFIG
        environment = {**self._env(), **declared}
        try:
            self._execute(argv[0], list(argv), environment)
        except OSError as exc:
            typer.echo(f"vibey supervisor exec: cannot run {argv[0]}: {exc}", err=True)
            return EXIT_NOT_FOUND
        return 0

    # --- the real host ----------------------------------------------------------------

    def _env(self) -> Mapping[str, str]:
        return os.environ if self._environ is None else self._environ

    def _cwd(self) -> Path:
        return self._root if self._root is not None else Path.cwd()

    def _real_host(self, platform: str) -> SupervisorHostInterface:
        return SupervisorHost(
            platform,
            home=Path.home(),
            environ=self._env(),
            uid=os.getuid(),
            run=self.service_manager,
        )

    @staticmethod
    def service_manager(argv: Sequence[str]) -> tuple[int, str]:
        """The service manager, asked: the one real `ServiceRunner` the host is given."""
        done = subprocess.run(  # nosec B603 -- fixed argv from SupervisorHost, never a shell
            list(argv), capture_output=True, text=True, check=False, timeout=30
        )
        return done.returncode, done.stdout


SUPERVISOR: Final[SupervisorCommandInterface] = SupervisorCommand()
"""The command `vibey supervisor` and `vibey doctor` run. Annotated with the interface so
`mypy --strict` checks the class against its declared seam."""

supervisor_app = typer.Typer(
    help="Keep `vibey worker --all-projects` and the delivery bridge running (#1189)."
)

PlatformOption = Annotated[str, typer.Option("--platform", help="launchd or systemd.")]
ConfigOption = Annotated[
    Path | None, typer.Option("--config", help="vibey.toml with [supervisor]; default ./.")
]


@supervisor_app.command("install")
def install_cmd(
    repo: Annotated[
        Path, typer.Option("--repo", help="The vibey checkout the bridge runs from.")
    ] = Path("."),
    out: Annotated[
        Path | None,
        typer.Option("--out", help="Write the units here instead of the service manager's."),
    ] = None,
    platform: PlatformOption = DEFAULT_PLATFORM,
    config: ConfigOption = None,
) -> None:
    """Render the worker's and the delivery bridge's units, and print how to load them."""
    raise typer.Exit(SUPERVISOR.install(platform=platform, repo=repo, out=out, config=config))


@supervisor_app.command("status")
def status_cmd(platform: PlatformOption = DEFAULT_PLATFORM, config: ConfigOption = None) -> None:
    """Whether each supervised service is installed and running; exit 1 when one is not."""
    raise typer.Exit(SUPERVISOR.status(platform=platform, config=config))


@supervisor_app.command(
    "exec", context_settings={"ignore_unknown_options": True, "allow_extra_args": True}
)
def exec_cmd(
    env_file: Annotated[
        Path, typer.Option("--env-file", help="KEY=VALUE lines to start the command with.")
    ],
    argv: Annotated[list[str] | None, typer.Argument(help="The command, after --.")] = None,
) -> None:
    """Read the environment file, then replace this process with the command."""
    raise typer.Exit(SUPERVISOR.exec_(env_file, argv or []))
