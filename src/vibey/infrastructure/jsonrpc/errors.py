# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""JSON-RPC 2.0 error codes and the exceptions a peer raises.

The codes and `RpcError` are protocol vocabulary held in `vibey/domain/jsonrpc_errors.py`, so
the ACP agent in the application layer can raise them too (SP-ACP); they are re-exported here
unchanged. The two exceptions below describe this peer's stream, so they stay here.
"""

from __future__ import annotations

from vibey.domain.jsonrpc_errors import INTERNAL_ERROR as INTERNAL_ERROR
from vibey.domain.jsonrpc_errors import INVALID_PARAMS as INVALID_PARAMS
from vibey.domain.jsonrpc_errors import INVALID_REQUEST as INVALID_REQUEST
from vibey.domain.jsonrpc_errors import METHOD_NOT_FOUND as METHOD_NOT_FOUND
from vibey.domain.jsonrpc_errors import PARSE_ERROR as PARSE_ERROR
from vibey.domain.jsonrpc_errors import RpcError as RpcError


class PeerClosed(Exception):
    """The input stream reached EOF, so no reply to an outbound request can arrive."""


class PeerCancelled(Exception):
    """An outbound request was resolved locally by `cancel_outbound` instead of by a reply."""
