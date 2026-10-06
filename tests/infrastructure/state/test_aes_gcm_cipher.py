# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`AesGcmStateCipher` and `StateKey`: a sealed snapshot opens under its key and nothing else."""

import base64

import pytest

from vibey.application.interfaces.state_sync import StateCipher
from vibey.domain.state_sync import SnapshotUnreadable
from vibey.infrastructure.state.aes_gcm_cipher import (
    KEY_BYTES,
    MAGIC,
    NONCE_BYTES,
    AesGcmStateCipher,
    StateKey,
)

DOCUMENT = b'{"schema": 1, "tables": {"project": []}}' * 20


def cipher() -> AesGcmStateCipher:
    return AesGcmStateCipher(StateKey.parse(StateKey.new()))


def test_the_cipher_satisfies_its_interface() -> None:
    assert isinstance(cipher(), StateCipher)


def test_a_sealed_document_opens_back_to_itself() -> None:
    sealer = cipher()
    sealed = sealer.seal(DOCUMENT)
    assert sealed.startswith(MAGIC)
    assert DOCUMENT not in sealed
    assert sealer.open(sealed) == DOCUMENT


def test_two_seals_of_the_same_document_differ_but_open_the_same() -> None:
    sealer = cipher()
    first, second = sealer.seal(DOCUMENT), sealer.seal(DOCUMENT)
    assert first != second
    assert (
        first[len(MAGIC) : len(MAGIC) + NONCE_BYTES]
        != second[len(MAGIC) : len(MAGIC) + NONCE_BYTES]
    )
    assert sealer.open(first) == sealer.open(second) == DOCUMENT


def test_a_snapshot_sealed_under_another_key_does_not_open() -> None:
    sealed = cipher().seal(DOCUMENT)
    with pytest.raises(SnapshotUnreadable, match="sealed under another key"):
        cipher().open(sealed)


@pytest.mark.parametrize("position", [len(MAGIC), len(MAGIC) + NONCE_BYTES, -1])
def test_one_flipped_bit_does_not_open(position: int) -> None:
    sealer = cipher()
    sealed = bytearray(sealer.seal(DOCUMENT))
    sealed[position] ^= 0x01
    with pytest.raises(SnapshotUnreadable, match="changed after it was sealed"):
        sealer.open(bytes(sealed))


@pytest.mark.parametrize(
    "sealed",
    [
        b"",
        b"not a vibey state at all, just bytes",
        b"VBYSTAT2" + bytes(64),
        MAGIC,
        MAGIC + bytes(NONCE_BYTES),
    ],
)
def test_bytes_that_are_not_a_sealed_state_are_unreadable(sealed: bytes) -> None:
    with pytest.raises(SnapshotUnreadable, match="does not hold a sealed vibey state"):
        cipher().open(sealed)


@pytest.mark.parametrize("length", [0, 16, KEY_BYTES - 1, KEY_BYTES + 1])
def test_the_cipher_takes_a_32_byte_key_only(length: int) -> None:
    with pytest.raises(ValueError, match=f"must be {KEY_BYTES} bytes"):
        AesGcmStateCipher(bytes(length))


def test_a_new_key_is_unpadded_base64url_of_32_random_bytes() -> None:
    text = StateKey.new()
    assert "=" not in text and "+" not in text and "/" not in text
    assert len(StateKey.parse(text)) == KEY_BYTES
    assert StateKey.parse(f"  {text}\n") == StateKey.parse(text)
    assert StateKey.new() != text


def test_a_padded_key_parses_too() -> None:
    raw = bytes(range(KEY_BYTES))
    assert StateKey.parse(base64.urlsafe_b64encode(raw).decode()) == raw


@pytest.mark.parametrize(
    "text",
    [
        "",
        "abcde",  # not base64 at all: one character past a whole group
        "ключ",  # not ASCII
        base64.urlsafe_b64encode(bytes(16)).decode(),  # base64, but 16 bytes
        base64.urlsafe_b64encode(bytes(KEY_BYTES + 1)).decode(),
    ],
)
def test_a_key_that_is_not_32_bytes_of_base64url_is_refused(text: str) -> None:
    with pytest.raises(ValueError, match="vibey state key --new"):
        StateKey.parse(text)
