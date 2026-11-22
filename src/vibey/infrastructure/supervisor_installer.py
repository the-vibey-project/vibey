# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Where a supervised unit's paths come from, and how its file is written (#1189, ADR-0101).

Two callers share it. `vibey supervisor install` writes with `overwrite=True`: the table is the
source and installing again replaces what it rendered before. `vibey acp` writes with
`overwrite=False`: a unit that differs from what vibey renders is the operator's edit, and it is
left exactly as it is (`kept-differing`), never replaced.

A unit is written atomically: staged in its directory under a fresh name with mode 0644, then
put in place by `link` (which never replaces, so a unit that appeared meanwhile still wins) or by
`rename` (with `overwrite`). The directory is resolved once and then opened without following a
link; every name inside it is read, staged and renamed relative to that descriptor, so a link
swapped in after the check is never followed. A unit that is itself a symbolic link, or not a
regular file, is refused.

The path rules (vibey found, nothing on volatile storage or in a linked worktree, 10.h) moved
here unchanged from `vibey supervisor install`, so both callers refuse the same places with the
same words.

Declared by `interfaces/supervisor_installer_interface.py`.
"""

from __future__ import annotations

import contextlib
import os
import secrets
import stat
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Final

from vibey.application.acp.dto import UnitAction, UnitOutcome
from vibey.domain.interfaces.supervisor_interface import SupervisorPlannerInterface
from vibey.domain.supervisor import (
    DELIVERY_SCRIPT,
    SupervisedService,
    SupervisorPaths,
    SupervisorSettings,
)
from vibey.infrastructure.driver.interfaces.timer_units_interface import (
    TimerUnitRendererInterface,
)
from vibey.infrastructure.interfaces.supervisor_interface import SupervisorHostInterface
from vibey.infrastructure.supervisor import LAUNCHD

UNIT_MODE: Final = 0o644
"""Readable by the service manager, writable by its owner alone (launchd refuses a property
list anyone else may write)."""
UNIT_READ_LIMIT: Final = 1 << 20
"""The most of an existing unit read to compare it; a unit is a few hundred bytes."""

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

STATE_ENV_NAME: Final = "state-sync.env"
STATE_ENV_TEMPLATE: Final = """\
# The environment of `vibey state sync --every N` (ADR-0086), the supervised state sync.
# Its own file, never the worker's: the sync's database role writes every synced table,
# more than the application role may (ADR-0055). Keep it private: it was created readable
# by you alone. Same syntax as supervisor.env.
#
# VIBEY_STATE_PG_URL=postgresql://vibey@localhost:5432/vibey
# VIBEY_STATE_REPOSITORY=OWNER/NAME
# GH_TOKEN=            # if gh cannot reach your login keychain here
# VIBEY_STATE_KEY=     # only if the keychain or the key file cannot be read here
"""


class SupervisorInstaller:
    """Declared by `interfaces/supervisor_installer_interface.py::SupervisorInstallerInterface`.

    `which` finds `vibey` on PATH; `python` is the interpreter that runs the delivery bridge;
    `linked_worktree` names the linked worktree a path lies in ("" when none)."""

    def __init__(
        self,
        host: SupervisorHostInterface,
        planner: SupervisorPlannerInterface,
        renderer: TimerUnitRendererInterface,
        *,
        which: Callable[[str], str | None],
        python: str,
        linked_worktree: Callable[[str], str] | None = None,
    ) -> None:
        self._host = host
        self._planner = planner
        self._renderer = renderer
        self._which = which
        self._python = python
        self._linked_worktree = linked_worktree or self.linked_worktree

    # --- paths --------------------------------------------------------------------------

    def paths(self, settings: SupervisorSettings, repo: Path) -> SupervisorPaths:
        host = self._host
        vibey = settings.vibey or self._which("vibey") or ""
        if not vibey:
            raise ValueError("vibey is not on PATH: set [supervisor] vibey to its full path")
        paths = SupervisorPaths(
            vibey=self._absolute(vibey),
            python=self._absolute(settings.python or self._python),
            repo=str(repo),
            env_file=self._absolute(settings.env_file or str(host.default_env_file())),
            log_dir=self._absolute(settings.log_dir or str(host.default_log_dir())),
            state_env_file=self._absolute(
                settings.state_sync_env_file
                or str(host.default_env_file().with_name(STATE_ENV_NAME))
            )
            if settings.state_sync
            else "",
        )
        roots = host.volatile_roots()
        for key, value in (
            ("log_dir", paths.log_dir),
            ("env_file", paths.env_file),
            ("state_sync_env_file", paths.state_env_file or paths.env_file),
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
    def linked_worktree(path: str) -> str:
        """The linked worktree `path` lies in, or "". A linked worktree's `.git` is a file
        naming the repository it belongs to; a main checkout's is a directory."""
        for parent in (Path(path), *Path(path).parents):
            if (parent / ".git").is_file():
                return str(parent)
        return ""

    @staticmethod
    def _absolute(path: str) -> str:
        return str(Path(path).expanduser().absolute())

    # --- the environment file -------------------------------------------------------------

    def env_file(self, path: Path, template: str) -> bool:
        if os.path.lexists(path):
            return False
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        except FileExistsError:
            return False
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            os.fchmod(handle.fileno(), 0o600)
            handle.write(template)
        return True

    # --- the units ------------------------------------------------------------------------

    def write(
        self,
        services: Sequence[SupervisedService],
        settings: SupervisorSettings,
        *,
        out: Path | None,
        overwrite: bool,
        path_env: str,
    ) -> tuple[UnitOutcome, ...]:
        host = self._host
        # Every unit is rendered before any is written: a value no unit can carry writes none.
        rendered = [(service, self._render(service, settings, path_env)) for service in services]
        target = out.expanduser().resolve() if out is not None else host.unit_dir()
        target.mkdir(parents=True, exist_ok=True)
        try:
            directory = os.open(
                os.path.realpath(target), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
            )
        except OSError as exc:
            return tuple(
                UnitOutcome(
                    service.label,
                    str(host.unit_path(service.label, target)),
                    "failed",
                    f"{target} could not be opened as a directory: {exc.strerror or exc}",
                )
                for service, _ in rendered
            )
        try:
            return tuple(
                self._write_one(
                    directory, host.unit_path(service.label, target), service, text, overwrite
                )
                for service, text in rendered
            )
        finally:
            os.close(directory)

    def _render(
        self, service: SupervisedService, settings: SupervisorSettings, path_env: str
    ) -> str:
        if self._host.platform == LAUNCHD:
            return self._renderer.launchd_service(
                service, path_env=path_env, restart_seconds=settings.restart_seconds
            )
        return self._renderer.systemd_service(
            service,
            path_env=path_env,
            restart_seconds=settings.restart_seconds,
            start_limit_interval_seconds=settings.start_limit_interval_seconds,
            start_limit_burst=settings.start_limit_burst,
        )

    def _write_one(
        self, directory: int, unit: Path, service: SupervisedService, text: str, overwrite: bool
    ) -> UnitOutcome:
        try:
            refusal = self._refusal(directory, unit.name)
            if refusal:
                return UnitOutcome(service.label, str(unit), "failed", refusal)
            return self._put(directory, unit, service, text, overwrite)
        except OSError as exc:
            return UnitOutcome(service.label, str(unit), "failed", exc.strerror or str(exc))

    def _put(
        self, directory: int, unit: Path, service: SupervisedService, text: str, overwrite: bool
    ) -> UnitOutcome:
        name = unit.name
        existing = self._existing(directory, name)
        if existing == text:
            return UnitOutcome(service.label, str(unit), "unchanged")
        if existing is not None and not overwrite:
            return self._kept(service, unit)
        staged = self._stage(directory, name, text)
        try:
            if overwrite:
                os.replace(staged, name, src_dir_fd=directory, dst_dir_fd=directory)
                action: UnitAction = "updated" if existing is not None else "created"
                return UnitOutcome(service.label, str(unit), action)
            try:
                # `link` never replaces: a unit that appeared since the check wins.
                os.link(staged, name, src_dir_fd=directory, dst_dir_fd=directory)
            except FileExistsError:
                if self._refusal(directory, name):
                    raise
                if self._existing(directory, name) == text:
                    return UnitOutcome(service.label, str(unit), "unchanged")
                return self._kept(service, unit)
            return UnitOutcome(service.label, str(unit), "created")
        finally:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(staged, dir_fd=directory)

    @staticmethod
    def _kept(service: SupervisedService, unit: Path) -> UnitOutcome:
        return UnitOutcome(
            service.label,
            str(unit),
            "kept-differing",
            "it differs from what vibey renders, so it is kept as you edited it",
        )

    @staticmethod
    def _refusal(directory: int, name: str) -> str:
        """Why vibey will not write `name`: a link, or anything but a regular file; "" when
        it may (it is a regular file, or there is none)."""
        try:
            found = os.stat(name, dir_fd=directory, follow_symlinks=False)
        except FileNotFoundError:
            return ""
        if stat.S_ISLNK(found.st_mode):
            return "it is a symbolic link, and vibey writes no unit through a link"
        if not stat.S_ISREG(found.st_mode):
            return "it is not a regular file"
        return ""

    @staticmethod
    def _existing(directory: int, name: str) -> str | None:
        """The unit's text, read without following a link; None when there is none."""
        try:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
        except FileNotFoundError:
            return None
        with os.fdopen(fd, "rb") as handle:
            return handle.read(UNIT_READ_LIMIT).decode("utf-8", errors="replace")

    @staticmethod
    def _stage(directory: int, name: str, text: str) -> str:
        staged = f".{name}.{secrets.token_hex(8)}.tmp"
        fd = os.open(
            staged,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            UNIT_MODE,
            dir_fd=directory,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                os.fchmod(handle.fileno(), UNIT_MODE)
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
        except BaseException:
            os.unlink(staged, dir_fd=directory)
            raise
        return staged
