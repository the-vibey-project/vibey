# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Unit tests for the asyncio JSON-RPC peer (SP-ACP Task 1).

No test waits on the real clock: progress is driven by yielding to the loop until a condition
holds. Module-level test functions rather than a class with an interface beside it (ADR-0016).
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable, Mapping
from typing import Any

import pytest

from vibey.infrastructure.jsonrpc.codec import CODEC
from vibey.infrastructure.jsonrpc.errors import (
    INTERNAL_ERROR,
    INVALID_PARAMS,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    PARSE_ERROR,
    PeerCancelled,
    PeerClosed,
    RpcError,
)
from vibey.infrastructure.jsonrpc.interfaces.peer_interface import JsonRpcPeerInterface
from vibey.infrastructure.jsonrpc.peer import JsonRpcPeer


async def _until(predicate: Callable[[], bool], spins: int = 500) -> None:
    for _ in range(spins):
        if predicate():
            return
        await asyncio.sleep(0)
    raise AssertionError("condition never became true")


def _line(**message: Any) -> bytes:
    return (json.dumps({"jsonrpc": "2.0", **message}) + "\n").encode()


class _Rig:
    """A peer on a test-fed StreamReader, recording what it writes and what its handlers see."""

    def __init__(self, *, limit: int = 65536, max_message_bytes: int = 65536) -> None:
        self.reader = asyncio.StreamReader(limit=limit)
        self.chunks: list[str] = []
        self.requests: list[tuple[str, Mapping[str, Any]]] = []
        self.notifications: list[tuple[str, Mapping[str, Any]]] = []
        self.request_handler: Callable[[str, Mapping[str, Any]], Any] = self._echo
        self.notification_handler: Callable[[str, Mapping[str, Any]], Any] = self._note
        self.write_hook: Callable[[str], Any] | None = None
        self.peer = JsonRpcPeer(
            self.reader,
            self._write,
            on_request=self._on_request,
            on_notification=self._on_notification,
            codec=CODEC,
            id_prefix="test",
            max_message_bytes=max_message_bytes,
        )
        self.task: asyncio.Task[None] | None = None

    def start(self) -> None:
        self.task = asyncio.create_task(self.peer.run())

    def feed(self, data: bytes) -> None:
        self.reader.feed_data(data)

    async def finish(self) -> None:
        self.reader.feed_eof()
        assert self.task is not None
        await asyncio.wait_for(self.task, 5)

    @property
    def replies(self) -> list[dict[str, Any]]:
        return [json.loads(chunk) for chunk in self.chunks]

    async def _write(self, line: str) -> None:
        if self.write_hook is not None:
            await self.write_hook(line)
        self.chunks.append(line)

    async def _on_request(self, method: str, params: Mapping[str, Any]) -> Mapping[str, Any]:
        self.requests.append((method, params))
        result = self.request_handler(method, params)
        return await result  # type: ignore[no-any-return]

    async def _on_notification(self, method: str, params: Mapping[str, Any]) -> None:
        self.notifications.append((method, params))
        await self.notification_handler(method, params)

    @staticmethod
    async def _echo(method: str, params: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"echo": method, "params": dict(params)}

    @staticmethod
    async def _note(method: str, params: Mapping[str, Any]) -> None:
        return None


async def test_the_peer_satisfies_its_interface() -> None:
    rig = _Rig()
    assert isinstance(rig.peer, JsonRpcPeerInterface)


async def test_inbound_request_gets_one_response_with_its_id() -> None:
    rig = _Rig()
    rig.start()
    rig.feed(_line(id=41, method="ping", params={"a": 1}))
    await _until(lambda: len(rig.chunks) == 1)
    assert rig.replies == [
        {"jsonrpc": "2.0", "id": 41, "result": {"echo": "ping", "params": {"a": 1}}}
    ]
    assert rig.chunks[0].endswith("\n") and rig.chunks[0].count("\n") == 1
    await rig.finish()
    assert len(rig.chunks) == 1


