# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import json
from contextlib import asynccontextmanager
from typing import Any

import pytest

from qwenloop.cli.app import _dispatcher_for
from qwenloop.domain.config import QwenConfig
from qwenloop.domain.model import Backend, ChatMessage, ServerInfo
from qwenloop.infrastructure.turn_dispatch import (
    DirectTurnDispatcher,
    HybridTurnMultiplexer,
    RabbitMqTurnDispatcher,
    RabbitMqTurnWorker,
)


class _StreamingServer:
    async def chat_stream(self, _info: ServerInfo, _messages: object):
        yield type("Chunk", (), {"text": "ok"})()


@pytest.mark.asyncio
async def test_hybrid_dispatch_streams_through_bounded_pool() -> None:
    info = ServerInfo(
        backend=Backend.OPENAI_COMPAT,
        profile="local",
        endpoint="http://model/v1",
        owned=False,
        healthy=True,
        pid=None,
        token="",
        model="gpt-oss:20b",
        argv=(),
        log_path="",
    )
    chunks = [
        chunk
        async for chunk in HybridTurnMultiplexer(concurrency=1).dispatch(
            _StreamingServer(), info, [ChatMessage(role="user", content="hi")]
        )
    ]
    assert chunks[0].text == "ok"


def test_hybrid_dispatch_rejects_non_positive_concurrency() -> None:
    with pytest.raises(ValueError, match="positive"):
        HybridTurnMultiplexer(concurrency=0)


class _Message:
    def __init__(self, body: bytes, correlation_id: str) -> None:
        self.body = body
        self.correlation_id = correlation_id

    @asynccontextmanager
    async def process(self) -> Any:
        yield


class _Replies:
    name = "reply.queue"

    def __init__(self, messages: list[_Message] | None = None) -> None:
        self.messages = messages
        self.index = 0

    async def __aenter__(self) -> "_Replies":
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    def __aiter__(self) -> "_Replies":
        return self

    def iterator(self) -> "_Replies":
        return self

    async def __anext__(self) -> _Message:
        if self.messages is not None:
            if self.index == len(self.messages):
                raise StopAsyncIteration
            message = self.messages[self.index]
            self.index += 1
            return message
        if getattr(self, "sent", False):
            raise StopAsyncIteration
        self.sent = True
        return _Message(
            json.dumps({"chunk": {"text": "reply"}, "done": True}).encode(),
            self.correlation_id,
        )


class _Exchange:
    async def publish(self, message: Any, *, routing_key: str) -> None:
        self.message = message
        self.routing_key = routing_key


class _Channel:
    def __init__(self) -> None:
        self.default_exchange = _Exchange()
        self.replies = _Replies()

    async def declare_queue(self, name: str = "", **_: object) -> Any:
        if name:
            return type("Requests", (), {"name": name})()
        return self.replies


class _Connection:
    def __init__(self) -> None:
        self.channel_instance = _Channel()

    async def channel(self) -> _Channel:
        return self.channel_instance

    async def close(self) -> None:
        return None


@pytest.mark.asyncio
async def test_rabbitmq_dispatch_round_trips_correlated_chunks() -> None:
    connection = _Connection()

    async def connect(_: str) -> _Connection:
        connection.channel_instance.replies.correlation_id = "unused"
        return connection

    dispatcher = RabbitMqTurnDispatcher("amqp://broker", connection_factory=connect)
    info = ServerInfo(
        backend=Backend.OPENAI_COMPAT,
        profile="local",
        endpoint="http://model/v1",
        owned=False,
        healthy=True,
        pid=None,
        token="",
        model="gpt-oss:20b",
        argv=(),
        log_path="",
    )
    # The fake broker copies the request correlation id onto its reply.
    original_publish = connection.channel_instance.default_exchange.publish

    async def publish(message: Any, *, routing_key: str) -> None:
        connection.channel_instance.replies.correlation_id = message.correlation_id
        await original_publish(message, routing_key=routing_key)

    connection.channel_instance.default_exchange.publish = publish
    chunks = await dispatcher.dispatch_all(info, [ChatMessage("user", "hello")])
    assert [chunk.text for chunk in chunks] == ["reply"]


