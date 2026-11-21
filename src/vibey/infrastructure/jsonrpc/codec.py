# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The JSON-RPC 2.0 line codec: one `json.dumps` per line, so MCP bytes stay what they were."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, Final

from vibey.infrastructure.jsonrpc.errors import INVALID_REQUEST, PARSE_ERROR, RpcError
from vibey.infrastructure.jsonrpc.interfaces.codec_interface import JsonRpcCodecInterface


class JsonRpcCodec:
    """Parses, frames and builds JSON-RPC 2.0 messages.

    Declared by `interfaces/codec_interface.py::JsonRpcCodecInterface`. `json.dumps` keeps its
    defaults (`ensure_ascii=True`, default separators): that escapes every newline inside a
    string, so one encoded message is always one line, and it is what keeps the MCP replies
    byte-identical to what they were before the codec was shared.
    """

    def is_blank(self, line: str) -> bool:
        return not line.strip()

    def decode(self, line: str) -> Mapping[str, Any]:
        try:
            parsed = json.loads(line.strip())
        except json.JSONDecodeError as exc:
            raise RpcError(PARSE_ERROR, f"Parse error: {exc.msg}") from exc
        if not isinstance(parsed, Mapping):
            raise RpcError(INVALID_REQUEST, "Invalid Request: expected JSON object")
        return parsed

    def parse_line(self, line: str) -> Mapping[str, Any] | dict[str, Any]:
        if self.is_blank(line):
            return {}
        try:
            return self.decode(line)
        except RpcError as exc:
            return self.error(None, exc.code, exc.message)

    def encode(self, message: Mapping[str, Any]) -> str:
        return json.dumps(message)

    def encode_strict(self, message: Mapping[str, Any]) -> str:
        return json.dumps(message, allow_nan=False)

    def ok(self, msg_id: Any, result: Mapping[str, Any]) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": msg_id, "result": dict(result)}

    def error(self, msg_id: Any, code: int, message: str, data: Any = None) -> dict[str, Any]:
        body: dict[str, Any] = {"code": code, "message": message}
        if data is not None:
            body["data"] = data
        return {"jsonrpc": "2.0", "id": msg_id, "error": body}

    def is_response(self, message: Mapping[str, Any]) -> bool:
        return (
            "method" not in message
            and "id" in message
            and ("result" in message or "error" in message)
        )

    def validate(
        self, message: Mapping[str, Any], *, allow_response: bool = False
    ) -> dict[str, Any] | None:
        well_formed = message.get("jsonrpc") == "2.0" and (
            isinstance(message.get("method"), str) or (allow_response and self.is_response(message))
        )
        if well_formed:
            return None
        return self.error(
            message.get("id"),
            INVALID_REQUEST,
            "Invalid Request: jsonrpc='2.0' and string method are required",
        )


CODEC: Final[JsonRpcCodecInterface] = JsonRpcCodec()
