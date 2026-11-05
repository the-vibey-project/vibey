# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Filesystem installer for `vibey connect`: reads host configs, writes backups, merges entries (ADR-0100)."""

from __future__ import annotations

import shutil
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Final

from vibey.domain.host_clients import HOST_CLIENT_CATALOG, ConnectPlanItem
from vibey.domain.interfaces.host_clients_interface import HostClientsInterface
from vibey.infrastructure.mcp.interfaces.host_installer_interface import HostInstallerInterface


class HostInstaller:
    """Builds and applies MCP host client registration plans.

    Declared by `interfaces/host_installer_interface.py::HostInstallerInterface`.
    """

    def __init__(
        self,
        *,
        catalog: HostClientsInterface = HOST_CLIENT_CATALOG,
        home_dir: Callable[[], Path] = Path.home,
        project_dir: Callable[[], Path] = Path.cwd,
        platform: str = sys.platform,
        which: Callable[[str], str | None] = shutil.which,
        python_executable: str = sys.executable,
    ) -> None:
        self._catalog = catalog
        self._home_dir = home_dir
        self._project_dir = project_dir
        self._platform = platform
        self._which = which
        self._python_executable = python_executable

    def build_plan(self, requested: Sequence[str] | None = None) -> tuple[ConnectPlanItem, ...]:
        specs = self._catalog.resolve_clients(requested)
        launch = self._catalog.resolve_launch(
            which_vibey=self._which("vibey"),
            python_executable=self._python_executable,
        )
        home = str(self._home_dir())
        proj = str(self._project_dir())
        items: list[ConnectPlanItem] = []
        for spec in specs:
            target = Path(
                spec.config_path(home_dir=home, project_dir=proj, platform=self._platform)
            )
            existing = target.read_text(encoding="utf-8") if target.exists() else None
            items.append(
                self._catalog.plan_one(
                    spec,
                    home_dir=home,
                    project_dir=proj,
                    platform=self._platform,
                    launch=launch,
                    existing_content=existing,
                )
            )
        return tuple(items)

    def apply_plan(self, plan: Sequence[ConnectPlanItem]) -> None:
        for item in plan:
            if item.action == "unchanged":
                continue
            target = Path(item.target_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            if item.backup_path is not None and target.exists():
                backup = Path(item.backup_path)
                backup.write_text(target.read_text(encoding="utf-8"), encoding="utf-8")
            target.write_text(item.new_content, encoding="utf-8")


HOST_INSTALLER: Final[HostInstallerInterface] = HostInstaller()