@pytest.mark.asyncio
async def test_direct_dispatcher_delegates_to_local_server() -> None:
    class Server:
        def chat_stream(self, _: ServerInfo, __: list[ChatMessage]) -> Any:
            async def stream() -> Any:
                yield type("Chunk", (), {"text": "local"})()

            return stream()

    info = ServerInfo(
        backend=Backend.OPENAI_COMPAT,
        profile="local",
        endpoint="http://model/v1",
        owned=False,
        healthy=True,
        pid=None,
        token="",
        model="gpt-oss:20b",
        argv=(),
        log_path="",
    )
    chunks = [chunk async for chunk in DirectTurnDispatcher().dispatch(Server(), info, [])]
    assert chunks[0].text == "local"


@pytest.mark.asyncio
async def test_rabbitmq_dispatch_streams_through_dispatch_interface() -> None:
    connection = _Connection()

    async def connect(_: str) -> _Connection:
        return connection

    async def publish(message: Any, *, routing_key: str) -> None:
        connection.channel_instance.replies.correlation_id = message.correlation_id

    connection.channel_instance.default_exchange.publish = publish
    dispatcher = RabbitMqTurnDispatcher("amqp://broker", connection_factory=connect)
    info = ServerInfo(
        backend=Backend.OPENAI_COMPAT,
        profile="local",
        endpoint="http://model/v1",
        owned=False,
        healthy=True,
        pid=None,
        token="",
        model="gpt-oss:20b",
        argv=(),
        log_path="",
    )
    chunks = [
        chunk async for chunk in dispatcher.dispatch(object(), info, [ChatMessage("user", "hello")])
    ]
    assert [chunk.text for chunk in chunks] == ["reply"]


@pytest.mark.asyncio
async def test_rabbitmq_dispatch_ignores_other_correlations_and_waits_for_done() -> None:
    connection = _Connection()

    async def connect(_: str) -> _Connection:
        return connection

    dispatcher = RabbitMqTurnDispatcher("amqp://broker", connection_factory=connect)
    correlation = "expected"
    connection.channel_instance.replies = _Replies(
        [
            _Message(b'{"chunk": {"text": "other"}, "done": true}', "other"),
            _Message(b'{"chunk": {"text": "first"}, "done": false}', correlation),
            _Message(b'{"chunk": {"text": "last"}, "done": true}', correlation),
        ]
    )

    async def publish(message: Any, *, routing_key: str) -> None:
        connection.channel_instance.replies.messages[-2].correlation_id = message.correlation_id
        connection.channel_instance.replies.messages[-1].correlation_id = message.correlation_id

    connection.channel_instance.default_exchange.publish = publish
    info = ServerInfo(
        backend=Backend.OPENAI_COMPAT,
        profile="local",
        endpoint="http://model/v1",
        owned=False,
        healthy=True,
        pid=None,
        token="",
        model="gpt-oss:20b",
        argv=(),
        log_path="",
    )
    chunks = await dispatcher.dispatch_all(info, [ChatMessage("user", "hello")])
    assert [chunk.text for chunk in chunks] == ["first", "last"]


@pytest.mark.asyncio
async def test_rabbitmq_dispatch_surfaces_worker_errors() -> None:
    connection = _Connection()

    async def connect(_: str) -> _Connection:
        return connection

    dispatcher = RabbitMqTurnDispatcher("amqp://broker", connection_factory=connect)
    connection.channel_instance.replies = _Replies([_Message(b'{"error": "failed"}', "unused")])

    async def publish(message: Any, *, routing_key: str) -> None:
        connection.channel_instance.replies.messages[0].correlation_id = message.correlation_id

    connection.channel_instance.default_exchange.publish = publish
    info = ServerInfo(
        backend=Backend.OPENAI_COMPAT,
        profile="local",
        endpoint="http://model/v1",
        owned=False,
        healthy=True,
        pid=None,
        token="",
        model="gpt-oss:20b",
        argv=(),
        log_path="",
    )
    with pytest.raises(RuntimeError, match="failed"):
        await dispatcher.dispatch_all(info, [ChatMessage("user", "hello")])


@pytest.mark.asyncio
async def test_rabbitmq_dispatch_returns_when_reply_stream_closes() -> None:
    connection = _Connection()

    async def connect(_: str) -> _Connection:
        return connection

    dispatcher = RabbitMqTurnDispatcher("amqp://broker", connection_factory=connect)
    connection.channel_instance.replies = _Replies(
        [_Message(b'{"chunk": {"text": "partial"}, "done": false}', "unused")]
    )

    async def publish(message: Any, *, routing_key: str) -> None:
        connection.channel_instance.replies.messages[0].correlation_id = message.correlation_id

    connection.channel_instance.default_exchange.publish = publish
    info = ServerInfo(
        backend=Backend.OPENAI_COMPAT,
        profile="local",
        endpoint="http://model/v1",
        owned=False,
        healthy=True,
        pid=None,
        token="",
        model="gpt-oss:20b",
        argv=(),
        log_path="",
    )
    chunks = await dispatcher.dispatch_all(info, [ChatMessage("user", "hello")])
    assert [chunk.text for chunk in chunks] == ["partial"]


