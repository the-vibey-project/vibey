# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""JSON-RPC 2.0 error codes and the error a handler raises to choose its reply.

Protocol vocabulary, so it lives in the domain: the ACP agent in `application/acp/` raises
`RpcError` to answer a request with a JSON-RPC error, and the application layer may not import
infrastructure. `infrastructure/jsonrpc/errors.py` re-exports these names unchanged, so the
peer and the MCP server read them where they always did. Value types and constants only
(ADR-0016 exempts them from the interface rule). Pure: no I/O.
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
