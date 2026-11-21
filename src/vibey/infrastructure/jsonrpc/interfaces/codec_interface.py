# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for the JSON-RPC 2.0 line codec."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class JsonRpcCodecInterface(Protocol):
    def is_blank(self, line: str) -> bool:
        """True for a line that is empty or whitespace only; callers skip it."""
        ...

    def decode(self, line: str) -> Mapping[str, Any]:
        """Parse one line to a JSON object, raising `RpcError` (PARSE_ERROR or INVALID_REQUEST)."""
        ...

    def parse_line(self, line: str) -> Mapping[str, Any] | dict[str, Any]:
        """Parse one line: the message, `{}` for a blank line, or a ready error response (id None)."""
        ...

    def encode(self, message: Mapping[str, Any]) -> str:
        """Serialise one message exactly as `json.dumps` does, with no trailing newline."""
        ...

    def ok(self, msg_id: Any, result: Mapping[str, Any]) -> dict[str, Any]:
        """A success response."""
        ...

    def error(self, msg_id: Any, code: int, message: str, data: Any = None) -> dict[str, Any]:
        """An error response; the `data` member is present only when `data` is not None."""
        ...

    def is_response(self, message: Mapping[str, Any]) -> bool:
        """True when `message` has the shape of a response: an id, a result or error, no method."""
        ...

    def validate(
        self, message: Mapping[str, Any], *, allow_response: bool = False
    ) -> dict[str, Any] | None:
        """The envelope check; the error response to send, or None when the message is well formed."""
        ...
