# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads a RabbitMQ broker for the queue reaper, without taking anything off it (ADR-0056).

Three things, all over the management HTTP API:

- **depths**: every queue on the vhost, with its ready and unacknowledged counts, its
  consumer count, and the age of its head message where the message carries a
  `timestamp` (vibey's publishes do). The counts are the management plugin's sampled
  statistics, a few seconds old at most -- a measurement, which is all a threshold needs.
- **peek_dead_letters**: up to a limit of a dead-letter queue's head messages, fetched
  with `ackmode: ack_requeue_true`, so each goes straight back to its place. Read, never
  removed: a reaper never deletes a dead letter.
- **apply_policy**: vibey's two policies (quorum, classic) for the queues it owns,
  reconciled -- read, written only when they differ, read back -- and then checked on the
  owned queues themselves: a policy object that no queue carries is not in force (12.e).
"""

from __future__ import annotations

import asyncio
import base64
import re
import time
import urllib.request
from collections.abc import Callable
from typing import Any, Final

from vibey.application.interfaces.queue_reap import BusInspectorPort
from vibey.domain.interfaces.queue_reap_interface import BrokerPolicyInterface
from vibey.domain.queue_reap import (
    DeadLetter,
    DeadLetterPeek,
    PolicyOutcome,
    QueueAttachment,
    QueueDepth,
)
from vibey.infrastructure.bus.management import RabbitMqApiError, RabbitMqManagementApi

PEEK_TRUNCATE_BYTES: Final = 65_536
"""The most of one dead letter's body a peek reads back. A longer body is marked
truncated, and a truncated body is never replayed as though it were whole."""

_DEAD_LETTER_SUFFIX: Final = re.compile(r"\.(dlq|dead)$")


class RabbitMqBusInspector(BusInspectorPort):
    """The management API's view of one vhost, for the reaper."""

    def __init__(
        self,
        *,
        url: str,
        username: str,
        password: str,
        vhost: str = "/",
        opener: Any = urllib.request.urlopen,
        epoch_seconds: Callable[[], float] = time.time,
        settle_seconds: float = 15.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._api = RabbitMqManagementApi(
            url=url, username=username, password=password, vhost=vhost, opener=opener
        )
        self._epoch_seconds = epoch_seconds
        self._settle_seconds = settle_seconds
        self._sleep = sleep

    async def depths(self) -> tuple[QueueDepth, ...]:
        return await asyncio.to_thread(self._depths_sync)

    def _depths_sync(self) -> tuple[QueueDepth, ...]:
        rows = self._api.request(
            "GET",
            f"queues/{self._api.vhost}?columns=name,type,messages_ready,"
            "messages_unacknowledged,consumers,head_message_timestamp",
        )
        now = self._epoch_seconds()
        depths: list[QueueDepth] = []
        for row in rows or ():
            stamp = row.get("head_message_timestamp")
            age = max(0.0, now - float(stamp)) if isinstance(stamp, int | float) else None
            depths.append(
                QueueDepth(
                    queue=str(row["name"]),
                    ready=int(row.get("messages_ready") or 0),
                    unacked=int(row.get("messages_unacknowledged") or 0),
                    consumers=int(row.get("consumers") or 0),
                    oldest_ready_age_seconds=age,
                    kind=str(row.get("type") or ""),
                )
            )
        return tuple(depths)

    async def peek_dead_letters(self, queue: str, *, limit: int) -> DeadLetterPeek:
        return await asyncio.to_thread(self._peek_sync, queue, limit)

    def _peek_sync(self, queue: str, limit: int) -> DeadLetterPeek:
        path = f"queues/{self._api.vhost}/{self._api.name(queue)}"
        info = self._api.request("GET", path)
        depth = int((info or {}).get("messages") or 0)
        if depth == 0:
            return DeadLetterPeek(queue=queue, depth=0)
        messages = self._api.request(
            "POST",
            f"{path}/get",
            {
                "count": limit,
                "ackmode": "ack_requeue_true",
                "encoding": "auto",
                "truncate": PEEK_TRUNCATE_BYTES,
            },
        )
        items = tuple(self._dead_letter(queue, message) for message in messages or ())
        return DeadLetterPeek(queue=queue, depth=max(depth, len(items)), items=items)

    @staticmethod
    def _dead_letter(queue: str, message: dict[str, Any]) -> DeadLetter:
        raw = str(message.get("payload", ""))
        body = (
            base64.b64decode(raw).decode("utf-8", errors="replace")
            if message.get("payload_encoding") == "base64"
            else raw
        )
        properties = message.get("properties") or {}
        headers = properties.get("headers") or {}
        deaths = headers.get("x-death") or []
        latest = deaths[0] if deaths else {}
        origin = headers.get("x-first-death-queue") or latest.get("queue")
        reason = headers.get("x-first-death-reason") or latest.get("reason")
        first_time = deaths[-1].get("time") if deaths else None
        size = message.get("payload_bytes")
        return DeadLetter(
            queue=queue,
            origin_queue=str(origin) if origin else _DEAD_LETTER_SUFFIX.sub("", queue),
            reason=str(reason) if reason else "unknown",
            body=body,
            message_id=str(properties["message_id"]) if properties.get("message_id") else None,
            first_death_at=str(first_time) if first_time is not None else None,
            truncated=isinstance(size, int) and size > len(body.encode("utf-8")),
        )

    async def apply_policy(self, policy: BrokerPolicyInterface) -> PolicyOutcome:
        return await asyncio.to_thread(self._apply_sync, policy)

    def _apply_sync(self, policy: BrokerPolicyInterface) -> PolicyOutcome:
        written = False
        problems: list[str] = []
        for document in policy.documents():
            path = f"policies/{self._api.vhost}/{self._api.name(document.name)}"
            if document.matches(self._read_policy(path)):
                continue
            try:
                self._api.request("PUT", path, document.body())
            except RabbitMqApiError as exc:
                problems.append(f"{document.name}: the broker refused it: {exc}")
                continue
            written = True
            observed = self._read_policy(path)
            if not document.matches(observed):
                problems.append(f"{document.name}: written, but read back as {observed!r}")
        if problems:
            return PolicyOutcome(policy=policy.name, verified=False, detail="; ".join(problems))
        # A policy object is not a policy in force: only the queues say which policy they
        # carry (12.e, #1108 review finding 2). A policy just written takes the broker's
        # statistics a few seconds to show, so a write earns a bounded wait.
        waited = 0.0
        while True:
            gaps = policy.attachment_gaps(self._attachments())
            if not gaps or not written or waited >= self._settle_seconds:
                break
            self._sleep(1.0)
            waited += 1.0
        if gaps:
            return PolicyOutcome(
                policy=policy.name,
                verified=False,
                detail="read back, but not in force on: " + "; ".join(gaps),
            )
        return PolicyOutcome(
            policy=policy.name,
            verified=True,
            detail=(
                "written, read back, and in force on every owned queue"
                if written
                else "in force on every owned queue"
            ),
        )

    def _attachments(self) -> tuple[QueueAttachment, ...]:
        rows = self._api.request(
            "GET", f"queues/{self._api.vhost}?columns=name,type,policy,effective_policy_definition"
        )
        return tuple(
            QueueAttachment(
                queue=str(row["name"]),
                kind=str(row.get("type") or ""),
                policy=str(row["policy"]) if row.get("policy") else None,
                effective=dict(row.get("effective_policy_definition") or {}),
            )
            for row in rows or ()
        )

    def _read_policy(self, path: str) -> object:
        try:
            return self._api.request("GET", path)
        except RabbitMqApiError as exc:
            if exc.status == 404:
                return None
            raise
