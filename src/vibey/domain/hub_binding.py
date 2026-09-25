# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Where the hub may listen, and which names a request may reach it by.

The hub listens on the loopback interface unless the host's `vibey.toml` declares
`[hub] lan = true` (ADR-0067, sub-doctrine 12.c): a network surface is a decision written
down in the repository, never a flag somebody typed once. `HubBindingPolicy.resolve` turns
the address asked for into the address to bind, and refuses a non-loopback address the
configuration does not declare. `exposure` is the same rule read the other way, for
`vibey doctor`: given where a running hub is bound, is that exposure declared?

`admits` is the DNS-rebinding defence. A browser page on another origin can make a name
it controls resolve to 127.0.0.1 and then send requests carrying that name in `Host`. The
hub answers only a `Host` it expects -- its own loopback names and port, or the names the
host declared -- so such a request is refused before any route runs.

Pure: the standard library's `ipaddress` only.
"""

import ipaddress
from enum import StrEnum
from typing import Final

from vibey.domain.errors import VibeyError

LOOPBACK_DEFAULT: Final = "127.0.0.1"
"""The address bound when none is asked for."""

LOOPBACK_NAMES: Final[frozenset[str]] = frozenset({"localhost", "127.0.0.1", "::1"})
"""The loopback names a `Host` header may carry, before the port."""


class UndeclaredExposure(VibeyError):
    """A non-loopback address was asked for and `[hub] lan = true` is not declared."""


class Exposure(StrEnum):
    """What a hub's bound address exposes, as `vibey doctor` reports it."""

    LOOPBACK = "loopback"
    DECLARED_LAN = "declared_lan"
    UNDECLARED = "undeclared"


class HubBindingPolicy:
    """Decides the bind address and the `Host` names a request may use. Pure.

    Declared by `interfaces/hub_binding_interface.py::HubBindingPolicyInterface`."""

    def is_loopback(self, host: str) -> bool:
        """True for `localhost` and every address in 127.0.0.0/8 or ::1."""
        if host == "localhost":
            return True
        try:
            return ipaddress.ip_address(host.strip("[]")).is_loopback
        except ValueError:
            return False

    def resolve(self, requested: str | None, *, lan_declared: bool) -> str:
        """The address to bind: loopback when none is asked for; `requested` when it is
        loopback or the LAN is declared. Raises `UndeclaredExposure` otherwise."""
        if requested is None:
            return LOOPBACK_DEFAULT
        if self.is_loopback(requested) or lan_declared:
            return requested
        raise UndeclaredExposure(
            f"refusing to listen on {requested}: it is not loopback, and vibey.toml does "
            "not declare [hub] lan = true"
        )

    def exposure(self, bound: str, *, lan_declared: bool) -> Exposure:
        """What a hub bound to `bound` exposes, given the declaration."""
        if self.is_loopback(bound):
            return Exposure.LOOPBACK
        return Exposure.DECLARED_LAN if lan_declared else Exposure.UNDECLARED

    def allowed_hosts(self, port: int, names: frozenset[str]) -> frozenset[str]:
        """Every `Host` value the hub answers: each loopback name and each of `names`,
        with and without `:port`. IPv6 literals appear bracketed, as `Host` carries them."""
        allowed: set[str] = set()
        for name in LOOPBACK_NAMES | names:
            shown = f"[{name}]" if ":" in name and not name.startswith("[") else name
            allowed.update({shown.lower(), f"{shown.lower()}:{port}"})
        return frozenset(allowed)

    def admits(self, host_header: str | None, allowed: frozenset[str]) -> bool:
        """True only when `host_header` is present and one of `allowed`."""
        return host_header is not None and host_header.strip().lower() in allowed


HUB_BINDING: Final = HubBindingPolicy()
"""The policy `vibey serve` and `vibey doctor` both read. Stateless, so one instance serves."""