async def test_a_request_without_params_gets_empty_params() -> None:
    rig = _Rig()
    rig.start()
    rig.feed(_line(id="s", method="ping"))
    await _until(lambda: rig.chunks)
    assert rig.requests == [("ping", {})]
    await rig.finish()


async def test_notifications_never_get_a_response() -> None:
    rig = _Rig()
    rig.start()
    rig.feed(_line(method="poke", params={"x": 1}) + _line(method="poke"))
    await _until(lambda: len(rig.notifications) == 2)
    assert rig.notifications == [("poke", {"x": 1}), ("poke", {})]
    await rig.finish()
    assert rig.chunks == []


async def test_blank_lines_are_skipped() -> None:
    rig = _Rig()
    rig.start()
    rig.feed(b"\n   \n" + _line(id=1, method="ping"))
    await _until(lambda: rig.chunks)
    await rig.finish()
    assert len(rig.chunks) == 1


async def test_handlers_run_concurrently_so_a_notification_lands_mid_request() -> None:
    rig = _Rig()
    poked = asyncio.Event()

    async def slow(method: str, params: Mapping[str, Any]) -> Mapping[str, Any]:
        await poked.wait()
        return {"poked": True}

    async def poke(method: str, params: Mapping[str, Any]) -> None:
        poked.set()

    rig.request_handler = slow
    rig.notification_handler = poke
    rig.start()
    rig.feed(_line(id=1, method="slow") + _line(method="poke"))
    await _until(lambda: rig.chunks)
    assert rig.replies == [{"jsonrpc": "2.0", "id": 1, "result": {"poked": True}}]
    await rig.finish()


async def test_handlers_start_in_arrival_order() -> None:
    rig = _Rig()
    started: list[str] = []

    async def record(method: str, params: Mapping[str, Any]) -> Mapping[str, Any]:
        started.append(str(params["n"]))
        await asyncio.sleep(0)
        return {}

    rig.request_handler = record
    rig.start()
    rig.feed(b"".join(_line(id=n, method="m", params={"n": n}) for n in range(20)))
    await _until(lambda: len(rig.chunks) == 20)
    assert started == [str(n) for n in range(20)]
    await rig.finish()


async def test_outbound_request_resolves_by_id_out_of_order() -> None:
    rig = _Rig()
    rig.start()
    first = asyncio.create_task(rig.peer.request("a", {"n": 1}))
    second = asyncio.create_task(rig.peer.request("b", {"n": 2}))
    await _until(lambda: len(rig.chunks) == 2)
    sent = rig.replies
    ids = {m["method"]: m["id"] for m in sent}
    assert ids == {"a": "test-1", "b": "test-2"}
    assert sent[0]["params"] == {"n": 1} and sent[0]["jsonrpc"] == "2.0"
    rig.feed(_line(id=ids["b"], result={"which": "b"}) + _line(id=ids["a"], result={"which": "a"}))
    assert await first == {"which": "a"}
    assert await second == {"which": "b"}
    await rig.finish()


async def test_outbound_error_response_raises_rpc_error_with_code() -> None:
    rig = _Rig()
    rig.start()
    pending = asyncio.create_task(rig.peer.request("a", {}))
    await _until(lambda: rig.chunks)
    rig.feed(_line(id="test-1", error={"code": -32001, "message": "nope", "data": {"k": 1}}))
    with pytest.raises(RpcError) as raised:
        await pending
    assert (raised.value.code, raised.value.message, raised.value.data) == (
        -32001,
        "nope",
        {"k": 1},
    )
    await rig.finish()


async def test_malformed_error_and_result_shapes_are_tolerated() -> None:
    rig = _Rig()
    rig.start()
    bad_error = asyncio.create_task(rig.peer.request("a", {}))
    odd_error = asyncio.create_task(rig.peer.request("b", {}))
    odd_result = asyncio.create_task(rig.peer.request("c", {}))
    await _until(lambda: len(rig.chunks) == 3)
    rig.feed(
        _line(id="test-1", error="boom")
        + _line(id="test-2", error={"code": "x", "message": 7})
        + _line(id="test-3", result=None)
    )
    for task in (bad_error, odd_error):
        with pytest.raises(RpcError) as raised:
            await task
        assert raised.value.code == INTERNAL_ERROR
        assert raised.value.message == "malformed error response"
    assert await odd_result == {}
    await rig.finish()


