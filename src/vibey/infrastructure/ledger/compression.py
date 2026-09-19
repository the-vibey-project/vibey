# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Lossless compression for ledger records (vibey#114).

Tiers move from raw (JSON) to compressed (zstd/lz4).
The core requirement is bit-for-bit reconstruction.
"""

from __future__ import annotations

import zlib

from vibey.infrastructure.ledger.interfaces.compression_interface import (
    CompressionCodecInterface,
)


class ZlibCodec(CompressionCodecInterface):
    """The standard-library lossless codec used by compressed ledger tiers."""

    def compress(self, data: bytes) -> bytes:
        return zlib.compress(data, level=9)

    def decompress(self, data: bytes) -> bytes:
        return zlib.decompress(data)


DEFAULT_CODEC: CompressionCodecInterface = ZlibCodec()
