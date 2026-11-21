# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""JSON-RPC 2.0 error codes and the exceptions a peer raises."""

from __future__ import annotations

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
