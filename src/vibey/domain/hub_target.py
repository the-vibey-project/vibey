# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Where a hub credential, or a probe of the hub, may be sent: this computer's loopback, and only
by an address literal decided here (SP-ACP Task 9b).

The hub's runtime record (`<state_dir>/serving.json`) names the host it listens on, and the state
folder can be named by a folder's `vibey.toml` -- a cloned repository's. So the host in a record is
untrusted: before the MCP gateway sends the agent token, or `vibey doctor` probes the hub, the
record's host must be one of exactly these, and the connection goes to the fixed loopback literal
this returns, never to the record's name resolved again:

- the wildcard binds `0.0.0.0` and `::` (the hub listens on every address, loopback included):
  `127.0.0.1` and `::1`;
- the exact, lowercase name `localhost`: `127.0.0.1`;
- an address literal that is loopback (`127.0.0.0/8`, `::1`), written canonically, or an
  IPv4-mapped IPv6 address whose IPv4 address is loopback: that address.

Nothing else: not `LOCALHOST`, not `localhost.`, not `*.localhost` (a resolver may answer those
from off the machine), not `127.1` or `0x7f.1`, not an address with a zone. This is stricter than
the search opener's no-proxy rule (`web/guarded_opener.py::GuardedOpener.is_loopback`), which
decides only whether a request bypasses a proxy, not where a credential may go; the two are kept
apart on purpose.

Pure: no I/O. Declared by `interfaces/hub_target_interface.py`.
"""

import ipaddress
from typing import Final

_WILDCARDS: Final = {"0.0.0.0": "127.0.0.1", "::": "::1"}  # nosec B104 - compared, never bound


class HubTargetPolicy:
    """Declared by `interfaces/hub_target_interface.py::HubTargetPolicyInterface`."""

    def loopback_address(self, host: str) -> str | None:
        """The loopback address literal to connect to for a record naming `host`, or None when
        `host` is not certainly this computer."""
        if host in _WILDCARDS:
            return _WILDCARDS[host]
        if host == "localhost":
            return "127.0.0.1"
        literal = host[1:-1] if host.startswith("[") and host.endswith("]") else host
        try:
            address = ipaddress.ip_address(literal)
        except ValueError:
            return None
        if isinstance(address, ipaddress.IPv6Address):
            if address.scope_id is not None:
                return None
            if address.ipv4_mapped is not None:
                address = address.ipv4_mapped
        return str(address) if address.is_loopback else None

    def lan_address(self, host: str) -> str | None:
        """The address literal to connect to for a host the person named on the command line
        (`vibey hub pair --host`), or None: this computer's loopback as `loopback_address`
        reads it, or an address literal -- never a name, never a zone -- on a private network
        (`PRIVATE_NETWORKS`). A runtime record never reaches here: only the person's own word
        may send a hub credential off the loopback."""
        loopback = self.loopback_address(host)
        if loopback is not None:
            return loopback
        literal = host[1:-1] if host.startswith("[") and host.endswith("]") else host
        try:
            address = ipaddress.ip_address(literal)
        except ValueError:
            return None
        if isinstance(address, ipaddress.IPv6Address):
            if address.scope_id is not None:
                return None
            if address.ipv4_mapped is not None:
                address = address.ipv4_mapped
        if any(address in network for network in PRIVATE_NETWORKS):
            return str(address)
        return None


PRIVATE_NETWORKS: Final = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("fc00::/7"),
)
"""The networks a hub may be paired over by `--host`: RFC 1918, the shared address space (RFC
6598, where an overlay such as Tailscale lives) and IPv6 unique local addresses. Not link-local
(`169.254.0.0/16` holds the clouds' metadata service; `fe80::/10` needs a zone), not a public
address, not a name."""

HUB_TARGETS: Final = HubTargetPolicy()
"""The one predicate every sender of a hub credential consults. Stateless."""
