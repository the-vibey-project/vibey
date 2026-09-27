# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Direct, hybrid, and RabbitMQ-backed model-turn dispatchers."""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncIterator, Sequence
from typing import Any

import aio_pika

from qwenloop.application.interfaces import InferenceServer
from qwenloop.domain.interfaces import ChatChunkInterface
from qwenloop.domain.model import ChatChunk, ChatMessage, ServerInfo


class DirectTurnDispatcher:
    """The existing one-run-at-a-time behavior, kept as the safe default."""

    def dispatch(
        self,
        server: InferenceServer,
        info: ServerInfo,
        messages: Sequence[ChatMessage],
    ) -> AsyncIterator[ChatChunkInterface]:
        return server.chat_stream(info, messages)


class HybridTurnMultiplexer:
    """Multiplexes several lane turns through one resident server in-process.

    The semaphore is shared by dispatchers for the same endpoint/model, so independently
    constructed lane runners still share the configured model capacity. It is deliberately
    local: RabbitMQ remains the explicit cross-process mode.
    """

    _pools: dict[tuple[str, str], asyncio.Semaphore] = {}

    def __init__(self, *, concurrency: int = 2) -> None:
        if concurrency <= 0:
            raise ValueError("hybrid concurrency must be positive")
        self._concurrency = concurrency

    def dispatch(
        self,
        server: InferenceServer,
        info: ServerInfo,
        messages: Sequence[ChatMessage],
    ) -> AsyncIterator[ChatChunkInterface]:
        return self._dispatch(server, info, messages)

    async def _dispatch(
        self,
        server: InferenceServer,
        info: ServerInfo,
        messages: Sequence[ChatMessage],
    ) -> AsyncIterator[ChatChunkInterface]:
        key = (info.endpoint, info.model)
        pool = self._pools.setdefault(key, asyncio.Semaphore(self._concurrency))
        async with pool:
            async for chunk in server.chat_stream(info, messages):
                yield chunk


class RabbitMqTurnDispatcher:
    """Request/reply dispatcher for a shared model service.

    Each request gets a correlation id and a private reply queue. The broker worker owns
    the model slot; lane processes only publish turns and consume their own ordered reply.
    """

    def __init__(
        self,
        url: str,
        *,
        request_queue: str = "vibey.llm.turns",
        connection_factory: Any = aio_pika.connect_robust,
    ) -> None:
        self._url = url
        self._request_queue = request_queue
        self._connection_factory = connection_factory

    async def dispatch_all(
        self,
        info: ServerInfo,
        messages: Sequence[ChatMessage],
    ) -> list[ChatChunkInterface]:
        connection = await self._connection_factory(self._url)
        try:
            channel = await connection.channel()
            requests = await channel.declare_queue(self._request_queue, durable=True)
            replies = await channel.declare_queue(exclusive=True, auto_delete=True)
            correlation_id = str(uuid.uuid4())
            payload = {
                "correlation_id": correlation_id,
                "reply_to": replies.name,
                "server": {"endpoint": info.endpoint, "model": info.model, "token": info.token},
                "messages": [self._message(item) for item in messages],
            }
            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(payload).encode(),
                    correlation_id=correlation_id,
                    reply_to=replies.name,
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                ),
                routing_key=requests.name,
            )
            chunks: list[ChatChunkInterface] = []
            async with replies.iterator() as iterator:
                async for message in iterator:
                    if message.correlation_id != correlation_id:
                        continue
                    async with message.process():
                        body = json.loads(message.body)
                        if body.get("error"):
                            raise RuntimeError(str(body["error"]))
                        chunks.append(ChatChunk(**body["chunk"]))
                        if body.get("done"):
                            break
            return chunks
        finally:
            await connection.close()

    async def dispatch(
        self,
        server: InferenceServer,
        info: ServerInfo,
        messages: Sequence[ChatMessage],
    ) -> AsyncIterator[ChatChunkInterface]:
        del server  # The shared service owns the inference server.
        for chunk in await self.dispatch_all(info, messages):
            yield chunk

    @staticmethod
    def _message(message: ChatMessage) -> dict[str, object]:
        return {
            "role": message.role,
            "content": message.content,
            "tool_calls": list(message.tool_calls),
            "tool_call_id": message.tool_call_id,
        }


class RabbitMqTurnWorker:
    """Hosts one inference server behind a durable, multi-lane turn queue."""

    def __init__(
        self,
        url: str,
        *,
        request_queue: str = "vibey.llm.turns",
        connection_factory: Any = aio_pika.connect_robust,
    ) -> None:
        self._url = url
        self._request_queue = request_queue
        self._connection_factory = connection_factory

    async def serve(self, server: InferenceServer, info: ServerInfo) -> None:
        connection = await self._connection_factory(self._url)
        try:
            channel = await connection.channel()
            queue = await channel.declare_queue(self._request_queue, durable=True)
            async with queue.iterator() as messages:
                async for message in messages:
                    await self._handle(channel, server, info, message)
        finally:
            await connection.close()

    async def _handle(
        self, channel: Any, server: InferenceServer, info: ServerInfo, message: Any
    ) -> None:
        async with message.process():
            request = json.loads(message.body)
            reply_to = str(request["reply_to"])
            correlation_id = str(request["correlation_id"])
            try:
                stream = server.chat_stream(
                    info,
                    [
                        ChatMessage(
                            role=item["role"],
                            content=item.get("content", ""),
                            tool_calls=tuple(item.get("tool_calls", ())),
                            tool_call_id=item.get("tool_call_id"),
                        )
                        for item in request["messages"]
                    ],
                )
                async for chunk in stream:
                    await self._publish(
                        channel,
                        reply_to,
                        correlation_id,
                        {"chunk": self._chunk(chunk), "done": False},
                    )
                await self._publish(channel, reply_to, correlation_id, {"done": True})
            except Exception as exc:
                await self._publish(channel, reply_to, correlation_id, {"error": str(exc)})

    @staticmethod
    async def _publish(
        channel: Any, reply_to: str, correlation_id: str, body: dict[str, object]
    ) -> None:
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(body).encode(),
                correlation_id=correlation_id,
            ),
            routing_key=reply_to,
        )

    @staticmethod
    def _chunk(chunk: ChatChunkInterface) -> dict[str, object]:
        return {
            "text": chunk.text,
            "tool_call": chunk.tool_call,
            "input_tokens": chunk.input_tokens,
            "output_tokens": chunk.output_tokens,
            "timings": chunk.timings,
            "finish_reason": chunk.finish_reason,
        }
