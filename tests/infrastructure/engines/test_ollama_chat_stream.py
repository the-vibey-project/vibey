# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Streaming the local model's reply, so an operator can watch it arrive (the wire log)."""

import json
import time
import urllib.request
from collections.abc import AsyncGenerator, Mapping
from pathlib import Path
from typing import Any

import pytest

from vibey.infrastructure.engines.interfaces.ollama_chat_interface import (
    OllamaStreamTransportInterface,
)
from vibey.infrastructure.engines.ollama_chat import OllamaChatClient, UrllibOllamaTransport
from vibey.infrastructure.engines.wire_log import WIRE_LOG_ENV

Line = dict[str, object]


class RecordingWireLog:
    def __init__(self) -> None:
        self.events: list[tuple[Any, ...]] = []

    def request(self, call: str, attempt: int, url: str, payload: Mapping[str, object]) -> None:
        self.events.append(("request", call, attempt, dict(payload)))

    def chunk(self, call: str, attempt: int, *, content: str, thinking: str) -> None:
        self.events.append(("chunk", call, attempt, content, thinking))

    def response(
        self, call: str, attempt: int, body: Mapping[str, object], elapsed_seconds: float
    ) -> None:
        assert elapsed_seconds >= 0
        self.events.append(("response", call, attempt, dict(body)))

    def error(self, call: str, attempt: int, error: BaseException, elapsed_seconds: float) -> None:
        self.events.append(("error", call, attempt, type(error).__name__, str(error)))

    def kinds(self) -> list[str]:
        return [str(event[0]) for event in self.events]


class FakeStream:
    """Plays one scripted run of lines per request."""

    def __init__(self, *runs: list[Line]) -> None:
        self.runs = list(runs)
        self.calls: list[tuple[str, dict[str, object], int]] = []

    async def stream_json(
        self, url: str, payload: Mapping[str, object], *, timeout: int
    ) -> AsyncGenerator[Line, None]:
        self.calls.append((url, dict(payload), timeout))
        for line in self.runs.pop(0):
            yield line


class ForbiddenTransport:
    async def post_json(self, *args: object, **kwargs: object) -> dict[str, object]:
        raise AssertionError("a streamed run must not make a blocking request")


def _done(**fields: object) -> Line:
    return {"message": {"role": "assistant", "content": ""}, "done": True, **fields}


def _client(stream: FakeStream, log: RecordingWireLog) -> OllamaChatClient:
    return OllamaChatClient(transport=ForbiddenTransport(), stream_transport=stream, wire_log=log)


async def test_a_streamed_reply_is_put_back_together_and_every_step_is_logged() -> None:
    stream = FakeStream(
        [
            {"message": {"content": "", "thinking": "hm "}, "done": False},
            {"message": {"content": '{"a": '}},
            {"message": {"content": "1}"}},
            _done(done_reason="stop", eval_count=5, prompt_eval_count=9),
        ]
    )
    log = RecordingWireLog()

    answer = await _client(stream, log).ask("sys", "user", "json")

    assert answer == {"a": 1}
    assert stream.calls[0][1]["stream"] is True
    assert log.kinds() == ["request", "chunk", "chunk", "chunk", "response"]
    assert log.events[1][3:] == ("", "hm ")
    assert log.events[2][3:] == ('{"a": ', "")
    call_ids = {event[1] for event in log.events}
    assert len(call_ids) == 1
    body = log.events[-1][3]
    assert body["eval_count"] == 5
    assert body["message"] == {"role": "assistant", "content": '{"a": 1}', "thinking": "hm "}


async def test_a_run_nobody_is_watching_keeps_its_one_blocking_request() -> None:
    class Blocking:
        def __init__(self) -> None:
            self.payloads: list[dict[str, object]] = []

        async def post_json(
            self, url: str, payload: Mapping[str, object], *, timeout: int
        ) -> dict[str, object]:
            self.payloads.append(dict(payload))
            return {"message": {"content": '{"ok": true}'}}

    class NeverStreams:
        def stream_json(self, *args: object, **kwargs: object) -> None:
            raise AssertionError("no wire log, no streaming")

    blocking = Blocking()
    client = OllamaChatClient(transport=blocking, stream_transport=NeverStreams())  # type: ignore[arg-type]
    assert await client.ask("s", "u", "json") == {"ok": True}
    assert blocking.payloads[0]["stream"] is False


async def test_an_error_line_in_the_stream_fails_the_call_and_is_logged() -> None:
    stream = FakeStream([{"message": {"content": "par"}}, {"error": "model crashed"}])
    log = RecordingWireLog()

    with pytest.raises(ValueError, match="Ollama stream error: model crashed"):
        await _client(stream, log).ask("s", "u", "json")

    assert log.kinds() == ["request", "chunk", "error"]
    assert log.events[-1][3:] == ("ValueError", "Ollama stream error: model crashed")


async def test_a_stream_that_ends_before_done_is_a_failure_not_a_short_answer() -> None:
    log = RecordingWireLog()
    with pytest.raises(ValueError, match="ended before the answer was complete"):
        await _client(FakeStream([{"message": {"content": '{"a": 1}'}}]), log).ask("s", "u", "json")
    assert log.kinds()[-1] == "error"


