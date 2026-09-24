# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The RabbitMQ inspector over a faked management API (ADR-0056).

CI runs no broker (ADR-0056 says so), so these pin exactly what vibey sends to and reads
from the management API. What the broker itself does with a policy -- that
`consumer-timeout` closes a hung channel and requeues, that `delivery-limit` dead-letters
on a quorum queue -- is upstream behaviour, owed as verification against the pinned image.
"""

from __future__ import annotations

import base64
import json
import urllib.error
from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock

import pytest

from vibey.application.interfaces import BusInspectorPort
from vibey.domain.queue_reap import BrokerPolicy
from vibey.infrastructure.bus.interfaces import (
    RabbitMqApiErrorInterface,
    RabbitMqBusInspectorInterface,
    RabbitMqManagementApiInterface,
)
from vibey.infrastructure.bus.management import RabbitMqApiError, RabbitMqManagementApi
from vibey.infrastructure.bus.rabbitmq_inspector import PEEK_TRUNCATE_BYTES, RabbitMqBusInspector

POLICY = BrokerPolicy(
    name="vibey-reap", pattern=r"^vibey\.", consumer_timeout_ms=21_600_000, delivery_limit=20
)


def _response(payload: object) -> MagicMock:
    resp = MagicMock()
    raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
    resp.__enter__.return_value.read.return_value = raw
    return resp


def _http_error(status: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("http://bus", status, "nope", {}, None)  # type: ignore[arg-type]


class Broker:
    """A fake management API: a route table, and every request it was sent."""

    def __init__(self, routes: dict[tuple[str, str], Callable[[Any], object]]) -> None:
        self.routes = routes
        self.sent: list[tuple[str, str, object]] = []

    def __call__(self, req: Any) -> MagicMock:
        path = req.full_url.split("/api/", 1)[1]
        body = json.loads(req.data.decode()) if req.data else None
        self.sent.append((req.get_method(), path, body))
        answer = self.routes[(req.get_method(), path)](body)
        if isinstance(answer, BaseException):
            raise answer
        return _response(answer)


def _inspector(broker: Broker, *, now: float = 1_000.0, vhost: str = "/") -> RabbitMqBusInspector:
    return RabbitMqBusInspector(
        url="http://bus:15672/",
        username="u",
        password="p",
        vhost=vhost,
        opener=broker,
        epoch_seconds=lambda: now,
    )


def test_the_inspector_and_the_client_satisfy_their_seams() -> None:
    inspector = _inspector(Broker({}))
    assert isinstance(inspector, RabbitMqBusInspectorInterface)
    assert isinstance(inspector, BusInspectorPort)
    api = RabbitMqManagementApi(url="http://bus", username="u", password="p", vhost="a b")
    assert isinstance(api, RabbitMqManagementApiInterface)
    assert api.vhost == "a%20b"
    assert api.name("vibey.jobs/x") == "vibey.jobs%2Fx"
    assert isinstance(RabbitMqApiError(404, "gone"), RabbitMqApiErrorInterface)


def test_an_http_error_carries_its_status() -> None:
    api = RabbitMqManagementApi(
        url="http://bus", username="u", password="p", opener=MagicMock(side_effect=_http_error(403))
    )
    with pytest.raises(RabbitMqApiError, match="RabbitMQ API error 403") as caught:
        api.request("GET", "overview")
    assert caught.value.status == 403


async def test_depths_measure_every_queue_and_the_age_of_its_head() -> None:
    rows = [
        {
            "name": "vibey.jobs.p",
            "messages_ready": 3,
            "messages_unacknowledged": 1,
            "consumers": 2,
            "head_message_timestamp": 400,
        },
        {"name": "celery", "messages_ready": 1, "consumers": 0, "head_message_timestamp": None},
        {"name": "fresh"},
        {"name": "future", "messages_ready": 1, "head_message_timestamp": 2_000.5},
    ]
    broker = Broker(
        {
            (
                "GET",
                "queues/%2F?columns=name,messages_ready,messages_unacknowledged,consumers,"
                "head_message_timestamp",
            ): lambda _: rows
        }
    )
    depths = await _inspector(broker).depths()
    assert [
        (d.queue, d.ready, d.unacked, d.consumers, d.oldest_ready_age_seconds) for d in depths
    ] == [
        ("vibey.jobs.p", 3, 1, 2, 600.0),
        ("celery", 1, 0, 0, None),
        ("fresh", 0, 0, 0, None),
        ("future", 1, 0, 0, 0.0),
    ]
    assert all(not d.owned and not d.dead_letter for d in depths)


async def test_depths_of_an_empty_vhost_are_empty() -> None:
    broker = Broker(
        {
            (
                "GET",
                "queues/vibey?columns=name,messages_ready,messages_unacknowledged,consumers,"
                "head_message_timestamp",
            ): lambda _: None
        }
    )
    assert await _inspector(broker, vhost="vibey").depths() == ()


async def test_a_peek_reads_the_head_and_returns_every_message_to_its_place() -> None:
    encoded = base64.b64encode(b'{"b": 2}').decode()
    messages = [
        {
            "payload": '{"a": 1}',
            "payload_encoding": "string",
            "payload_bytes": 8,
            "properties": {
                "message_id": "m1",
                "headers": {
                    "x-first-death-queue": "vibey.jobs",
                    "x-first-death-reason": "rejected",
                    "x-death": [
                        {"queue": "vibey.jobs", "reason": "expired", "time": 20},
                        {"queue": "vibey.jobs", "reason": "rejected", "time": 10},
                    ],
                },
            },
        },
        {
            "payload": encoded,
            "payload_encoding": "base64",
            "payload_bytes": 8,
            "properties": {"headers": {"x-death": [{"queue": "vibey.other", "reason": "maxlen"}]}},
        },
        {"payload": '{"c"', "payload_bytes": 99_999, "properties": {}},
    ]
    broker = Broker(
        {
            ("GET", "queues/%2F/vibey.jobs.dlq"): lambda _: {"messages": 5},
            ("POST", "queues/%2F/vibey.jobs.dlq/get"): lambda _: messages,
        }
    )
    peek = await _inspector(broker).peek_dead_letters("vibey.jobs.dlq", limit=3)
    assert broker.sent[-1] == (
        "POST",
        "queues/%2F/vibey.jobs.dlq/get",
        {
            "count": 3,
            "ackmode": "ack_requeue_true",
            "encoding": "auto",
            "truncate": PEEK_TRUNCATE_BYTES,
        },
    )
    assert (peek.depth, peek.complete) == (5, False)
    first, second, third = peek.items
    assert (first.origin_queue, first.reason, first.message_id, first.first_death_at) == (
        "vibey.jobs",
        "rejected",
        "m1",
        "10",
    )
    assert first.payload_object() == {"a": 1} and not first.truncated
    assert (second.origin_queue, second.reason, second.body) == (
        "vibey.other",
        "maxlen",
        '{"b": 2}',
    )
    assert second.message_id is None and second.first_death_at is None
    assert (third.origin_queue, third.reason, third.truncated) == ("vibey.jobs", "unknown", True)
    assert third.payload_object() is None


async def test_a_peek_of_an_empty_queue_takes_nothing() -> None:
    broker = Broker({("GET", "queues/%2F/x.dead"): lambda _: None})
    peek = await _inspector(broker).peek_dead_letters("x.dead", limit=10)
    assert (peek.depth, peek.items, peek.complete) == (0, (), True)
    assert [method for method, _, _ in broker.sent] == ["GET"]


async def test_a_peek_trusts_what_it_read_over_a_stale_count() -> None:
    broker = Broker(
        {
            ("GET", "queues/%2F/q.dead"): lambda _: {"messages": 1},
            ("POST", "queues/%2F/q.dead/get"): lambda _: [
                {"payload": "{}", "properties": {}},
                {"payload": "{}", "properties": {}},
            ],
        }
    )
    peek = await _inspector(broker).peek_dead_letters("q.dead", limit=10)
    assert peek.depth == 2 and peek.complete
    assert peek.items[0].origin_queue == "q"


async def test_a_policy_already_in_force_is_not_written_again() -> None:
    broker = Broker({("GET", "policies/%2F/vibey-reap"): lambda _: POLICY.body()})
    outcome = await _inspector(broker).apply_policy(POLICY)
    assert outcome.verified and outcome.detail == "already in force"
    assert [method for method, _, _ in broker.sent] == ["GET"]


async def test_a_missing_policy_is_written_and_read_back() -> None:
    reads = iter([_http_error(404), POLICY.body()])
    broker = Broker(
        {
            ("GET", "policies/%2F/vibey-reap"): lambda _: next(reads),
            ("PUT", "policies/%2F/vibey-reap"): lambda body: None,
        }
    )
    outcome = await _inspector(broker).apply_policy(POLICY)
    assert outcome.verified and outcome.detail == "written and read back"
    assert broker.sent[1] == ("PUT", "policies/%2F/vibey-reap", POLICY.body())


async def test_a_policy_that_reads_back_wrong_is_not_verified() -> None:
    drifted = {**POLICY.body(), "priority": 9}
    broker = Broker(
        {
            ("GET", "policies/%2F/vibey-reap"): lambda _: drifted,
            ("PUT", "policies/%2F/vibey-reap"): lambda body: None,
        }
    )
    outcome = await _inspector(broker).apply_policy(POLICY)
    assert not outcome.verified
    assert outcome.detail.startswith("written, but read back as")


async def test_a_refused_policy_write_is_reported_not_raised() -> None:
    broker = Broker(
        {
            ("GET", "policies/%2F/vibey-reap"): lambda _: _http_error(404),
            ("PUT", "policies/%2F/vibey-reap"): lambda body: _http_error(401),
        }
    )
    outcome = await _inspector(broker).apply_policy(POLICY)
    assert not outcome.verified
    assert "the broker refused it: RabbitMQ API error 401" in outcome.detail


async def test_an_unreadable_policy_raises_for_the_reaper_to_name() -> None:
    broker = Broker({("GET", "policies/%2F/vibey-reap"): lambda _: _http_error(500)})
    with pytest.raises(RabbitMqApiError, match="500"):
        await _inspector(broker).apply_policy(POLICY)
