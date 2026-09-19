# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://github.com/adammatthewsteinberger/).
"""The seam implemented by lossless ledger compression codecs."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class CompressionCodecInterface(Protocol):
    """Round-trips arbitrary bytes without loss."""

    def compress(self, data: bytes) -> bytes: ...

    def decompress(self, data: bytes) -> bytes: ...