async def test_odd_lines_add_nothing_and_an_empty_stream_takes_the_json_retry() -> None:
    odd = [{"message": "flat"}, {"message": {"content": 7, "thinking": None}}, _done()]
    log = RecordingWireLog()

    with pytest.raises(ValueError, match="empty message content"):
        await _client(FakeStream(odd, odd), log).ask("s", "u", {"type": "object"})

    assert log.kinds() == ["request", "response", "request", "response"]
    assert {event[2] for event in log.events} == {1, 2}
    assert len({event[1] for event in log.events}) == 1
    assert log.events[2][3]["format"] == "json"


async def test_the_budget_retry_is_a_second_attempt_of_the_same_call() -> None:
    cut_short = [
        {"message": {"content": "", "thinking": "reasoning " * 3}},
        _done(done_reason="length", prompt_eval_count=100),
    ]
    answered = [{"message": {"content": '{"ok": true}'}}, _done(done_reason="stop")]
    stream = FakeStream(cut_short, answered)
    log = RecordingWireLog()

    assert await _client(stream, log).ask("s", "u", "json") == {"ok": True}

    requests = [event for event in log.events if event[0] == "request"]
    assert [event[2] for event in requests] == [1, 2]
    assert len({event[1] for event in requests}) == 1
    assert requests[1][3]["think"] == "low"
    assert requests[1][3]["stream"] is True


async def test_the_environment_turns_streaming_on_with_a_wire_log_path(tmp_path: Path) -> None:
    path = tmp_path / "logs" / "wire.jsonl"
    stream = FakeStream([{"message": {"content": '{"a": 1}'}}, _done()])
    client = OllamaChatClient.from_environment({WIRE_LOG_ENV: str(path)}, stream_transport=stream)

    assert await client.ask("s", "u", "json") == {"a": 1}

    kinds = [json.loads(line)["kind"] for line in path.read_text().splitlines()]
    assert kinds[0] == "request" and kinds[-1] == "response"
    assert stream.calls[0][1]["stream"] is True


@pytest.mark.parametrize("declared", [{}, {WIRE_LOG_ENV: ""}, {WIRE_LOG_ENV: "   "}])
async def test_without_a_wire_log_path_the_environment_changes_nothing(
    declared: dict[str, str],
) -> None:
    class Blocking:
        async def post_json(
            self, url: str, payload: Mapping[str, object], *, timeout: int
        ) -> dict[str, object]:
            assert payload["stream"] is False
            return {"message": {"content": '{"a": 1}'}}

    client = OllamaChatClient.from_environment(declared, transport=Blocking())
    assert await client.ask("s", "u", "json") == {"a": 1}


async def test_a_given_wire_log_beats_the_environment(tmp_path: Path) -> None:
    log = RecordingWireLog()
    stream = FakeStream([{"message": {"content": '{"a": 1}'}}, _done()])
    client = OllamaChatClient.from_environment(
        {WIRE_LOG_ENV: str(tmp_path / "ignored.jsonl")}, stream_transport=stream, wire_log=log
    )
    await client.ask("s", "u", "json")
    assert log.kinds()[0] == "request"
    assert not (tmp_path / "ignored.jsonl").exists()


class _Response:
    def __init__(self, lines: Any) -> None:
        self._lines = lines

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *exc: object) -> bool:
        return False

    def __iter__(self) -> Any:
        return iter(self._lines)


async def test_the_real_transport_yields_each_line_as_it_arrives() -> None:
    seen: list[tuple[urllib.request.Request, int]] = []

    def opener(request: urllib.request.Request, timeout: int) -> _Response:
        seen.append((request, timeout))
        return _Response([b'{"n": 1}\n', b"\n", b'  {"n": 2}  \n'])

    transport: OllamaStreamTransportInterface = UrllibOllamaTransport(opener=opener)
    lines = [line async for line in transport.stream_json("http://h/api/chat", {"q": 1}, timeout=7)]

    assert lines == [{"n": 1}, {"n": 2}]
    ((request, timeout),) = seen
    assert timeout == 7
    assert json.loads(request.data) == {"q": 1}  # type: ignore[arg-type]


async def test_the_real_transport_refuses_what_is_not_http() -> None:
    transport = UrllibOllamaTransport(opener=lambda *a, **k: _Response([]))
    with pytest.raises(ValueError, match="non-HTTP"):
        _ = [line async for line in transport.stream_json("file:///etc/passwd", {}, timeout=1)]


async def test_the_real_transport_refuses_a_line_that_is_not_an_object() -> None:
    transport = UrllibOllamaTransport(opener=lambda *a, **k: _Response([b"[1]\n"]))
    with pytest.raises(ValueError, match="non-object line"):
        _ = [line async for line in transport.stream_json("http://h/x", {}, timeout=1)]


async def test_a_failure_to_connect_reaches_the_caller_not_the_thread() -> None:
    def opener(*args: object, **kwargs: object) -> _Response:
        raise ConnectionRefusedError("nothing listens")

    transport = UrllibOllamaTransport(opener=opener)
    with pytest.raises(ConnectionRefusedError, match="nothing listens"):
        _ = [line async for line in transport.stream_json("http://h/x", {}, timeout=1)]


async def test_closing_early_stops_the_reader_thread_without_hanging() -> None:
    def slow() -> Any:
        yield b'{"n": 1}\n'
        time.sleep(0.3)
        yield b'{"n": 2}\n'
        yield b'{"n": 3}\n'

    transport = UrllibOllamaTransport(opener=lambda *a, **k: _Response(slow()))
    stream = transport.stream_json("http://h/x", {}, timeout=1)
    assert await stream.__anext__() == {"n": 1}
    await stream.aclose()
