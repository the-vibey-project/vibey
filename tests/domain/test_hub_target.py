# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Where a hub credential may be sent (SP-ACP Task 9b): this computer's loopback, by a fixed
literal, and nothing a resolver could answer from elsewhere.

Module-level test functions rather than a class with an interface beside it (ADR-0016)."""

import pytest

from vibey.domain.hub_target import HUB_TARGETS
from vibey.domain.interfaces.hub_target_interface import HubTargetPolicyInterface
from vibey.infrastructure.web.guarded_opener import GuardedOpener


def test_the_policy_meets_its_seam() -> None:
    assert isinstance(HUB_TARGETS, HubTargetPolicyInterface)


@pytest.mark.parametrize(
    ("host", "connect"),
    [
        ("localhost", "127.0.0.1"),
        ("127.0.0.1", "127.0.0.1"),
        ("127.8.9.10", "127.8.9.10"),
        ("::1", "::1"),
        ("[::1]", "::1"),
        ("0.0.0.0", "127.0.0.1"),
        ("::", "::1"),
        ("[::ffff:127.0.0.1]", "127.0.0.1"),
        ("::ffff:127.0.0.1", "127.0.0.1"),
    ],
)
def test_this_computer_is_reached_by_a_fixed_loopback_literal(host: str, connect: str) -> None:
    assert HUB_TARGETS.loopback_address(host) == connect


@pytest.mark.parametrize(
    "host",
    [
        "evil.localhost",
        "localhost.",
        "LOCALHOST",
        "Localhost",
        "localhost.localdomain",
        "127.1",
        "0x7f.1",
        "2130706433",
        "0177.0.0.1",
        "[::ffff:10.0.0.1]",
        "::ffff:10.0.0.1",
        "fe80::1%en0",
        "::1%lo0",
        "10.0.0.1",
        "203.0.113.9",
        "hub.example",
        "",
    ],
)
def test_anything_else_is_not_a_place_to_send_a_credential(host: str) -> None:
    assert HUB_TARGETS.loopback_address(host) is None


def test_the_search_proxy_bypass_keeps_its_own_wider_forms() -> None:
    """A different question -- whether a request may skip a proxy -- with its own answer: these
    count as local for search, and are still never a place to send a hub credential."""
    for host in ("evil.localhost", "localhost."):
        assert GuardedOpener.is_loopback(f"http://{host}:28180/")
        assert HUB_TARGETS.loopback_address(host) is None


@pytest.mark.parametrize(
    ("host", "connect"),
    [
        ("192.168.1.5", "192.168.1.5"),
        ("10.0.0.7", "10.0.0.7"),
        ("172.16.4.4", "172.16.4.4"),
        ("100.101.102.103", "100.101.102.103"),
        ("fd12:3456::1", "fd12:3456::1"),
        ("[fd12:3456::1]", "fd12:3456::1"),
        ("::ffff:192.168.1.5", "192.168.1.5"),
        ("localhost", "127.0.0.1"),
        ("0.0.0.0", "127.0.0.1"),
    ],
)
def test_a_host_the_person_names_may_be_a_private_network_literal(host: str, connect: str) -> None:
    assert HUB_TARGETS.lan_address(host) == connect


@pytest.mark.parametrize(
    "host",
    [
        "studio.local",
        "example.com",
        "8.8.8.8",
        "169.254.169.254",
        "fe80::1",
        "fe80::1%en0",
        "fd12::1%en0",
        "172.32.0.1",
        "100.128.0.1",
        "192.168.1",
        "0xc0.0xa8.1.5",
        "3232235781",
        "::ffff:8.8.8.8",
        "2001:db8::1",
        "",
    ],
)
def test_a_name_or_a_public_link_local_or_odd_spelling_is_never_a_lan_hub(host: str) -> None:
    assert HUB_TARGETS.lan_address(host) is None
