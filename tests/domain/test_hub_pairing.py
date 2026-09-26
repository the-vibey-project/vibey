# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The pairing rules: codes, expiry, the signed form, the URI (ADR-0068)."""

import pytest

from vibey.domain.hub_pairing import (
    HUB_PAIRING,
    PAIRING_TTL_SECONDS,
    SIGNATURE_WINDOW_SECONDS,
    PairingRefused,
)
from vibey.domain.hub_scope import HubScope
from vibey.domain.interfaces.hub_pairing_interface import HubPairingPolicyInterface

VIEW = frozenset({HubScope.VIEW})


def test_the_policy_meets_its_declared_seam() -> None:
    assert isinstance(HUB_PAIRING, HubPairingPolicyInterface)


def test_an_offer_is_good_for_two_minutes_and_only_for_its_code() -> None:
    offer = HUB_PAIRING.offer("012345", VIEW, 100.0)
    assert offer.expires_at == 100.0 + PAIRING_TTL_SECONDS == 220.0
    assert HUB_PAIRING.claims(offer, "012345", 219.9)
    assert not HUB_PAIRING.claims(offer, "012345", 220.0)
    assert not HUB_PAIRING.claims(offer, "012346", 150.0)
    assert not HUB_PAIRING.claims(offer, "", 150.0)


@pytest.mark.parametrize("digits", ["12345", "1234567", "12345a", "١٢٣٤٥٦", ""])
def test_a_code_is_six_ascii_digits(digits: str) -> None:
    with pytest.raises(PairingRefused):
        HUB_PAIRING.offer(digits, VIEW, 0.0)


def test_an_offer_that_grants_nothing_is_refused() -> None:
    """Deny by default: a key that opens nothing is a key someone widens later."""
    with pytest.raises(PairingRefused):
        HUB_PAIRING.offer("123456", frozenset(), 0.0)


def test_a_signed_timestamp_is_fresh_only_inside_the_window() -> None:
    assert HUB_PAIRING.fresh(1000.0, 1000.0 + SIGNATURE_WINDOW_SECONDS)
    assert HUB_PAIRING.fresh(1000.0, 1000.0 - SIGNATURE_WINDOW_SECONDS)
    assert not HUB_PAIRING.fresh(1000.0, 1000.0 + SIGNATURE_WINDOW_SECONDS + 0.1)


def test_the_canonical_form_binds_every_field_and_refuses_a_newline() -> None:
    fields = {
        "device_id": "d1",
        "method": "post",
        "path": "/api/v1/gates/x/answer",
        "query": "a=1",
        "timestamp": "1000",
        "nonce": "n1",
        "body_sha256": "ab",
    }
    signed = HUB_PAIRING.canonical(**fields)
    assert signed == b"d1\nPOST\n/api/v1/gates/x/answer\na=1\n1000\nn1\nab"
    for name in fields:
        changed = dict(fields, **{name: fields[name] + "z"})
        assert HUB_PAIRING.canonical(**changed) != signed
    with pytest.raises(ValueError):
        HUB_PAIRING.canonical(**dict(fields, path="/a\n/b"))


def test_the_uri_carries_where_the_fingerprint_and_the_code() -> None:
    uri = HUB_PAIRING.uri(host="192.168.1.5", port=8765, fingerprint="ab12", code="012345")
    assert uri == "vibey-pair://192.168.1.5:8765?fp=ab12&code=012345&v=1"
    assert HUB_PAIRING.uri(host="::1", port=1, fingerprint="f", code="000000").startswith(
        "vibey-pair://[::1]:1?"
    )
