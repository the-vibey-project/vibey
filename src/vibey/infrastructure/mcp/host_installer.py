# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Filesystem installer for `vibey connect`: reads host configs, writes backups, merges entries (ADR-0100).

`apply_plan` writes the way a config that may hold other servers' API keys deserves, because
`vibey acp` runs it unattended too:

- **Atomically.** The new content goes to a temporary file beside the target, which then
  replaces it (`os.replace`): a crash or a full disk never leaves a half-written config.
- **No wider than it was.** The new file keeps the old one's permission bits (a new file is
  0600), and the `.vibey.bak` copy gets the original's bits too, never the umask's 0644.
- **Only inside its scope's root.** A user-scope config is written only inside the home
  folder, a project-scope one only inside the project folder. The target's folder is resolved
  first (every symlink followed) and must lie inside the root's resolved path, however the
  target is spelled; a folder symlinked to another place inside the root still works.
- **Never through a symlinked file.** A config or `.vibey.bak` that is itself a symbolic link
  is refused. The files are opened and renamed relative to the resolved folder's descriptor,
  with `O_NOFOLLOW`, so a link swapped in after the check is never followed either.

Every target of a plan is checked before any file is written; a refusal is a
`HostClientError`.
"""

from __future__ import annotations

import os
import secrets
import shutil
import stat
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Final

from vibey.domain.host_clients import HOST_CLIENT_CATALOG, ConnectPlanItem, HostClientError
from vibey.domain.interfaces.host_clients_interface import HostClientsInterface
from vibey.infrastructure.mcp.interfaces.host_installer_interface import HostInstallerInterface


class HostInstaller:
    """Builds and applies host client registration plans (MCP servers, and Zed's ACP agent).

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
        environ: Mapping[str, str] = os.environ,
    ) -> None:
        self._catalog = catalog
        self._home_dir = home_dir
        self._project_dir = project_dir
        self._platform = platform
        self._which = which
        self._python_executable = python_executable
        self._environ = environ

    def build_plan(self, requested: Sequence[str] | None = None) -> tuple[ConnectPlanItem, ...]:
        specs = self._catalog.resolve_clients(requested)
        which_vibey = self._which("vibey")
        home = str(self._home_dir())
        proj = str(self._project_dir())
        xdg = self._environ.get("XDG_CONFIG_HOME")  # Zed on Linux follows it when absolute
        items: list[ConnectPlanItem] = []
        for spec in specs:
            # Each client launches what it speaks: `vibey mcp`, or `vibey acp` for Zed.
            launch = self._catalog.resolve_launch(
                which_vibey=which_vibey,
                python_executable=self._python_executable,
                protocol=spec.protocol,
            )
            target = Path(
                spec.config_path(
                    home_dir=home, project_dir=proj, platform=self._platform, xdg_config_home=xdg
                )
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
                    xdg_config_home=xdg,
                )
            )
        return tuple(items)

    def apply_plan(self, plan: Sequence[ConnectPlanItem]) -> None:
        pending = [(item, self._folder(item)) for item in plan if item.action != "unchanged"]
        for item, folder in pending:
            folder.mkdir(parents=True, exist_ok=True)
            self._write(item, folder)

    def _folder(self, item: ConnectPlanItem) -> Path:
        """The target's folder, resolved, after checking it lies inside the scope's root and that
        the target is not a symbolic link."""
        target = Path(item.target_path)
        scope_root = self._home_dir() if item.client.scope == "user" else self._project_dir()
        root = Path(os.path.realpath(scope_root))
        folder = Path(os.path.realpath(target.parent))
        where = "your home folder" if item.client.scope == "user" else "the project folder"
        if not folder.is_relative_to(root):
            raise HostClientError(f"{target} is not inside {where} ({root}); it is not written")
        for path in (target, *([Path(item.backup_path)] if item.backup_path else [])):
            if path.is_symlink():
                raise HostClientError(
                    f"{path} is a symbolic link; vibey does not write through one"
                )
        return folder

    def _write(self, item: ConnectPlanItem, folder: Path) -> None:
        name = Path(item.target_path).name
        directory = os.open(folder, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            mode, old = self._read(name, directory)
            if old is not None and item.backup_path is not None:
                self._create(Path(item.backup_path).name, directory, old, mode, replace=True)
            staged = f".{name}.{secrets.token_hex(6)}.tmp"
            self._create(staged, directory, item.new_content, mode, replace=False)
            try:
                os.replace(staged, name, src_dir_fd=directory, dst_dir_fd=directory)
            except BaseException:
                os.unlink(staged, dir_fd=directory)
                raise
        finally:
            os.close(directory)

    @staticmethod
    def _read(name: str, directory: int) -> tuple[int, str | None]:
        """The existing config's permission bits and text (0600 and None when there is none),
        read without following a link."""
        try:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
        except FileNotFoundError:
            return 0o600, None
        with os.fdopen(fd, encoding="utf-8") as handle:
            return stat.S_IMODE(os.fstat(handle.fileno()).st_mode), handle.read()

    @staticmethod
    def _create(name: str, directory: int, text: str, mode: int, *, replace: bool) -> None:
        flags = os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW | (os.O_TRUNC if replace else os.O_EXCL)
        handle = os.fdopen(os.open(name, flags, mode, dir_fd=directory), "w", encoding="utf-8")
        try:
            with handle:
                os.fchmod(handle.fileno(), mode)
                handle.write(text)
        except BaseException:
            if not replace:
                os.unlink(name, dir_fd=directory)
            raise


HOST_INSTALLER: Final[HostInstallerInterface] = HostInstaller()
