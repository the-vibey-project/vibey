# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The Nextcloud file storage seam.

Mirrors `vibey/infrastructure/files/nextcloud.py` (ADR-0016). Interfaces declare;
they never consume.
"""

from typing import Protocol, runtime_checkable

from vibey.application.interfaces.files import FilesPort


@runtime_checkable
class NextcloudFilesAdapterInterface(FilesPort, Protocol):
    """The self-hosted Nextcloud WebDAV implementation of the Files port."""
