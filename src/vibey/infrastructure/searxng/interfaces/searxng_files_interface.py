# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for the SearXNG's files: its settings and its provision record (ADR-0102).

Implemented by `infrastructure/searxng/searxng_files.py`. Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pathlib import Path

    from vibey.domain.searxng import SearxngProvision


@runtime_checkable
class SearxngFilesInterface(Protocol):
    @property
    def folder(self) -> Path:
        """The folder both files live in."""
        ...

    @property
    def settings_path(self) -> Path:
        """`settings.yml`, the file a container mounts read-only."""
        ...

    def read(self) -> SearxngProvision | None:
        """The provision record; None when there is none. Raises ValueError for one that is a
        link or a FIFO, someone else's or open to others, too large, not JSON, or holds a value
        vibey would not have written (an image other than the pinned one included)."""
        ...

    def read_installed(self) -> SearxngProvision | None:
        """The record as an earlier vibey may have written it: every check but the pinned image
        (any SearXNG digest). For updating it and recognising its SearXNG, never for running it.
        Raises ValueError as `read` does for anything else."""
        ...

    def settings_marker(self) -> str | None:
        """The marker `settings.yml` names, read as carefully as the record; None when there is
        no settings file vibey can believe."""
        ...

    def settings_ready(self) -> bool:
        """Whether `settings.yml` exists as a regular file the person owns, closed to everyone
        else (never a link or a FIFO)."""
        ...

    def disabled(self) -> bool:
        """Whether the person stopped it for good (`vibey acp unload`, `vibey searxng
        uninstall`); a mark vibey cannot believe counts as stopped."""
        ...

    def disable(self) -> None:
        """Leave the mark that stops it for good."""
        ...

    def enable(self) -> None:
        """Remove that mark (`vibey searxng install`)."""
        ...

    def ensure(self, *, image: str, port: int, label: str, runtime: str) -> SearxngProvision:
        """Write the settings (once: a kept file keeps its secret and marker, while it names the
        record's marker; otherwise both are made again) and the record, staged then renamed as a
        pair.
        Raises ValueError, writing nothing, for a value vibey would not run, or for a folder
        that is a link or someone else's; `OSError` when a file cannot be written."""
        ...

    def purge(self) -> tuple[str, ...]:
        """Delete both files, and the folder when nothing else is in it; the names removed."""
        ...
