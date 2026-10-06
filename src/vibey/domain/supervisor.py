# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The declared supervisor: what keeps vibey's long-running processes alive (#1189).

Two processes have to outlive the terminal that started them: `vibey worker
--all-projects`, which serves every project's queue, and the triaged-delivery bridge
(`scripts/triaged_delivery.py --interval N`), which resumes and publishes projects.
Nothing supervised either, so a reboot or a crash stopped delivery until someone
noticed. This module is the pure half: which services exist, what each one runs,
where it logs, and how an environment file is read. Rendering them for launchd or
systemd, and asking the service manager whether they run, is infrastructure's.

Every service is started through `vibey supervisor exec --env-file <file> -- <argv>`,
on both platforms, so the environment reaches it one way, read by one parser:
launchd has no environment-file key, and giving systemd its own `EnvironmentFile=`
would give the two platforms two dialects of the same file.
"""

import re
from dataclasses import dataclass
from typing import Final

WORKER: Final = "worker"
DELIVERY: Final = "delivery"
DELIVERY_SCRIPT: Final = "scripts/triaged_delivery.py"
STATE_SYNC: Final = "state-sync"

# POSIX shell names: what a process environment can carry and a shell can read back.
_NAME: Final = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


@dataclass(frozen=True)
class SupervisorSettings:
    """`[supervisor]` in `vibey.toml` (docs/reference/configuration.md#supervisor).

    An empty path means the platform's default, which infrastructure resolves: vibey
    has no clock or home directory here."""

    log_dir: str = ""
    env_file: str = ""
    vibey: str = ""
    python: str = ""
    delivery: bool = True
    delivery_interval_seconds: int = 300
    restart_seconds: int = 30
    label_prefix: str = "dev.vibey"
    worker_args: tuple[str, ...] = ()
    delivery_args: tuple[str, ...] = ()
    required: bool = False
    state_sync: bool = False
    state_sync_interval_seconds: int = 300
    state_sync_env_file: str = ""
    state_sync_args: tuple[str, ...] = ()


@dataclass(frozen=True)
class SupervisedService:
    """One process the service manager keeps running."""

    name: str
    label: str
    argv: tuple[str, ...]
    working_directory: str
    log_path: str


@dataclass(frozen=True)
class SupervisorPaths:
    """The resolved places a plan is built from: every one absolute, none defaulted."""

    vibey: str
    python: str
    repo: str
    env_file: str
    log_dir: str
    state_env_file: str = ""


class SupervisorPlanner:
    """Declared by `interfaces/supervisor_interface.py::SupervisorPlannerInterface`."""

    def names(self, settings: SupervisorSettings) -> tuple[tuple[str, str], ...]:
        """(name, label) of every supervised service: what `status` and `doctor` ask
        the service manager about, without resolving a single path."""
        names = (WORKER, DELIVERY) if settings.delivery else (WORKER,)
        if settings.state_sync:
            names = (*names, STATE_SYNC)
        return tuple((name, f"{settings.label_prefix}.{name}") for name in names)

    def services(
        self, settings: SupervisorSettings, paths: SupervisorPaths
    ) -> tuple[SupervisedService, ...]:
        if settings.delivery_interval_seconds < 1:
            raise ValueError("[supervisor] delivery_interval_seconds must be at least 1")
        if settings.state_sync and settings.state_sync_interval_seconds < 1:
            raise ValueError("[supervisor] state_sync_interval_seconds must be at least 1")
        if settings.state_sync and not paths.state_env_file:
            raise ValueError("the state sync's environment file was not resolved")
        launcher = (paths.vibey, "supervisor", "exec", "--env-file", paths.env_file, "--")
        worker = SupervisedService(
            name=WORKER,
            label=f"{settings.label_prefix}.{WORKER}",
            argv=(*launcher, paths.vibey, "worker", "--all-projects", *settings.worker_args),
            working_directory=paths.repo,
            log_path=f"{paths.log_dir}/{WORKER}.log",
        )
        planned = (worker, *self._delivery(settings, paths, launcher))
        if not settings.state_sync:
            return planned
        # Its own environment file: the sync's DSN may write every table (ADR-0086), so it
        # is never in the file the worker reads (ADR-0055).
        state_sync = SupervisedService(
            name=STATE_SYNC,
            label=f"{settings.label_prefix}.{STATE_SYNC}",
            argv=(
                paths.vibey,
                "supervisor",
                "exec",
                "--env-file",
                paths.state_env_file,
                "--",
                paths.vibey,
                "state",
                "sync",
                "--every",
                str(settings.state_sync_interval_seconds),
                *settings.state_sync_args,
            ),
            working_directory=paths.repo,
            log_path=f"{paths.log_dir}/{STATE_SYNC}.log",
        )
        return (*planned, state_sync)

    @staticmethod
    def _delivery(
        settings: SupervisorSettings, paths: SupervisorPaths, launcher: tuple[str, ...]
    ) -> tuple[SupervisedService, ...]:
        if not settings.delivery:
            return ()
        delivery = SupervisedService(
            name=DELIVERY,
            label=f"{settings.label_prefix}.{DELIVERY}",
            argv=(
                *launcher,
                paths.python,
                f"{paths.repo}/{DELIVERY_SCRIPT}",
                "--repo",
                paths.repo,
                "--interval",
                str(settings.delivery_interval_seconds),
                *settings.delivery_args,
            ),
            working_directory=paths.repo,
            log_path=f"{paths.log_dir}/{DELIVERY}.log",
        )
        return (delivery,)

    def under(self, path: str, roots: tuple[str, ...]) -> str:
        """The root `path` lies in or under, or "": the check that keeps a supervised
        service's files off storage a reboot empties (10.h, ADR-0057)."""
        for root in roots:
            base = root.rstrip("/")
            if path.rstrip("/") == base or path.startswith(base + "/"):
                return base
        return ""


class EnvFileParser:
    """Declared by `interfaces/supervisor_interface.py::EnvFileParserInterface`.

    `KEY=VALUE` lines. Blank lines and lines starting with `#` are skipped, a leading
    `export ` is allowed, and one pair of matching single or double quotes around a
    value is removed. Nothing is expanded: `$HOME` stays `$HOME`, so the file means the
    same thing whichever service manager starts the process."""

    def parse(self, text: str) -> dict[str, str]:
        found: dict[str, str] = {}
        for number, raw in enumerate(text.splitlines(), start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line.removeprefix("export ").lstrip()
            key, equals, value = line.partition("=")
            key = key.strip()
            if not equals or not _NAME.fullmatch(key):
                # The line itself is never quoted back: it may hold a secret.
                raise ValueError(f"line {number}: expected KEY=VALUE with a shell-style name")
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
                value = value[1:-1]
            found[key] = value
        return found
