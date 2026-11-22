# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Loads and restarts `vibey acp`'s own user-level units (ADR-0101).

ADR-0070 and #1189 left loading to the operator. ADR-0101 amends that for two units only -- the
hub and the worker `vibey acp` plans -- and only while `[acp] auto_bootstrap` and
`[acp] auto_services` are on: vibey loads user-level units (launchd `gui/<uid>`,
`systemctl --user`), never system ones, never with sudo, and says what it loaded and how to
unload it.

Every argv here is a fixed list. The label is held to the closed alphabet `LABEL` (no space,
slash or specifier), and a unit path must be the very file the service manager reads for that
label; anything else issues nothing and is a `failed` outcome. A label already loaded is left
alone: nothing that would unload or replace it (`bootout`, a second `bootstrap`) is ever issued.

Declared by `application/acp/interfaces/service_loader_interface.py`.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Final

from vibey.application.acp.dto import UnitAction, UnitOutcome
from vibey.domain.supervisor import LABEL
from vibey.infrastructure.acp.service_manager_runner import ServiceManagerRunner
from vibey.infrastructure.interfaces.supervisor_interface import SupervisorHostInterface
from vibey.infrastructure.supervisor import LAUNCHD, ServiceRunner

USER_MANAGER_STATES: Final = frozenset({"running", "degraded", "starting", "initializing"})
"""What `systemctl --user is-system-running` says when a user manager is there to load into."""
DETAIL_CHARS: Final = 400


class ServiceLoader:
    """Declared by `ServiceLoaderInterface`."""

    def __init__(
        self, host: SupervisorHostInterface, run: ServiceRunner, uid: int, *, euid: int
    ) -> None:
        self._host = host
        self._run = run
        self._uid = uid
        self._euid = euid
        self._launchd = host.platform == LAUNCHD

    def refused(self) -> str:
        if self._euid == 0:
            return (
                "vibey acp is running as root, and root's user-level units are daemons with "
                "root's power: vibey loads none of them; run your editor as yourself"
            )
        return ""

    def available(self) -> bool:
        try:
            if self._launchd:
                code, _ = self._issue(("launchctl", "print", f"gui/{self._uid}"))
                return code == 0
            _, out = self._issue(("systemctl", "--user", "is-system-running"))
        except OSError:
            return False
        return out.strip() in USER_MANAGER_STATES

    def state(self, label: str) -> str:
        if not LABEL.fullmatch(label):
            return "unknown: not a label vibey loads"
        return self._host.state(label)

    def load(self, label: str, unit: str) -> UnitOutcome:
        refusal = self._refusal(label, unit)
        if refusal:
            return UnitOutcome(label, unit, "failed", refusal)
        try:
            if self._launchd:
                code, _ = self._issue(("launchctl", "print", f"gui/{self._uid}/{label}"))
                if code == 0:
                    return UnitOutcome(label, unit, "already-loaded")
                return self._done(
                    label, unit, ("launchctl", "bootstrap", f"gui/{self._uid}", unit), "loaded"
                )
            if self._host.state(label) == "running":
                return UnitOutcome(label, unit, "already-loaded")
            reloaded = self._done(label, unit, ("systemctl", "--user", "daemon-reload"), "loaded")
            if reloaded.action == "failed":
                return reloaded
            return self._done(
                label,
                unit,
                ("systemctl", "--user", "enable", "--now", f"{label}.service"),
                "loaded",
            )
        except OSError as exc:
            return UnitOutcome(label, unit, "failed", self._cut(str(exc)))

    def restart(self, label: str) -> UnitOutcome:
        unit = str(self._host.unit_path(label)) if LABEL.fullmatch(label) else ""
        if not LABEL.fullmatch(label):
            return UnitOutcome(label, unit, "failed", "not a label vibey loads")
        argv = (
            ("launchctl", "kickstart", "-k", f"gui/{self._uid}/{label}")
            if self._launchd
            else ("systemctl", "--user", "restart", f"{label}.service")
        )
        try:
            return self._done(label, unit, argv, "restarted")
        except OSError as exc:
            return UnitOutcome(label, unit, "failed", self._cut(str(exc)))

    def unload(self, label: str) -> UnitOutcome:
        unit = str(self._host.unit_path(label)) if LABEL.fullmatch(label) else ""
        if not LABEL.fullmatch(label):
            return UnitOutcome(label, unit, "failed", "not a label vibey loads")
        try:
            if self._launchd:
                code, _ = self._issue(("launchctl", "print", f"gui/{self._uid}/{label}"))
                if code != 0:
                    return UnitOutcome(label, unit, "not-loaded")
                return self._done(
                    label, unit, ("launchctl", "bootout", f"gui/{self._uid}/{label}"), "unloaded"
                )
            if not Path(unit).exists():
                # The file was deleted by hand: `disable` would fail on it for good. Stop what
                # may still run from it, or say it is not loaded, so the record can be cleared.
                if self._host.state(label) != "running":
                    return UnitOutcome(label, unit, "not-loaded")
                return self._done(
                    label, unit, ("systemctl", "--user", "stop", f"{label}.service"), "unloaded"
                )
            return self._done(
                label,
                unit,
                ("systemctl", "--user", "disable", "--now", f"{label}.service"),
                "unloaded",
            )
        except OSError as exc:
            return UnitOutcome(label, unit, "failed", self._cut(str(exc)))

    def forget_unit_files(self) -> UnitOutcome:
        if self._launchd:
            return UnitOutcome("", "", "unchanged")
        try:
            return self._done("", "", ("systemctl", "--user", "daemon-reload"), "unchanged")
        except OSError as exc:
            return UnitOutcome("", "", "failed", self._cut(str(exc)))

    def unload_commands(self, labels: Sequence[str]) -> tuple[str, ...]:
        return tuple(self._host.unload_commands(labels))

    def domain(self) -> str:
        return f"launchd gui/{self._uid}" if self._launchd else "systemctl --user"

    def _refusal(self, label: str, unit: str) -> str:
        if not LABEL.fullmatch(label):
            return "not a label vibey loads"
        if Path(unit) != self._host.unit_path(label) or not Path(unit).is_absolute():
            return f"not the unit the service manager reads for {label}"
        return ""

    def _done(
        self, label: str, unit: str, argv: tuple[str, ...], action: UnitAction
    ) -> UnitOutcome:
        code, out = self._issue(argv)
        if code == 0:
            return UnitOutcome(label, unit, action)
        said = f"`{' '.join(argv[:2])}` exited {code}" + (f": {out.strip()}" if out.strip() else "")
        return UnitOutcome(label, unit, "failed", self._cut(said))

    def _issue(self, argv: tuple[str, ...]) -> tuple[int, str]:
        """Ask the runner, after checking once more that the argv is user-scoped: whatever
        runner the loader was given, it is never handed anything else."""
        refusal = ServiceManagerRunner.refusal(argv, self._uid)
        if refusal:
            raise PermissionError(f"refused: {refusal}")
        return self._run(argv)

    @staticmethod
    def _cut(text: str) -> str:
        return text[:DETAIL_CHARS]
