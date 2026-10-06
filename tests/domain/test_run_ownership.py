# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`RunOwnership`: a workflows request id names its starter, and only its starter's name
verifies it (ADR-0085)."""

import pytest

from vibey.domain.interfaces.run_ownership_interface import RunOwnershipInterface
from vibey.domain.remote_command import RemoteCommand
from vibey.domain.run_ownership import MIN_KEY_BYTES, NONCE_CHARS, TAG_CHARS, RunOwnership

KEY = bytes(range(32))
NONCE = "0123456789abcdef01234567"
PHONE = "device:phone"
TABLET = "device:tablet"


def test_it_meets_its_declared_seam() -> None:
    assert isinstance(RunOwnership(KEY), RunOwnershipInterface)


def test_a_minted_id_is_a_request_id_and_names_a_run() -> None:
    minted = RunOwnership(KEY).mint(PHONE, NONCE)
    assert len(minted) == NONCE_CHARS + 1 + TAG_CHARS <= 64
    assert minted.startswith(f"{NONCE}-")
    assert RemoteCommand.REQUEST_ID.fullmatch(minted)
    assert RemoteCommand(("status",), minted).run_name == f"vibey {minted}"


def test_an_id_verifies_for_its_owner_alone() -> None:
    ownership = RunOwnership(KEY)
    minted = ownership.mint(PHONE, NONCE)
    assert ownership.owns(PHONE, minted)
    assert not ownership.owns(TABLET, minted)
    assert not ownership.owns("host", minted)


def test_the_same_nonce_under_another_owner_or_key_is_another_id() -> None:
    assert RunOwnership(KEY).mint(PHONE, NONCE) != RunOwnership(KEY).mint(TABLET, NONCE)
    other = RunOwnership(bytes(reversed(KEY)))
    assert not other.owns(PHONE, RunOwnership(KEY).mint(PHONE, NONCE))


def test_a_restarted_hub_with_the_same_key_recognises_its_ids() -> None:
    assert RunOwnership(KEY).owns(PHONE, RunOwnership(bytes(KEY)).mint(PHONE, NONCE))


def _flip(text: str, index: int) -> str:
    replacement = "1" if text[index] == "0" else "0"
    return text[:index] + replacement + text[index + 1 :]


@pytest.mark.parametrize("index", [0, NONCE_CHARS - 1, NONCE_CHARS + 1, NONCE_CHARS + TAG_CHARS])
def test_a_tampered_nonce_or_tag_is_refused(index: int) -> None:
    ownership = RunOwnership(KEY)
    minted = ownership.mint(PHONE, NONCE)
    assert not ownership.owns(PHONE, _flip(minted, index))


@pytest.mark.parametrize(
    "request_id",
    [
        "",
        "0123456789abcdef",  # a random CLI id: never minted for anyone
        "0123456789abcdef0123456789abcdef",
        f"{NONCE}-",
        f"{NONCE}-{'0' * (TAG_CHARS - 1)}",
        f"{NONCE}-{'0' * (TAG_CHARS + 1)}",
        f"{NONCE.upper()}-{'0' * TAG_CHARS}",
        f"{NONCE}_{'0' * TAG_CHARS}",
        f"{NONCE}-{'0' * TAG_CHARS}-x",
    ],
)
def test_anything_not_shaped_like_a_minted_id_is_refused(request_id: str) -> None:
    assert not RunOwnership(KEY).owns(PHONE, request_id)


def test_a_short_key_is_refused() -> None:
    with pytest.raises(ValueError, match=f"at least {MIN_KEY_BYTES} bytes"):
        RunOwnership(b"k" * (MIN_KEY_BYTES - 1))


@pytest.mark.parametrize("nonce", ["", NONCE[:-1], NONCE + "0", NONCE.upper(), "g" * NONCE_CHARS])
def test_a_nonce_that_is_not_hex_of_the_right_length_is_refused(nonce: str) -> None:
    with pytest.raises(ValueError, match="lowercase hex"):
        RunOwnership(KEY).mint(PHONE, nonce)
