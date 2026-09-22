# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""In-memory Files implementation of the File manager port (ADR-0042)."""

from __future__ import annotations

from vibey.application.interfaces.files import FilesPort


class InMemoryFiles(FilesPort):
    """Faked file store for testing and unconfigured local runs."""

    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    async def upload_file(self, remote_path: str, content: bytes) -> str:
        self.files[remote_path] = content
        return f"memory://{remote_path}"

    async def download_file(self, remote_path: str) -> bytes:
        if remote_path not in self.files:
            raise FileNotFoundError(remote_path)
        return self.files[remote_path]