@pytest.mark.asyncio
async def test_rabbitmq_worker_publishes_chunks_and_completion() -> None:
    worker = RabbitMqTurnWorker("amqp://broker")
    channel = _Channel()

    class Server:
        def chat_stream(self, _: ServerInfo, __: list[ChatMessage]) -> Any:
            async def stream() -> Any:
                yield type(
                    "Chunk",
                    (),
                    {
                        "text": "worker",
                        "tool_call": None,
                        "input_tokens": 1,
                        "output_tokens": 2,
                        "timings": None,
                        "finish_reason": "stop",
                    },
                )()

            return stream()

    message = _Message(
        json.dumps(
            {
                "correlation_id": "corr",
                "reply_to": "reply.queue",
                "messages": [{"role": "user", "content": "hello"}],
            }
        ).encode(),
        "corr",
    )
    await worker._handle(
        channel, Server(), ServerInfo(Backend.OPENAI_COMPAT, "local", "url", False, True), message
    )
    assert channel.default_exchange.routing_key == "reply.queue"
    assert b'"done": true' in channel.default_exchange.message.body


@pytest.mark.asyncio
async def test_rabbitmq_worker_reports_model_errors() -> None:
    worker = RabbitMqTurnWorker("amqp://broker")
    channel = _Channel()

    class Server:
        def chat_stream(self, _: ServerInfo, __: list[ChatMessage]) -> Any:
            raise RuntimeError("model unavailable")

    message = _Message(
        b'{"correlation_id":"corr","reply_to":"reply.queue","messages":[]}',
        "corr",
    )
    await worker._handle(
        channel, Server(), ServerInfo(Backend.OPENAI_COMPAT, "local", "url", False, True), message
    )
    assert b"model unavailable" in channel.default_exchange.message.body


@pytest.mark.asyncio
async def test_rabbitmq_worker_serves_until_queue_closes() -> None:
    class EmptyQueue:
        seen = False

        def __aiter__(self) -> "EmptyQueue":
            return self

        async def __anext__(self) -> Any:
            if not self.seen:
                self.seen = True
                return object()
            raise StopAsyncIteration

        def iterator(self) -> "EmptyQueue":
            return self

        async def __aenter__(self) -> "EmptyQueue":
            return self

        async def __aexit__(self, *_: object) -> None:
            return None

    class Channel:
        async def declare_queue(self, *_: object, **__: object) -> EmptyQueue:
            return EmptyQueue()

    class Connection:
        closed = False

        async def channel(self) -> Channel:
            return Channel()

        async def close(self) -> None:
            self.closed = True

    connection = Connection()

    async def connect(_: str) -> Connection:
        return connection

    worker = RabbitMqTurnWorker("amqp://broker", connection_factory=connect)

    async def handle(*_: object) -> None:
        return None

    worker._handle = handle  # type: ignore[method-assign]
    await worker.serve(object(), ServerInfo(Backend.OPENAI_COMPAT, "local", "url", False, True))
    assert connection.closed


def test_dispatcher_composition_preserves_direct_default_and_explicit_rabbitmq() -> None:
    assert isinstance(
        _dispatcher_for(QwenConfig(turn_dispatch_mode="direct")), DirectTurnDispatcher
    )
    assert isinstance(
        _dispatcher_for(QwenConfig(turn_dispatch_mode="rabbitmq", turn_queue_url="amqp://broker")),
        RabbitMqTurnDispatcher,
    )


def test_dispatcher_composition_supports_explicit_hybrid_mode() -> None:
    assert isinstance(
        _dispatcher_for(QwenConfig(turn_dispatch_mode="hybrid")), HybridTurnMultiplexer
    )


def test_dispatcher_composition_auto_uses_measured_winner(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("qwenloop.cli.app.DispatchBenchmark.load", lambda _path: "hybrid")
    assert isinstance(_dispatcher_for(QwenConfig(turn_dispatch_mode="auto")), HybridTurnMultiplexer)


def test_dispatcher_composition_auto_falls_back_to_direct(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("qwenloop.cli.app.DispatchBenchmark.load", lambda _path: None)
    assert isinstance(_dispatcher_for(QwenConfig(turn_dispatch_mode="auto")), DirectTurnDispatcher)
