# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The SearXNG vibey runs, as files: its `settings.yml` and its provision record (ADR-0102).

Both live in `<the person's configuration folder>/searxng/` (`SearxngFiles.personal`), never in a
project: what search believes is the person's own, and so is what a unit mounts into a container.

- **The folder** is made 0700 (and narrowed to 0700 when it was wider), must be a real folder the
  person owns, and is opened once with `O_NOFOLLOW`; every file is reached relative to that
  descriptor, so a link swapped in for the folder or for a file is never followed.
- **A write** is staged under a random name with `O_CREAT|O_EXCL|O_NOFOLLOW`, mode 0600, synced,
  then renamed over the old file (a link there is replaced, never written through), and the
  folder synced.
- **`settings.yml`** is written once: a random 32-byte `secret_key` and the identity marker
  (`vibey-<32 hex>`) are made with `secrets` and kept. A later install keeps the file and its
  marker; only a lost settings file is made again, with a new marker.
- **`provision.json`** is the record: what was installed, read back with every value checked
  (`SearxngPlan.parse`), so a changed record cannot widen the container's command line. It is
  written last, so a record always names settings that exist.

Declared by `interfaces/searxng_files_interface.py`.
"""

from __future__ import annotations

import contextlib
import json
import os
import secrets
import stat
from collections.abc import Callable
from pathlib import Path
from typing import Final

from vibey.domain.interfaces.searxng_interface import SearxngPlanInterface
from vibey.domain.searxng import SearxngPlan, SearxngProvision
from vibey.infrastructure.user_config_folder import UserConfigFolder

FOLDER: Final = "searxng"
SETTINGS_FILE: Final = "settings.yml"
RECORD_FILE: Final = "provision.json"
_READ_LIMIT: Final = 1 << 16


class SearxngFiles:
    """Declared by `SearxngFilesInterface`. `token_hex` is `secrets.token_hex`, a seam."""

    def __init__(
        self,
        folder: Path,
        *,
        plan: SearxngPlanInterface | None = None,
        token_hex: Callable[[int], str] = secrets.token_hex,
    ) -> None:
        self._folder = folder
        self._plan = plan or SearxngPlan()
        self._token_hex = token_hex

    @classmethod
    def personal(cls) -> SearxngFiles:
        """The person's own: `<configuration folder>/searxng`."""
        return cls(UserConfigFolder().path() / FOLDER)

    @property
    def folder(self) -> Path:
        return self._folder

    @property
    def settings_path(self) -> Path:
        return self._folder / SETTINGS_FILE

    def read(self) -> SearxngProvision | None:
        try:
            folder = os.open(self._folder, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise ValueError(f"{self._folder} is a link or not a folder: {exc}") from None
        try:
            return self._read_at(folder)
        finally:
            os.close(folder)

    def _read_at(self, folder: int) -> SearxngProvision | None:
        try:
            fd = os.open(RECORD_FILE, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=folder)
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise ValueError(
                f"{RECORD_FILE} cannot be read (a link, or not a file): {exc}"
            ) from None
        with os.fdopen(fd, "rb") as handle:
            raw = handle.read(_READ_LIMIT)
        try:
            data = json.loads(raw)
        except (ValueError, RecursionError):
            raise ValueError(f"{RECORD_FILE} is not JSON") from None
        return self._plan.parse(data)

    def settings_ready(self) -> bool:
        try:
            found = os.lstat(self.settings_path)
        except OSError:
            return False
        return stat.S_ISREG(found.st_mode)

    def ensure(self, *, image: str, port: int, label: str, runtime: str) -> SearxngProvision:
        folder = self._open_folder()
        try:
            try:
                current = self._read_at(folder)
            except ValueError:
                current = None  # not vibey's record: made again below, settings and all
            keep = current is not None and self._is_file(folder, SETTINGS_FILE)
            marker = (
                current.marker
                if keep and current is not None
                else self._plan.new_marker(self._token_hex(16))
            )
            provision = SearxngProvision(
                image=image, port=port, marker=marker, label=label, runtime=runtime
            )
            record = self._plan.record(provision)  # refuses a bad value before anything is written
            if not keep:
                text = self._plan.settings_text(secret_key=self._token_hex(32), marker=marker)
                self._write(folder, SETTINGS_FILE, text)
            self._write(folder, RECORD_FILE, json.dumps(record, indent=2) + "\n")
        finally:
            os.close(folder)
        return provision

    def purge(self) -> tuple[str, ...]:
        removed: list[str] = []
        try:
            folder = os.open(self._folder, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        except OSError:
            return ()
        try:
            for name in (SETTINGS_FILE, RECORD_FILE):
                with contextlib.suppress(FileNotFoundError):
                    os.unlink(name, dir_fd=folder)
                    removed.append(name)
        finally:
            os.close(folder)
        with contextlib.suppress(OSError):
            os.rmdir(self._folder)  # only when nothing else is in it
        return tuple(removed)

    # -- writing -------------------------------------------------------------------------------

    def _open_folder(self) -> int:
        self._folder.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with contextlib.suppress(FileExistsError):
            os.mkdir(self._folder, 0o700)
        try:
            fd = os.open(self._folder, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        except OSError as exc:
            raise ValueError(
                f"{self._folder} is a link or not a folder, so vibey writes nothing there: {exc}"
            ) from None
        found = os.fstat(fd)
        if found.st_uid != os.getuid():
            os.close(fd)
            raise ValueError(f"{self._folder} is not yours, so vibey writes nothing there")
        if stat.S_IMODE(found.st_mode) != 0o700:
            os.fchmod(fd, 0o700)
        return fd

    @staticmethod
    def _is_file(folder: int, name: str) -> bool:
        try:
            found = os.stat(name, dir_fd=folder, follow_symlinks=False)
        except OSError:
            return False
        return stat.S_ISREG(found.st_mode)

    def _write(self, folder: int, name: str, text: str) -> None:
        staged = f".{name}.{self._token_hex(8)}.tmp"
        fd = os.open(
            staged, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=folder
        )
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(staged, name, src_dir_fd=folder, dst_dir_fd=folder)
        finally:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(staged, dir_fd=folder)
        os.fsync(folder)
