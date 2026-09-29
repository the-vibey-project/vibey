# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The #1108 review's broker probes, against a real RabbitMQ (ADR-0056).

The `probe_*.py` scripts of the post-merge review, as regression tests. They run where a
broker is: CI's `gates` job starts the pinned image as a service and sets
`VIBEY_TEST_RABBITMQ_URL`; elsewhere they skip, saying so. Each test works in a vhost of
its own, created and deleted around it, so parallel workers never share a policy or a
queue, and nothing is left on the broker.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass

import pytest
import pytest_asyncio

from vibey.domain.config import QueueReapConfig
from vibey.infrastructure.bus.dispatch import BusDispatchBenchmark
from vibey.infrastructure.bus.management import RabbitMqApiError, RabbitMqManagementApi
from vibey.infrastructure.bus.rabbitmq import RabbitMqBusAdapter
from vibey.infrastructure.bus.rabbitmq_inspector import RabbitMqBusInspector

URL = os.environ.get("VIBEY_TEST_RABBITMQ_URL", "")
USER = os.environ.get("VIBEY_TEST_RABBITMQ_USER", "vibey")
PASSWORD = os.environ.get("VIBEY_TEST_RABBITMQ_PASSWORD", "vibey")

pytestmark = pytest.mark.skipif(
    not URL, reason="no broker: set VIBEY_TEST_RABBITMQ_URL (CI's gates job does)"
)

POLICY = QueueReapConfig().broker_policy()


@dataclass
class Broker:
    vhost: str
    api: RabbitMqManagementApi
    bus: RabbitMqBusAdapter
    inspector: RabbitMqBusInspector

    def queue(self, name: str) -> dict[str, object]:
        info = self.api.request("GET", f"queues/{self.api.vhost}/{self.api.name(name)}")
        assert isinstance(info, dict)
        return info

    def settled(self, name: str, key: str, want: object, seconds: float = 20.0) -> object:
        """A queue's `key` once the management statistics catch up, or what it last was."""
        value: object = None
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            value = self.queue(name).get(key)
            if value == want:
                return value
            time.sleep(1.0)
        return value


@pytest_asyncio.fixture
async def broker() -> AsyncIterator[Broker]:
    vhost = f"vibey-test-{uuid.uuid4().hex[:12]}"
    root = RabbitMqManagementApi(url=URL, username=USER, password=PASSWORD)
    root.request("PUT", f"vhosts/{root.name(vhost)}", {})
    root.request(
        "PUT",
        f"permissions/{root.name(vhost)}/{root.name(USER)}",
        {"configure": ".*", "write": ".*", "read": ".*"},
    )
    kw = {"url": URL, "username": USER, "password": PASSWORD, "vhost": vhost}
    try:
        yield Broker(
            vhost=vhost,
            api=RabbitMqManagementApi(**kw),
            bus=RabbitMqBusAdapter(**kw),
            inspector=RabbitMqBusInspector(**kw, settle_seconds=20.0),
        )
    finally:
        root.request("DELETE", f"vhosts/{root.name(vhost)}")


def _declare(broker: Broker, name: str, *, quorum: bool = False, **arguments: object) -> None:
    if quorum:
        arguments["x-queue-type"] = "quorum"
    broker.api.request(
        "PUT",
        f"queues/{broker.api.vhost}/{broker.api.name(name)}",
        {"durable": True, "arguments": arguments},
    )


def _publish(broker: Broker, queue: str, body: str, **properties: object) -> None:
    routed = broker.api.request(
        "POST",
        f"exchanges/{broker.api.vhost}//publish",
        {
            "routing_key": queue,
            "payload": body,
            "payload_encoding": "string",
            "properties": {"delivery_mode": 2, **properties},
        },
    )
    assert isinstance(routed, dict) and routed.get("routed"), routed


