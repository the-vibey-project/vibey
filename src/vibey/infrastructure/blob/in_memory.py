# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""In-memory Blob implementation of the Blob storage port (ADR-0042)."""

from __future__ import annotations

from vibey.application.interfaces.blob import BlobPort


class InMemoryBlob(BlobPort):
    """Faked object storage for testing and unconfigured local runs."""

    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}

    async def put_blob(
        self, bucket: str, key: str, content: bytes, content_type: str | None = None
    ) -> str:
        del content_type
        self.objects[(bucket, key)] = bytes(content)
        return f"memory://{bucket}/{key}"

    async def get_blob(self, bucket: str, key: str) -> bytes:
        try:
            return self.objects[(bucket, key)]
        except KeyError:
            raise FileNotFoundError(f"blob {bucket}/{key} not found") from None