async def test_unknown_response_id_is_logged_to_stderr_and_dropped(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rig = _Rig()
    rig.start()
    rig.feed(_line(id="never-sent", result={}) + _line(id=[1], result={}) + _line(id=1, method="m"))
    await _until(lambda: rig.chunks)
    await rig.finish()
    captured = capsys.readouterr()
    assert captured.err.count("unknown id") == 2
    assert "never-sent" in captured.err
    assert captured.out == ""
    assert len(rig.chunks) == 1  # only the request got a reply


async def test_a_duplicate_response_is_ignored_without_noise(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rig = _Rig()
    rig.start()
    pending = asyncio.create_task(rig.peer.request("a", {}))
    await _until(lambda: rig.chunks)
    rig.feed(_line(id="test-1", result={"n": 1}) + _line(id="test-1", result={"n": 2}))
    assert await pending == {"n": 1}
    await rig.finish()
    assert capsys.readouterr().err == ""


async def test_handler_exception_becomes_internal_error_and_the_peer_keeps_serving(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rig = _Rig()

    async def boom(method: str, params: Mapping[str, Any]) -> Mapping[str, Any]:
        if method == "boom":
            raise ValueError("secret detail")
        return {"fine": True}

    rig.request_handler = boom
    rig.start()
    rig.feed(_line(id=1, method="boom") + _line(id=2, method="ok"))
    await _until(lambda: len(rig.chunks) == 2)
    by_id = {r["id"]: r for r in rig.replies}
    assert by_id[1]["error"] == {"code": INTERNAL_ERROR, "message": "Internal error: ValueError"}
    assert by_id[2]["result"] == {"fine": True}
    await rig.finish()
    err = capsys.readouterr().err
    assert "ValueError" in err and "secret detail" in err  # to stderr only, never to the client


async def test_rpc_error_from_handler_keeps_its_code_and_data() -> None:
    rig = _Rig()

    async def refuse(method: str, params: Mapping[str, Any]) -> Mapping[str, Any]:
        raise RpcError(-32000, "auth required", {"methods": ["a"]})

    rig.request_handler = refuse
    rig.start()
    rig.feed(_line(id=1, method="m"))
    await _until(lambda: rig.chunks)
    assert rig.replies[0]["error"] == {
        "code": -32000,
        "message": "auth required",
        "data": {"methods": ["a"]},
    }
    await rig.finish()


async def test_unknown_method_is_method_not_found() -> None:
    rig = _Rig()

    async def route(method: str, params: Mapping[str, Any]) -> Mapping[str, Any]:
        raise RpcError(METHOD_NOT_FOUND, f"Method not found: {method}")

    rig.request_handler = route
    rig.start()
    rig.feed(_line(id=9, method="nope"))
    await _until(lambda: rig.chunks)
    assert rig.replies[0]["error"]["code"] == METHOD_NOT_FOUND
    assert rig.replies[0]["id"] == 9
    await rig.finish()


async def test_a_failing_notification_handler_is_logged_and_the_peer_keeps_serving(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rig = _Rig()

    async def boom(method: str, params: Mapping[str, Any]) -> None:
        raise RuntimeError("bad note")

    rig.notification_handler = boom
    rig.start()
    rig.feed(_line(method="n") + _line(id=1, method="ping"))
    await _until(lambda: rig.chunks)
    await rig.finish()
    assert "bad note" in capsys.readouterr().err


async def test_non_object_params_are_invalid_params_for_a_request_and_dropped_for_a_note(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rig = _Rig()
    rig.start()
    rig.feed(_line(id=1, method="m", params=[1]) + _line(method="n", params="x"))
    await _until(lambda: rig.chunks)
    await rig.finish()
    assert rig.replies[0]["error"]["code"] == INVALID_PARAMS
    assert rig.requests == [] and rig.notifications == []
    assert "dropped notification" in capsys.readouterr().err


async def test_malformed_input_is_answered_and_the_peer_keeps_serving() -> None:
    rig = _Rig()
    rig.start()
    rig.feed(
        b"{nope\n[1]\n"
        + b'{"jsonrpc": "1.0", "id": 5, "method": "m"}\n'
        + b"\xff\xfe\n"
        + _line(id=1, method="ping")
    )
    await _until(lambda: len(rig.chunks) == 5)
    codes = [r.get("error", {}).get("code") for r in rig.replies]
    assert codes == [PARSE_ERROR, INVALID_REQUEST, INVALID_REQUEST, PARSE_ERROR, None]
    assert rig.replies[2]["id"] == 5
    assert rig.replies[3]["error"]["message"] == "Parse error: invalid UTF-8"
    assert rig.replies[4]["result"]["echo"] == "ping"
    await rig.finish()


async def test_writes_are_serialised_one_whole_line_at_a_time() -> None:
    rig = _Rig()
    events: list[str] = []

    async def slowly(line: str) -> None:
        events.append("start")
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        events.append("end")

    rig.write_hook = slowly
    rig.start()
    await asyncio.gather(*(rig.peer.notify("n", {"i": i}) for i in range(50)))
    assert events == ["start", "end"] * 50
    assert len(rig.chunks) == 50
    for chunk in rig.chunks:
        assert chunk.endswith("\n") and chunk.count("\n") == 1
        assert json.loads(chunk)["method"] == "n"
    assert {json.loads(c)["params"]["i"] for c in rig.chunks} == set(range(50))
    assert all("id" not in json.loads(c) for c in rig.chunks)
    await rig.finish()


async def test_a_dead_output_stream_is_logged_and_does_not_stop_the_peer(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rig = _Rig()
    failures = {"left": 1}

    async def flaky(line: str) -> None:
        if failures["left"]:
            failures["left"] -= 1
            raise BrokenPipeError("gone")

    rig.write_hook = flaky
    rig.start()
    rig.feed(_line(id=1, method="m") + _line(id=2, method="m"))
    await _until(lambda: len(rig.requests) == 2 and rig.chunks)
    await rig.finish()
    assert [r["id"] for r in rig.replies] == [2]
    assert "could not write a reply" in capsys.readouterr().err


async def test_eof_fails_pending_outbound_with_peer_closed() -> None:
    rig = _Rig()
    rig.start()
    pending = asyncio.create_task(rig.peer.request("a", {}))
    await _until(lambda: rig.chunks)
    await rig.finish()
    with pytest.raises(PeerClosed):
        await pending
    with pytest.raises(PeerClosed):
        await rig.peer.request("late", {})


async def test_a_reply_read_just_before_eof_still_resolves_its_request() -> None:
    rig = _Rig()
    rig.start()
    pending = asyncio.create_task(rig.peer.request("a", {}))
    await _until(lambda: rig.chunks)
    rig.feed(_line(id="test-1", result={"made": "it"}))
    await rig.finish()
    assert await pending == {"made": "it"}


async def test_eof_stops_handlers_that_are_still_running() -> None:
    rig = _Rig()
    cancelled = asyncio.Event()

    async def hang(method: str, params: Mapping[str, Any]) -> Mapping[str, Any]:
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            cancelled.set()
            raise
        return {}

    rig.request_handler = hang
    rig.start()
    rig.feed(_line(id=1, method="hang"))
    await _until(lambda: rig.requests)
    await rig.finish()
    assert cancelled.is_set()
    assert rig.chunks == []


async def test_cancel_outbound_resolves_matching_requests_only() -> None:
    rig = _Rig()
    rig.start()
    keep = asyncio.create_task(rig.peer.request("keep", {"session": "s2"}))
    drop_a = asyncio.create_task(rig.peer.request("ask", {"session": "s1"}))
    drop_b = asyncio.create_task(rig.peer.request("ask", {"session": "s1"}))
    await _until(lambda: len(rig.chunks) == 3)
    ids = rig.peer.cancel_outbound(lambda method, params: params.get("session") == "s1")
    assert ids == ("test-2", "test-3")
    assert rig.peer.cancel_outbound(lambda method, params: params.get("session") == "s1") == ()
    for task in (drop_a, drop_b):
        with pytest.raises(PeerCancelled):
            await task
    assert not keep.done()
    rig.feed(_line(id="test-1", result={"kept": True}))
    assert await keep == {"kept": True}
    await rig.finish()


async def test_oversized_line_is_refused_and_the_next_line_is_served() -> None:
    rig = _Rig(limit=65536, max_message_bytes=65536)
    rig.start()
    rig.feed(b"x" * 70_000 + b"\n" + _line(id=1, method="ping"))
    await _until(lambda: len(rig.chunks) == 2)
    first, second = rig.replies
    assert first["id"] is None and first["error"]["code"] == INVALID_REQUEST
    assert "65536" in first["error"]["message"]
    assert second["id"] == 1 and second["result"]["echo"] == "ping"
    await rig.finish()


async def test_an_oversized_line_that_arrives_in_pieces_is_drained_and_refused_once() -> None:
    rig = _Rig(limit=65536, max_message_bytes=65536)
    rig.start()
    rig.feed(b"y" * 70_000)
    for _ in range(3):
        await asyncio.sleep(0)
    rig.feed(b"y" * 70_000)
    for _ in range(3):
        await asyncio.sleep(0)
    rig.feed(b"tail\n" + _line(id=2, method="ping"))
    await _until(lambda: len(rig.chunks) == 2)
    first, second = rig.replies
    assert first["id"] is None and first["error"]["code"] == INVALID_REQUEST
    assert second["id"] == 2
    await rig.finish()
    assert len(rig.chunks) == 2


async def test_a_line_over_the_peer_bound_is_refused_even_when_the_reader_allows_it() -> None:
    rig = _Rig(limit=1_000_000, max_message_bytes=1_000)
    rig.start()
    rig.feed(_line(id=1, method="m", params={"pad": "z" * 2_000}) + _line(id=2, method="ping"))
    await _until(lambda: len(rig.chunks) == 2)
    assert rig.replies[0]["error"]["code"] == INVALID_REQUEST
    assert rig.replies[1]["id"] == 2
    await rig.finish()


async def test_eof_without_a_final_newline_still_parses_the_last_line() -> None:
    rig = _Rig()
    rig.start()
    rig.feed(b"{unterminated")
    await asyncio.sleep(0)
    await rig.finish()
    assert [r["error"]["code"] for r in rig.replies] == [PARSE_ERROR]


async def test_eof_in_the_middle_of_an_oversized_line_reports_it_once() -> None:
    rig = _Rig(limit=65536, max_message_bytes=65536)
    rig.start()
    rig.feed(b"w" * 70_000)
    await asyncio.sleep(0)
    await rig.finish()
    assert [r["error"]["code"] for r in rig.replies] == [INVALID_REQUEST]


async def test_an_unterminated_oversized_tail_at_eof_is_refused() -> None:
    rig = _Rig(limit=1_000_000, max_message_bytes=100)
    rig.start()
    rig.feed(b"v" * 500)
    await asyncio.sleep(0)
    await rig.finish()
    assert [r["error"]["code"] for r in rig.replies] == [INVALID_REQUEST]


async def test_request_timeout_raises_timeout_error_and_forgets_the_id(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rig = _Rig()
    rig.start()
    with pytest.raises(TimeoutError):
        await rig.peer.request("slow", {}, timeout=0.01)
    rig.feed(_line(id="test-1", result={"late": True}))
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    await rig.finish()
    assert "unknown id 'test-1'" in capsys.readouterr().err


async def test_the_peer_never_writes_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    rig = _Rig()
    rig.start()
    rig.feed(b"{bad\n" + _line(id=1, method="ping") + _line(method="n"))
    pending = asyncio.create_task(rig.peer.request("ask", {}))
    await _until(lambda: len(rig.chunks) == 3)
    rig.feed(_line(id="test-1", result={}))
    await pending
    await rig.finish()
    assert capsys.readouterr().out == ""
