# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The File manager port seam (ADR-0042)."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class FilesPort(Protocol):
    """Common protocol for file and document storage."""

    async def upload_file(self, remote_path: str, content: bytes) -> str:
        """Upload file content to a remote path and return its public URL/locator."""
        ...

    async def download_file(self, remote_path: str) -> bytes:
        """Download binary content of a file from its remote path."""
        ...
