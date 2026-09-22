# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The Blob storage port seam (ADR-0042)."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class BlobPort(Protocol):
    """Common protocol for FOSS S3-compatible object storage (sovereign default: Garage)."""

    async def put_blob(
        self, bucket: str, key: str, content: bytes, content_type: str | None = None
    ) -> str:
        """Store bytes under bucket/key (creating the bucket when missing); return its locator."""
        ...

    async def get_blob(self, bucket: str, key: str) -> bytes:
        """Return the bytes stored under bucket/key; missing is FileNotFoundError."""
        ...