async def test_finding_2_both_queue_types_carry_their_policy(broker: Broker) -> None:
    """probe_policy.py: one policy holding `delivery-limit` left classic queues with no
    policy at all, and was reported verified. Two policies, and verified means the queues
    carry them."""
    _declare(broker, "vibey.cq")
    _declare(broker, "vibey.qq", quorum=True)
    outcome = await broker.inspector.apply_policy(POLICY)
    assert outcome.verified, outcome.detail
    assert broker.settled("vibey.cq", "policy", "vibey-reap-classic") == "vibey-reap-classic"
    assert broker.queue("vibey.cq")["effective_policy_definition"] == {
        "consumer-timeout": 21_600_000
    }
    assert broker.settled("vibey.qq", "policy", "vibey-reap") == "vibey-reap"
    assert broker.queue("vibey.qq")["effective_policy_definition"] == {
        "consumer-timeout": 21_600_000,
        "delivery-limit": 20,
    }
    again = await broker.inspector.apply_policy(POLICY)
    assert again.verified and again.detail == "in force on every owned queue"


async def test_finding_2_a_single_mixed_policy_is_caught_as_not_in_force(broker: Broker) -> None:
    """The old shape -- `apply-to: queues` with both keys -- is exactly what the queue check
    must refuse to call verified."""
    _declare(broker, "vibey.cq")
    quorum, classic = POLICY.documents()
    broker.api.request(
        "PUT",
        f"policies/{broker.api.vhost}/vibey-reap",
        {**quorum.body(), "apply-to": "queues"},
    )
    broker.api.request("PUT", f"policies/{broker.api.vhost}/vibey-reap-classic", classic.body())
    broker.api.request("DELETE", f"policies/{broker.api.vhost}/vibey-reap-classic")
    time.sleep(6)
    assert broker.queue("vibey.cq").get("policy") is None
    outcome = await broker.inspector.apply_policy(POLICY)
    assert outcome.verified, "the reconcile rewrites both policies and they attach"


async def test_finding_11_replay_into_a_quorum_queue_publishes_and_leaves_nothing(
    broker: Broker,
) -> None:
    """probe_replay_quorum.py: the publish re-declared the quorum queue as classic -- a 400
    -- and left `.dlx` and `.dlq` behind."""
    _declare(broker, "vibey.jobs.p1", quorum=True)
    await broker.bus.publish("vibey.jobs.p1", {"replayed": True})
    names = {q["name"] for q in broker.api.request("GET", f"queues/{broker.api.vhost}")}
    exchanges = {x["name"] for x in broker.api.request("GET", f"exchanges/{broker.api.vhost}")}
    assert names == {"vibey.jobs.p1"}
    assert "vibey.jobs.p1.dlx" not in exchanges
    assert broker.settled("vibey.jobs.p1", "messages", 1) == 1


async def test_finding_12_a_quorum_queue_reports_no_head_timestamp(broker: Broker) -> None:
    """probe_hmt.py: why a quorum queue's ready age is never measured, and a classic
    queue's is."""
    _declare(broker, "vibey.qq", quorum=True)
    _declare(broker, "vibey.cq")
    stamp = int(time.time()) - 5_000
    _publish(broker, "vibey.qq", "{}", timestamp=stamp)
    _publish(broker, "vibey.cq", "{}", timestamp=stamp)
    broker.settled("vibey.cq", "messages_ready", 1)
    broker.settled("vibey.qq", "messages_ready", 1)
    await asyncio.sleep(6)
    depths = {d.queue: d for d in await broker.inspector.depths()}
    assert depths["vibey.qq"].kind == "quorum"
    assert depths["vibey.qq"].oldest_ready_age_seconds is None
    assert depths["vibey.cq"].kind == "classic"
    age = depths["vibey.cq"].oldest_ready_age_seconds
    assert age is not None and age >= 4_990


async def test_a_quorum_dead_letter_survives_being_read_again_and_again(broker: Broker) -> None:
    """probe_quorum_peek.py: a read returns each message to its place; on a quorum queue
    that must not count toward its delivery limit and drop it -- a reaper never deletes a
    dead letter. Thirty reads, past the default limit of twenty."""
    _declare(broker, "vibey.jobs.dead", quorum=True)
    await broker.inspector.apply_policy(POLICY)
    _publish(broker, "vibey.jobs.dead", '{"k": 1}', message_id="m1")
    broker.settled("vibey.jobs.dead", "messages", 1)
    for _ in range(30):
        peek = await broker.inspector.peek_dead_letters("vibey.jobs.dead", limit=100)
        assert [item.message_id for item in peek.items] == ["m1"]
    assert broker.settled("vibey.jobs.dead", "messages", 1) == 1


