# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Where the hub may listen, and the Host allowlist that defends against DNS rebinding."""

import pytest

from vibey.domain.hub_binding import HUB_BINDING, Exposure, UndeclaredExposure
from vibey.domain.interfaces.hub_binding_interface import HubBindingPolicyInterface


def test_the_policy_meets_its_seam() -> None:
    assert isinstance(HUB_BINDING, HubBindingPolicyInterface)


@pytest.mark.parametrize(
    ("host", "loopback"),
    [
        ("localhost", True),
        ("127.8.9.10", True),
        ("::1", True),
        ("[::1]", True),
        ("192.168.1.20", False),
        ("0.0.0.0", False),  # nosec B104 - a value under test
        ("example.com", False),
    ],
)
def test_loopback_is_recognised(host: str, loopback: bool) -> None:
    assert HUB_BINDING.is_loopback(host) is loopback


def test_loopback_by_default_and_the_lan_only_when_declared() -> None:
    assert HUB_BINDING.resolve(None, lan_declared=False) == "127.0.0.1"
    assert HUB_BINDING.resolve("::1", lan_declared=False) == "::1"
    assert HUB_BINDING.resolve("192.168.1.20", lan_declared=True) == "192.168.1.20"
    with pytest.raises(UndeclaredExposure, match=r"\[hub\] lan = true"):
        HUB_BINDING.resolve("0.0.0.0", lan_declared=False)  # nosec B104 - refused


def test_exposure_names_what_is_declared() -> None:
    assert HUB_BINDING.exposure("127.0.0.1", lan_declared=False) is Exposure.LOOPBACK
    assert HUB_BINDING.exposure("192.168.1.20", lan_declared=True) is Exposure.DECLARED_LAN
    assert HUB_BINDING.exposure("192.168.1.20", lan_declared=False) is Exposure.UNDECLARED


def test_only_expected_hosts_are_admitted() -> None:
    allowed = HUB_BINDING.allowed_hosts(8765, frozenset({"studio.local", "fe80::2"}))
    assert {
        "localhost",
        "127.0.0.1:8765",
        "[::1]:8765",
        "studio.local:8765",
        "[fe80::2]:8765",
    } <= allowed
    assert HUB_BINDING.admits("LOCALHOST:8765", allowed)
    assert not HUB_BINDING.admits(None, allowed)
    assert not HUB_BINDING.admits("attacker.example:8765", allowed)
