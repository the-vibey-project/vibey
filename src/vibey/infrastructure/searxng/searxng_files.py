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
  (`SearxngPlan.parse`), so a changed record cannot widen the container's command line. The pair
  is staged first and renamed settings-then-record; a failed second rename removes the first, and
  a pair whose markers disagree (a crash between the renames) is made again, both files.
- **Reading** opens without following links and non-blocking (a FIFO can never hang search,
  doctor or `serve`), and refuses anything but a regular file the person owns, closed to everyone
  else (0600 or narrower), within a size cap; the folder must be the person's and closed too.
- **`disabled`** is the mark `vibey acp unload` and `vibey searxng uninstall` leave: stopped for
  good until `vibey searxng install` removes it.

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
DISABLED_FILE: Final = "disabled"
"""Present once `vibey acp unload` or `vibey searxng uninstall` stopped it for good: nothing
loads, restarts, serves or offers it again until `vibey searxng install` removes the mark."""
DISABLED: Final = "stopped for good by vibey acp unload or vibey searxng uninstall\n"
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
    def personal(cls, config_folder: Path | None = None) -> SearxngFiles:
        """The person's own: `<their configuration folder>/searxng`, the folder `config_folder`
        names when given (the one their `vibey.toml` was read from). Every caller finds the files
        here, so one stand-in keeps a test suite off the person's own."""
        return cls((config_folder or UserConfigFolder().path()) / FOLDER)

    @property
    def folder(self) -> Path:
        return self._folder

    @property
    def settings_path(self) -> Path:
        return self._folder / SETTINGS_FILE

    def read(self) -> SearxngProvision | None:
        raw = self._raw(RECORD_FILE)
        return None if raw is None else self._parse(raw)

    def read_installed(self) -> SearxngProvision | None:
        raw = self._raw(RECORD_FILE)
        return None if raw is None else self._plan.parse_installed(self._json(raw))

    def settings_marker(self) -> str | None:
        try:
            raw = self._raw(SETTINGS_FILE)
        except ValueError:
            return None
        return None if raw is None else self._plan.marker_in(raw.decode("utf-8", "replace"))

    def _raw(self, name: str) -> bytes | None:
        folder = self._reading()
        if folder is None:
            return None
        try:
            return self._read_file(folder, name)
        finally:
            os.close(folder)

    def settings_ready(self) -> bool:
        try:
            folder = self._reading()
            if folder is None:
                return False
            try:
                return self._read_file(folder, SETTINGS_FILE) is not None
            finally:
                os.close(folder)
        except ValueError:
            return False

    def disabled(self) -> bool:
        try:
            folder = self._reading()
            if folder is None:
                return False
            try:
                return self._read_file(folder, DISABLED_FILE) is not None
            finally:
                os.close(folder)
        except ValueError:
            return True  # a mark vibey cannot believe is not a reason to start anything

    def disable(self) -> None:
        folder = self._open_folder()
        try:
            self._publish(folder, [(DISABLED_FILE, self._stage(folder, DISABLED_FILE, DISABLED))])
        finally:
            os.close(folder)

    def enable(self) -> None:
        try:
            folder = self._reading()
        except ValueError:
            folder = self._open_folder()  # narrows the folder, or refuses one not the person's
        if folder is None:
            return
        try:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(DISABLED_FILE, dir_fd=folder)
        finally:
            os.close(folder)

    def ensure(self, *, image: str, port: int, label: str, runtime: str) -> SearxngProvision:
        folder = self._open_folder()
        try:
            current = self._believed(folder, RECORD_FILE)
            settings = self._believed(folder, SETTINGS_FILE)
            current_record = None if current is None else self._parse_or_none(current)
            # The pair is kept only while it agrees: the settings must name the record's marker,
            # or the identity check could never pass again (a crash between two writes, or two
            # writers interleaved). Anything else is made again, both files at once.
            keep = (
                current_record is not None
                and settings is not None
                and self._plan.marker_in(settings.decode("utf-8", "replace"))
                == current_record.marker
            )
            marker = (
                current_record.marker
                if keep and current_record is not None
                else self._plan.new_marker(self._token_hex(16))
            )
            provision = SearxngProvision(
                image=image, port=port, marker=marker, label=label, runtime=runtime
            )
            record = json.dumps(self._plan.record(provision), indent=2) + "\n"  # refuses first
            staged: list[tuple[str, str]] = []
            try:
                if not keep:
                    text = self._plan.settings_text(secret_key=self._token_hex(32), marker=marker)
                    staged.append((SETTINGS_FILE, self._stage(folder, SETTINGS_FILE, text)))
                staged.append((RECORD_FILE, self._stage(folder, RECORD_FILE, record)))
                self._publish(folder, staged)
            finally:
                for _, name in staged:
                    with contextlib.suppress(FileNotFoundError):
                        os.unlink(name, dir_fd=folder)
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
            for name in (SETTINGS_FILE, RECORD_FILE, DISABLED_FILE):
                with contextlib.suppress(FileNotFoundError):
                    os.unlink(name, dir_fd=folder)
                    if name != DISABLED_FILE:
                        removed.append(name)
        finally:
            os.close(folder)
        with contextlib.suppress(OSError):
            os.rmdir(self._folder)  # only when nothing else is in it
        return tuple(removed)

    # -- reading -------------------------------------------------------------------------------

    def _reading(self) -> int | None:
        """The folder, opened without following a link and checked: the person's own, and open
        to no one else. None when it does not exist."""
        try:
            folder = os.open(self._folder, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise ValueError(f"{self._folder} is a link or not a folder: {exc}") from None
        found = os.fstat(folder)
        if found.st_uid != os.getuid() or found.st_mode & 0o077:
            os.close(folder)
            raise ValueError(
                f"{self._folder} is not yours alone (owner or mode), so vibey reads nothing there"
            )
        return folder

    @staticmethod
    def _read_file(folder: int, name: str) -> bytes | None:
        """A file of the folder, or None when it is not there. Refused (ValueError): a link, a
        FIFO or anything but a regular file (opened non-blocking, so nothing hangs), someone
        else's, readable or writable by anyone but the person, or larger than vibey writes."""
        try:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=folder)
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise ValueError(f"{name} cannot be read (a link, or not a file): {exc}") from None
        try:
            found = os.fstat(fd)
            if not stat.S_ISREG(found.st_mode):
                raise ValueError(f"{name} is not a regular file")
            if found.st_uid != os.getuid() or found.st_mode & 0o077:
                raise ValueError(f"{name} is not yours alone (owner or a mode wider than 0600)")
            if found.st_size > _READ_LIMIT:
                raise ValueError(f"{name} is larger than vibey ever writes it")
            return os.read(fd, _READ_LIMIT)
        finally:
            os.close(fd)

    def _parse(self, raw: bytes) -> SearxngProvision:
        return self._plan.parse(self._json(raw))

    @staticmethod
    def _json(raw: bytes) -> object:
        try:
            return json.loads(raw)
        except (ValueError, RecursionError):
            raise ValueError(f"{RECORD_FILE} is not JSON") from None

    def _parse_or_none(self, raw: bytes) -> SearxngProvision | None:
        """The record as installed (an earlier pin's image is kept: updating it keeps its marker
        and settings), or None when it is not one vibey wrote."""
        try:
            return self._plan.parse_installed(self._json(raw))
        except ValueError:
            return None  # not vibey's record: made again, settings and all

    def _believed(self, folder: int, name: str) -> bytes | None:
        try:
            return self._read_file(folder, name)
        except ValueError:
            return None  # replaced below, never written through

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

    def _stage(self, folder: int, name: str, text: str) -> str:
        """`text` in a new 0600 file beside `name`, synced: its name."""
        staged = f".{name}.{self._token_hex(8)}.tmp"
        fd = os.open(
            staged, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=folder
        )
        with os.fdopen(fd, "w", encoding="utf-8") as handle:  # owns the descriptor from here
            os.fchmod(handle.fileno(), 0o600)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        return staged

    def _publish(self, folder: int, staged: list[tuple[str, str]]) -> None:
        """Rename each staged file over its name, in order. When a later rename fails, the ones
        already published by this call are removed, so a half-written pair is never left."""
        done: list[str] = []
        try:
            for name, temporary in staged:
                os.replace(temporary, name, src_dir_fd=folder, dst_dir_fd=folder)
                done.append(name)
        except OSError:
            for name in done:
                with contextlib.suppress(FileNotFoundError):
                    os.unlink(name, dir_fd=folder)
            raise
        finally:
            os.fsync(folder)