async def test_finding_10_a_read_returns_the_same_head_so_the_window_must_grow(
    broker: Broker,
) -> None:
    """probe_broker.py: a read with requeue gives back the same head, in the same order,
    every time -- which is why the reaper widens the read by what it has parked."""
    await broker.bus.declare_queue("vibey.probe")
    for i in range(150):
        await broker.bus.publish("vibey.probe", {"i": i})
    broker.api.request(
        "POST",
        f"queues/{broker.api.vhost}/vibey.probe/get",
        {"count": 150, "ackmode": "reject_requeue_false", "encoding": "auto"},
    )
    broker.settled("vibey.probe.dlq", "messages", 150)
    first = await broker.inspector.peek_dead_letters("vibey.probe.dlq", limit=100)
    second = await broker.inspector.peek_dead_letters("vibey.probe.dlq", limit=100)
    head = [json.loads(d.body)["i"] for d in first.items]
    assert head == [json.loads(d.body)["i"] for d in second.items] == list(range(100))
    assert (first.depth, first.complete) == (150, False)
    wider = await broker.inspector.peek_dead_letters("vibey.probe.dlq", limit=250)
    assert [json.loads(d.body)["i"] for d in wider.items] == list(range(150))
    assert wider.complete


async def test_probe_forge_a_forged_origin_is_read_as_what_it_claims(broker: Broker) -> None:
    """probe_forge.py: the origin comes from the message's own headers. Dead-lettering
    overwrites a forged `x-first-death-queue` (the broker writes its own), but anyone who
    can publish can put a message straight onto a dead-letter queue with whatever headers
    they like. The reaper reads them faithfully -- and the policy says the queue they name
    is not vibey's, so replay is never offered."""
    await broker.bus.declare_queue("vibey.forge")
    _publish(
        broker,
        "vibey.forge.dlq",
        '{"evil": true}',
        message_id="forged-1",
        headers={"x-first-death-queue": "celery", "x-first-death-reason": "expired"},
    )
    broker.settled("vibey.forge.dlq", "messages", 1)
    (item,) = (await broker.inspector.peek_dead_letters("vibey.forge.dlq", limit=10)).items
    assert (item.origin_queue, item.reason) == ("celery", "expired")
    assert not POLICY.owns(item.origin_queue)


async def test_a_dispatch_benchmark_leaves_no_queue_and_the_policy_verifies(
    broker: Broker,
) -> None:
    """The #1244 cluster-smoke flake: three `vibey.dispatch.benchmark.<uuid>` queues per run,
    never deleted, owned by the reap policy and reading 'no policy' when it was checked."""
    _declare(broker, "vibey.jobs")
    result = await BusDispatchBenchmark(messages=2, hybrid_concurrency=2).run(broker.bus)
    assert result["winner"] in {"singleton", "multiplexer", "hybrid"}
    queues = broker.api.request("GET", f"queues/{broker.api.vhost}")
    assert [queue["name"] for queue in queues] == ["vibey.jobs"]
    await broker.bus.delete_queue("vibey.never-declared")
    outcome = await broker.inspector.apply_policy(POLICY)
    assert outcome.verified, outcome.detail


def test_an_unreachable_broker_is_named_without_its_password() -> None:
    """probe_leak.py, the reachable half: a refused connection names no credential."""
    api = RabbitMqManagementApi(url="http://127.0.0.1:1", username="u", password="s3cretpw")
    with pytest.raises(Exception, match="cannot reach the RabbitMQ management API") as caught:
        api.request("GET", "overview")
    assert "s3cretpw" not in str(caught.value)
    assert not isinstance(caught.value, RabbitMqApiError)
