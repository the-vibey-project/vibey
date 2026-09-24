# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""RabbitMQ Bus adapter implementing the service-bus port (ADR-0042).

Self-hosted RabbitMQ over its management HTTP API with stdlib urllib only --
no AMQP client dependency. Queues are durable; with `dead_letter` (the
default) each queue gets a fanout dead-letter exchange and a bound
`<queue>.dlq`, so rejected and expired messages park for inspection instead
of vanishing. Consuming uses basic.get semantics: one acknowledged message
per call, None when the queue is empty. That is at-most-once: no delivery is
ever held, so none can hang, be orphaned or be redelivered -- and a consumer
that dies after `consume` returns has lost the message (ADR-0056 records this).

Every publish carries a `message_id` and a `timestamp` (ADR-0056): the id makes a
dead letter's identity its own, so parking it is idempotent, and the timestamp
lets the reaper measure how long the oldest ready message has waited.
"""

from __future__ import annotations

import asyncio
import base64
import json
import time
import urllib.request
import uuid
from collections.abc import Callable
from typing import Any

from vibey.application.interfaces.bus import BusPort
from vibey.infrastructure.bus.management import RabbitMqManagementApi


class RabbitMqBusAdapter(BusPort):
    def __init__(
        self,
        *,
        url: str,
        username: str,
        password: str,
        vhost: str = "/",
        opener: Any = urllib.request.urlopen,
        message_ids: Callable[[], uuid.UUID] = uuid.uuid4,
        epoch_seconds: Callable[[], float] = time.time,
    ) -> None:
        self._api = RabbitMqManagementApi(
            url=url, username=username, password=password, vhost=vhost, opener=opener
        )
        self._vhost = self._api.vhost
        self._message_ids = message_ids
        self._epoch_seconds = epoch_seconds

    def _request(self, method: str, path: str, payload: dict[str, object] | None = None) -> Any:
        return self._api.request(method, path, payload)

    async def declare_queue(self, queue: str, *, dead_letter: bool = True) -> None:
        await asyncio.to_thread(self._declare_sync, queue, dead_letter)

    def _declare_sync(self, queue: str, dead_letter: bool) -> None:
        arguments: dict[str, object] = {}
        if dead_letter:
            exchange = f"{queue}.dlx"
            dlq = f"{queue}.dlq"
            self._request(
                "PUT", f"exchanges/{self._vhost}/{exchange}", {"type": "fanout", "durable": True}
            )
            self._request("PUT", f"queues/{self._vhost}/{dlq}", {"durable": True})
            self._request(
                "POST",
                f"bindings/{self._vhost}/e/{exchange}/q/{dlq}",
                {"routing_key": queue},
            )
            arguments["x-dead-letter-exchange"] = exchange
        self._request(
            "PUT", f"queues/{self._vhost}/{queue}", {"durable": True, "arguments": arguments}
        )

    async def publish(self, queue: str, payload: dict[str, object]) -> None:
        await asyncio.to_thread(self._publish_sync, queue, payload)

    def _publish_sync(self, queue: str, payload: dict[str, object]) -> None:
        self._declare_sync(queue, True)
        result = self._request(
            "POST",
            f"exchanges/{self._vhost}//publish",
            {
                "routing_key": queue,
                "payload": json.dumps(payload),
                "payload_encoding": "string",
                "properties": {
                    "delivery_mode": 2,
                    "message_id": self._message_ids().hex,
                    "timestamp": int(self._epoch_seconds()),
                },
            },
        )
        if not isinstance(result, dict) or not result.get("routed"):
            raise RuntimeError(f"RabbitMQ did not route the payload to {queue!r}")

    async def consume(self, queue: str) -> dict[str, object] | None:
        return await asyncio.to_thread(self._consume_sync, queue)

    def _consume_sync(self, queue: str) -> dict[str, object] | None:
        result = self._request(
            "POST",
            f"queues/{self._vhost}/{queue}/get",
            {"count": 1, "ackmode": "ack_requeue_false", "encoding": "auto"},
        )
        if not result:
            return None
        message = result[0]
        body = message.get("payload", "")
        if message.get("payload_encoding") == "base64":
            body = base64.b64decode(body).decode("utf-8")
        value = json.loads(body)
        if not isinstance(value, dict):
            raise RuntimeError(f"expected a JSON object on {queue!r}")
        return value
