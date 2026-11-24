# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""JSON-RPC 2.0 error codes, the error a handler raises to choose its reply, and the peer's own.

Protocol vocabulary, shared by every speaker of the wire format in the family: vibey's MCP
server and ACP agent, and the local runner's MCP client (SP-LOOPS Phase 5 R1). The ACP agent in
vibey's application layer raises `RpcError` to answer a request with a JSON-RPC error; it may
import this module because `vibey-runners-common` is a dependency-free family package
(ADR-0017), and this module pulls in no `asyncio`. Value types and constants only (ADR-0016
exempts them from the interface rule). Pure: no I/O.
"""

from typing import Any, Final

PARSE_ERROR: Final = -32700
INVALID_REQUEST: Final = -32600
METHOD_NOT_FOUND: Final = -32601
INVALID_PARAMS: Final = -32602
INTERNAL_ERROR: Final = -32603


class RpcError(Exception):
    """A JSON-RPC error: raised by a handler to choose its reply, or by `request` for a remote one."""

    def __init__(self, code: int, message: str, data: Any = None) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.data = data


class PeerClosed(Exception):
    """The input stream reached EOF, so no reply to an outbound request can arrive."""


class PeerCancelled(Exception):
    """An outbound request was resolved locally by `cancel_outbound` instead of by a reply."""
