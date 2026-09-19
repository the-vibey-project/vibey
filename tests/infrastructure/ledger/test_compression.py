# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

from vibey.infrastructure.ledger.compression import DEFAULT_CODEC, ZlibCodec
from vibey.infrastructure.ledger.interfaces.compression_interface import (
    CompressionCodecInterface,
)


def test_zlib_codec_satisfies_its_interface_and_round_trips_bytes() -> None:
    payload = bytes(range(256)) * 8

    assert isinstance(DEFAULT_CODEC, CompressionCodecInterface)
    assert isinstance(ZlibCodec(), CompressionCodecInterface)
    assert DEFAULT_CODEC.decompress(DEFAULT_CODEC.compress(payload)) == payload
