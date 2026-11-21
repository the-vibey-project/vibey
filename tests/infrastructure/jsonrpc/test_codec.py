# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Unit tests for the JSON-RPC 2.0 line codec (SP-ACP Task 1).

Module-level test functions rather than a class with an interface beside it (ADR-0016).
"""

from __future__ import annotations

import json

import pytest

from vibey.infrastructure.jsonrpc.codec import CODEC, JsonRpcCodec
from vibey.infrastructure.jsonrpc.errors import INVALID_REQUEST, PARSE_ERROR, RpcError
from vibey.infrastructure.jsonrpc.interfaces.codec_interface import JsonRpcCodecInterface


def test_the_singleton_satisfies_the_interface() -> None:
    assert isinstance(CODEC, JsonRpcCodecInterface)
    assert isinstance(JsonRpcCodec(), JsonRpcCodecInterface)


def test_parse_line_reports_parse_error_with_null_id() -> None:
    assert CODEC.parse_line("{nope") == {
        "jsonrpc": "2.0",
        "id": None,
        "error": {
            "code": -32700,
            "message": "Parse error: Expecting property name enclosed in double quotes",
        },
    }


@pytest.mark.parametrize("line", ["[1, 2]", "42", '"text"', "null"])
def test_parse_line_refuses_non_objects_as_invalid_request(line: str) -> None:
    reply = CODEC.parse_line(line)
    assert reply["id"] is None
    assert reply["error"] == {"code": -32600, "message": "Invalid Request: expected JSON object"}


def test_parse_line_returns_the_message_and_empty_for_blank() -> None:
    assert CODEC.parse_line('  {"jsonrpc": "2.0", "id": 1}  \n') == {"jsonrpc": "2.0", "id": 1}
    assert CODEC.parse_line("   \n") == {}
    assert CODEC.is_blank("   \n") is True
    assert CODEC.is_blank(" x ") is False


def test_decode_raises_rpc_error_with_the_code() -> None:
    with pytest.raises(RpcError) as parse:
        CODEC.decode("{")
    assert parse.value.code == PARSE_ERROR
    with pytest.raises(RpcError) as shape:
        CODEC.decode("[]")
    assert shape.value.code == INVALID_REQUEST
    assert CODEC.decode('{"a": 1}') == {"a": 1}


def test_encode_never_emits_a_raw_newline() -> None:
    encoded = CODEC.encode({"text": "a\nb\r\nc d", "n": 1})
    assert "\n" not in encoded and "\r" not in encoded
    assert json.loads(encoded)["text"] == "a\nb\r\nc d"


def test_encode_is_exactly_json_dumps() -> None:
    message = {"jsonrpc": "2.0", "id": "x", "result": {"café": [1, None, True]}}
    assert CODEC.encode(message) == json.dumps(message)


def test_ok_and_error_shapes() -> None:
    assert CODEC.ok(7, {"a": 1}) == {"jsonrpc": "2.0", "id": 7, "result": {"a": 1}}
    assert CODEC.error(7, -32601, "no") == {
        "jsonrpc": "2.0",
        "id": 7,
        "error": {"code": -32601, "message": "no"},
    }


def test_error_omits_data_when_none() -> None:
    assert "data" not in CODEC.error(1, -1, "m")["error"]
    assert "data" not in CODEC.error(1, -1, "m", None)["error"]
    assert CODEC.error(1, -1, "m", {"why": 1})["error"]["data"] == {"why": 1}
    assert CODEC.error(1, -1, "m", 0)["error"]["data"] == 0


def test_validate_accepts_a_request_and_a_notification() -> None:
    assert CODEC.validate({"jsonrpc": "2.0", "id": 1, "method": "ping"}) is None
    assert CODEC.validate({"jsonrpc": "2.0", "method": "note"}) is None


@pytest.mark.parametrize(
    "message",
    [
        {"jsonrpc": "1.0", "id": 1, "method": "ping"},
        {"jsonrpc": "2.0", "id": 1, "method": 5},
        {"id": 1, "method": "ping"},
        {"jsonrpc": "2.0", "id": 1, "result": {}},
    ],
)
def test_validate_refuses_a_bad_envelope_echoing_the_id(message: dict[str, object]) -> None:
    reply = CODEC.validate(message)
    assert reply is not None
    assert reply["id"] == 1
    assert reply["error"]["code"] == INVALID_REQUEST


def test_validate_gives_a_null_id_when_the_message_has_none() -> None:
    reply = CODEC.validate({"jsonrpc": "2.0", "method": 123})
    assert reply is not None and reply["id"] is None


def test_validate_allows_a_response_shape_only_when_asked() -> None:
    response = {"jsonrpc": "2.0", "id": "a", "result": {}}
    failure = {"jsonrpc": "2.0", "id": "a", "error": {"code": 1, "message": "m"}}
    assert CODEC.validate(response, allow_response=True) is None
    assert CODEC.validate(failure, allow_response=True) is None
    assert CODEC.validate(response) is not None
    assert CODEC.validate({"jsonrpc": "2.0", "id": "a"}, allow_response=True) is not None
    assert CODEC.validate({"jsonrpc": "1.0", "id": "a", "result": {}}, allow_response=True)


def test_is_response() -> None:
    assert CODEC.is_response({"id": 1, "result": {}}) is True
    assert CODEC.is_response({"id": 1, "error": {}}) is True
    assert CODEC.is_response({"id": 1, "method": "m", "result": {}}) is False
    assert CODEC.is_response({"result": {}}) is False
    assert CODEC.is_response({"id": 1}) is False


def test_encode_strict_refuses_nan_and_infinity_while_encode_keeps_its_bytes() -> None:
    message = {"n": float("nan")}
    assert CODEC.encode(message) == '{"n": NaN}'
    with pytest.raises(ValueError):
        CODEC.encode_strict(message)
    assert CODEC.encode_strict({"a": 1}) == CODEC.encode({"a": 1})
