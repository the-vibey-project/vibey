<!-- split of #351: child 2 of 2; audit: issue-audit/updates/351.md -->
## Title
feat(bootstrap): AmqpClient, the aio-pika transport behind vibey_bootstrap.amqp

## Why
Sub-doctrine 10.e (`src/vibey_tools/gh/docs/doctrines.md:417`) and ADR-0044 §14
(`docs/architecture/decisions/0044-job-queue-port-and-loop-services.md:511-515`) ask `vibey_bootstrap.amqp` for a robust connection, a confirming
publisher, a prefetching consumer and an `AmqpDelivery` whose settles mirror Service Bus (`complete` =
`basic.ack`, `abandon` = `basic.nack(requeue=True)`, `dead_letter` = `basic.reject(requeue=False)`).
Child 1 (`split-351-1-amqp-contract`) shipped the contract and the in-memory broker; this lane adds the
real transport behind the same `AmqpClientInterface`, so the queue backend (#359–#363) and the
ADR-0045/ADR-0047 lanes swap the double for the broker at one constructor. The connector is injected
(sub-doctrine 9.b, `doctrines.md:349`), so the unit tests drive the client with a fake connector and
never patch `aio_pika`. Verified at integration `4317cff6`; the aio-pika facts below were read from the
aio-pika 10.0.1, aiormq 7.0.0 and pamqp 4.0.1 wheels.

## Required behaviour
All paths are under `src/vibey_tools/bootstrap/vibey_bootstrap/amqp/`.

1. **`delivery.py`:** `class AmqpDelivery` implements `AmqpDeliveryInterface`. Its constructor takes
   one `aio_pika.abc.AbstractIncomingMessage` and sets:
   - `body = message.body`;
   - `properties = AmqpProperties(message_id=message.message_id, correlation_id=message.correlation_id,
     reply_to=message.reply_to, type=message.type, content_type=message.content_type or "application/json",
     delivery_mode=int(message.delivery_mode) if message.delivery_mode is not None else 2,
     priority=message.priority, headers=dict(message.headers or {}))`;
   - `routing_key = message.routing_key or ""`; `redelivered = bool(message.redelivered)`;
   - `delivery_count` = the `x-delivery-count` header when it is an `int`, else `0`.
   Settles:
   - `complete()` awaits `message.ack()`; `abandon()` awaits `message.nack(requeue=True)`;
     `dead_letter()` awaits `message.reject(requeue=False)`.
   - Each returns `False` without calling the broker when `message.processed` is true, and returns
     `False` when the call raises `aio_pika.exceptions.MessageProcessError` or
     `aio_pika.exceptions.ChannelInvalidStateError` (the channel is gone, so the broker has already
     returned the message). Otherwise it calls `vibey_bootstrap.heartbeat.record_message_settled()`
     and returns `True`.
2. **`client.py`:** `class AmqpClient` implements `AmqpClientInterface`:
   `AmqpClient(settings: AmqpSettings, *, connector: Callable[[str], Awaitable[AbstractRobustConnection]] = aio_pika.connect_robust)`.
   The connector is the only way in to the network, so unit tests pass a fake connector object.
   1. **`connect()`**: when already open it does nothing. Otherwise
      `self._connection = await self._connector(self._connection_url())` and then the publish channel
      `self._channel = await self._connection.channel(publisher_confirms=True, on_return_raises=True)`.
      `_connection_url()` (a private method) returns `settings.url` with the query parameters
      `name=<connection_name>` and `heartbeat=<heartbeat_seconds>` set, replacing any existing values of
      those two keys and keeping every other query parameter, built with `urllib.parse`
      (`urlsplit`, `parse_qsl(keep_blank_values=True)`, `urlencode`, `urlunsplit`):
      `amqp://vibey:s3cret@broker:5672/%2F` becomes `amqp://vibey:s3cret@broker:5672/%2F?name=vibey&heartbeat=60`,
      and `amqp://b/?heartbeat=5&x=1` becomes `amqp://b/?x=1&name=vibey&heartbeat=60`.
      (aio-pika ignores `client_properties=` and extra keywords when it is given a URL string —
      `make_url` returns the URL unchanged, `aio_pika/connection.py:283-286` — and aiormq reads the
      heartbeat and the connection name from the URL query, `aiormq/connection.py:413-419`.)
   2. **Lazy and closed.** Every other method first opens the client lazily when it was never opened.
      `close()` awaits `self._connection.close()` when a connection exists, drops the connection, the
      publish channel and every consumer entry, and marks the client closed. While closed, every method
      except `connect()` and `close()` raises
      `AmqpNotConnected("AmqpClient is closed; call connect() first")`; `connect()` reopens it.
   3. **`declare_exchange(name, kind)`** raises
      `ValueError(f"exchange kind must be direct, topic or fanout, not {kind!r}")` for any other kind,
      else awaits `self._channel.declare_exchange(name, kind, durable=True)`.
   4. **`declare_queue(name, *, arguments=None, durable=True, exclusive=False, auto_delete=False) -> str`**
      awaits `self._channel.declare_queue(name, durable=durable, exclusive=exclusive,
      auto_delete=auto_delete, arguments=dict(arguments) if arguments is not None else None)` and returns
      the declared queue's `.name` (the broker's name for `""`).
   5. Both declares turn `aio_pika.exceptions.ChannelPreconditionFailed` into
      `AmqpError(f"PRECONDITION_FAILED - exchange {name!r} was declared with other arguments")` (and the
      same text with `queue`), exactly as the in-memory broker words it. aio-pika's `RobustChannel`
      reopens itself after the broker closes it, so nothing else is needed.
   6. **`bind(queue, exchange, routing_key)`**: `q = await self._channel.get_queue(queue, ensure=False)`,
      then `await q.bind(exchange, routing_key=routing_key)`.
   7. **`publish(exchange, routing_key, body, properties, *, mandatory=True)`**:
      `target = await self._channel.get_exchange(exchange, ensure=False)`; build
      `aio_pika.Message(body, headers=dict(properties.headers), content_type=properties.content_type,
      delivery_mode=properties.delivery_mode, priority=properties.priority,
      correlation_id=properties.correlation_id, reply_to=properties.reply_to,
      message_id=properties.message_id, type=properties.type)`; then
      `confirmation = await target.publish(message, routing_key, mandatory=mandatory, timeout=self._settings.publish_timeout_seconds)`.
      - Any `aio_pika.exceptions.AMQPError` (a nack arrives as `DeliveryError`; an unroutable mandatory
        message arrives as `PublishError`, because the channel was opened with `on_return_raises=True`),
        `aio_pika.exceptions.ChannelInvalidStateError` or `TimeoutError` raises
        `AmqpPublishError(f"publish to {exchange!r} with routing key {routing_key!r} was not confirmed: {type(exc).__name__}")`
        chained `from exc`.
      - A confirmation that is not an instance of `pamqp.commands.Basic.Ack` raises
        `AmqpPublishError(f"publish to {exchange!r} with routing key {routing_key!r} was not confirmed: no Basic.Ack")`.
   8. **`consume(queue, *, prefetch, handler) -> str`**: `prefetch < 1` raises
      `ValueError("prefetch must be at least 1")` before any channel opens. Otherwise open a dedicated
      channel, `channel = await self._connection.channel(publisher_confirms=False)`, then
      `await channel.set_qos(prefetch_count=prefetch)`, `q = await channel.get_queue(queue, ensure=False)`
      and `tag = await q.consume(callback)`, where `callback` is a nested `async def` that calls
      `vibey_bootstrap.heartbeat.record_consumer_iteration()` and then awaits
      `handler(AmqpDelivery(message))`. Keep `q` under its tag and return the tag.
   9. **`cancel(tag)`**: pops the tag's queue and awaits `q.cancel(tag)`; an unknown tag does nothing.
      The consumer's channel stays open until `close()`, so deliveries it already holds can still be
      settled (the in-memory broker's `cancel` behaves the same way).
   10. **`get(queue)`**: `q = await self._channel.get_queue(queue, ensure=False)`,
       `message = await q.get(no_ack=False, fail=False)`; returns `None` when that is `None`, else
       `AmqpDelivery(message)`.
3. **`__init__.py`** also exports `AmqpClient` and `AmqpDelivery` (import them and add both to
   `__all__`), and its docstring gains one sentence after the existing text: "`AmqpClient` needs the
   `amqp` extra (aio-pika), so importing this package needs it too; `InMemoryAmqpClient` is the
   network-free double."
4. `client.py` and `delivery.py` must be covered line for line by the unit tests (the tenant's 100% line
   floor, `pyproject.toml:402`).

## Where to change
- New `src/vibey_tools/bootstrap/vibey_bootstrap/amqp/client.py` (`AmqpClient`) and
  `src/vibey_tools/bootstrap/vibey_bootstrap/amqp/delivery.py` (`AmqpDelivery`). Their interfaces
  already exist beside them: `vibey_bootstrap/amqp/interfaces/client_interface.py` (child 1). Do not
  change that file.
- `src/vibey_tools/bootstrap/vibey_bootstrap/amqp/__init__.py`: the two exports and the docstring
  sentence only.
- New tests `src/vibey_tools/bootstrap/test/amqp/test_client_unit.py` and
  `src/vibey_tools/bootstrap/test/amqp/test_client_integration.py`.
- Why two source files: the audit splits the delivery (a per-message wrapper) from the client (the
  connection owner), matching the two Protocols child 1 declared. No `packages` entry changes:
  both files live in the `vibey_bootstrap.amqp` package child 1 declared.
- Copy line 1 (the provenance comment) of any sibling file byte for byte. Follow the lazy-construction
  style of `vibey_bootstrap/amqp/memory.py` (child 1) for the open/closed state.

## Acceptance criteria
- [ ] `test/amqp/test_client_unit.py` passes against a fake connector: the client names its connection
      and heartbeat in the URL, opens a confirming publish channel, declares, publishes and waits for
      the confirm, raises `AmqpPublishError` on a nack, a return, a timeout and a missing `Basic.Ack`,
      sets qos per consumer, cancels, gets without auto-ack, and maps `complete`/`abandon`/`dead_letter`
      to `ack()`/`nack(requeue=True)`/`reject(requeue=False)`.
- [ ] `test/amqp/test_client_integration.py` passes against a real RabbitMQ when `VIBEY_TEST_AMQP_URL`
      is set, and is skipped otherwise.
- [ ] `isinstance(AmqpClient(AmqpSettings("amqp://x/")), AmqpClientInterface)` and an `AmqpDelivery`
      satisfies `AmqpDeliveryInterface`.
- [ ] The whole tenant suite keeps its 100% line floor; the tenant's mypy and bandit pass; root
      `ruff check` and `ruff format --check` pass.
- [ ] `grep -nE "monkeypatch|mock\.patch|MagicMock|AsyncMock" src/vibey_tools/bootstrap/test/amqp/*.py` prints nothing.

## Tests to write first (TDD)
`src/vibey_tools/bootstrap/test/amqp/test_client_unit.py` (no service). Write the doubles as small
plain classes in the test module and hand them to the client through `connector=`:
- `FakeConnector` — an object with `async __call__(self, url: str)` that records `url` and returns a
  `FakeConnection`.
- `FakeConnection` — `async channel(self, *, publisher_confirms=True, on_return_raises=False)` records
  its keywords and returns a new `FakeChannel`; `async close()` records it.
- `FakeChannel` — `async declare_exchange(name, type, *, durable)`, `async declare_queue(name, *,
  durable, exclusive, auto_delete, arguments)` (returns a `FakeQueue` named `"amq.gen-x"` for `""`),
  `async get_exchange(name, *, ensure)` (returns a `FakeExchange`), `async get_queue(name, *, ensure)`
  (returns a `FakeQueue`), `async set_qos(*, prefetch_count)`; each records its arguments, and a
  settable attribute makes the declares raise `aio_pika.exceptions.ChannelPreconditionFailed("PRECONDITION_FAILED")`.
- `FakeExchange` — `async publish(message, routing_key, *, mandatory, timeout)` records its arguments
  and returns or raises what the test scripted (default `pamqp.commands.Basic.Ack(delivery_tag=1)`).
- `FakeQueue` — a `name` attribute; `async bind(exchange, routing_key=None)`; `async consume(callback)`
  records the callback and returns a tag unique within the test (for example `f"ctag-{id(self)}"`, since
  every `get_queue` call builds a new `FakeQueue`); `async cancel(tag)` records the tag;
  `async get(*, no_ack, fail)` records its keywords and returns the scripted message or `None`.
- `FakeIncomingMessage` — attributes `body`, `headers`, `routing_key`, `redelivered`, `message_id`,
  `correlation_id`, `reply_to`, `type`, `content_type`, `delivery_mode`, `priority`; a `processed`
  property; `async ack()`, `async nack(requeue=True)`, `async reject(requeue=False)` that record the
  call and set `processed`, or raise a scripted exception.

Tests:
- `test_connect_names_the_connection_and_heartbeat_in_the_url`: the connector gets
  `amqp://vibey:s3cret@broker:5672/%2F?name=vibey&heartbeat=60`; with `amqp://b/?heartbeat=5&x=1` it
  gets `amqp://b/?x=1&name=vibey&heartbeat=60`; the first channel was opened with
  `publisher_confirms=True, on_return_raises=True`; a second `connect()` calls the connector no more.
- `test_a_first_call_connects_lazily_and_a_closed_client_refuses`: `declare_exchange` before `connect`
  connects; `close()` closes the fake connection; `publish` then raises `AmqpNotConnected`; after
  `connect()` it works again; `close()` on a never-opened client marks it closed too.
- `test_declares_and_binds_map_to_the_channel`: `declare_exchange("vibey.jobs", "topic")` calls
  `declare_exchange("vibey.jobs", "topic", durable=True)`; kind `"headers"` raises `ValueError`;
  `declare_queue("", arguments={"x-queue-type": "quorum"})` returns `"amq.gen-x"` and passed the
  arguments as a dict; `bind("q", "vibey.jobs", "job.p")` calls `bind("vibey.jobs", routing_key="job.p")`.
- `test_a_redeclare_with_other_arguments_is_an_amqp_error`: both declares raise `AmqpError` whose text
  starts `PRECONDITION_FAILED`.
- `test_publish_waits_for_the_confirm`: the recorded `aio_pika.Message` carries the body,
  `content_type`, `delivery_mode == 2`, `message_id`, `type` and `headers`; `mandatory=True`;
  `timeout=10.0`.
- `test_publish_raises_on_a_nack_a_return_a_timeout_or_no_confirm` (parametrized): the fake exchange
  raises `aio_pika.exceptions.DeliveryError(None, pamqp.commands.Basic.Nack(delivery_tag=1))`, raises
  `aio_pika.exceptions.DeliveryError(None, pamqp.commands.Basic.Return(reply_code=312, reply_text="NO_ROUTE", exchange="vibey.jobs", routing_key="nowhere"))`,
  raises `TimeoutError()`, or returns `None`; each makes `publish` raise `AmqpPublishError` whose text
  names the exchange and the routing key.
- `test_consume_opens_a_channel_per_consumer_with_its_prefetch`: two `consume` calls open two new
  channels with `publisher_confirms=False` and `set_qos(prefetch_count=4)` / `set_qos(prefetch_count=1)`;
  `prefetch=0` raises `ValueError`; awaiting the recorded callback with a `FakeIncomingMessage` calls
  the handler with an `AmqpDelivery`, and after `vibey_bootstrap.heartbeat.reset_state()`
  `metrics_snapshot()["last_consumer_iteration_age_seconds"]` is not `None`.
- `test_cancel_stops_one_consumer`: `cancel(tag)` calls the fake queue's `cancel(tag)`; `cancel("nope")` does nothing.
- `test_get_maps_to_basic_get_without_auto_ack`: `get` passed `no_ack=False, fail=False`, returns an
  `AmqpDelivery` for a message and `None` for an empty queue.
- `test_settles_map_to_ack_nack_and_reject`: `complete` → `ack()`, `abandon` → `nack(requeue=True)`,
  `dead_letter` → `reject(requeue=False)`, each returning `True`; a second settle returns `False` and
  calls nothing; `metrics_snapshot()["last_sb_settle_age_seconds"]` is not `None`.
- `test_a_settle_on_a_closed_channel_returns_false`: `ack()` raising
  `aio_pika.exceptions.ChannelInvalidStateError("closed")`, or `aio_pika.exceptions.MessageProcessError("done")`, makes `complete()` return `False`.
- `test_the_delivery_reads_its_properties_and_count`: headers `{"x-delivery-count": 3}` give
  `delivery_count == 3`; no headers, `content_type=None`, `delivery_mode=None` and `routing_key=None`
  give `0`, `"application/json"`, `2` and `""`.
- `test_the_client_and_its_delivery_satisfy_their_interfaces`.

`src/vibey_tools/bootstrap/test/amqp/test_client_integration.py`, with
`pytestmark = [pytest.mark.integration, pytest.mark.skipif(not os.environ.get("VIBEY_TEST_AMQP_URL"), reason="set VIBEY_TEST_AMQP_URL to run against a real RabbitMQ")]`:
- `test_round_trip_against_a_real_broker`: declare the topic exchange `vibey.test.amqp`, a server-named
  `exclusive=True, auto_delete=True` queue bound on `f"t.{suffix}"` (`suffix = uuid4().hex[:8]`);
  publish `b'{"n": 1}'` with `AmqpProperties(message_id="m1", type="test")`; `get` it (poll every
  0.1 s for up to 5 s); body, `message_id`, routing key and `delivery_count == 0` match; `complete()`
  is `True`, then `False`; a mandatory publish on `f"none.{suffix}"` raises `AmqpPublishError`;
  `close()` in `finally`.
- `test_quorum_delivery_limit_dead_letters_after_channel_closes`: declare the fanout exchange
  `vibey.test.amqp.dlx`, a dead queue `f"vibey.test.dead.{suffix}"` with `{"x-expires": 600000}` bound
  to it with key `""`, and a work queue `f"vibey.test.work.{suffix}"` with `{"x-queue-type": "quorum",
  "x-delivery-limit": 1, "x-dead-letter-exchange": "vibey.test.amqp.dlx", "x-expires": 600000}` bound
  to `vibey.test.amqp` on `f"w.{suffix}"`; publish one message there. Up to three rounds: a fresh
  `AmqpClient` consumes the work queue with `prefetch=1` and a handler that sets an `asyncio.Event`
  without settling; wait for it (10 s), then `close()` that client; then poll `get` on the dead queue
  for up to 2 s. The message arrives in the dead queue, body unchanged, within the three rounds.

## Checks the lane must run (all must pass)
```bash
# Root gates that also cover this tenant's files (root ruff includes src/**; do not run black here)
uv run ruff check . && uv run ruff format --check .
uv run lint-imports
export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
uv run pytest -q -p no:cacheprovider tests/meta
# The tenant's own environment, installed the way CI's floor row does (.github/workflows/ci.yml:278-281); only when missing
(cd src/vibey_tools/bootstrap && { test -x .venv/bin/python || python3.12 -m venv .venv || python3 -m venv .venv; })
(cd src/vibey_tools/bootstrap && { .venv/bin/python -m pip show vibey-bootstrap vibey-gh aio-pika pytest-asyncio mongomock mypy bandit >/dev/null 2>&1 || { .venv/bin/python -m pip install -e ../gh && .venv/bin/python -m pip install -e ".[test,all,dev]"; }; })
# Focused run: a partial run needs --no-cov, because [tool.coverage.report] fail_under = 100 applies to every run
(cd src/vibey_tools/bootstrap && .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov test/amqp test/test_packaging.py)
# The real broker, only when one is configured
(cd src/vibey_tools/bootstrap && if [ -n "${VIBEY_TEST_AMQP_URL:-}" ]; then .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov -m integration test/amqp/test_client_integration.py; fi)
# The whole tenant suite at its 100% line floor (CI's `test` command, verbatim)
(cd src/vibey_tools/bootstrap && .venv/bin/python -m pytest test/ -m "not integration" --cov=vibey_bootstrap --cov-report=term)
# The tenant's static gates (CI's `static` command, verbatim)
(cd src/vibey_tools/bootstrap && .venv/bin/python -m mypy vibey_bootstrap/ && .venv/bin/python -m bandit -r vibey_bootstrap/ -ll -q)
! grep -nE "monkeypatch|mock\.patch|MagicMock|AsyncMock" src/vibey_tools/bootstrap/test/amqp/*.py
git diff --stat
```

## Out of scope
- `interfaces/client_interface.py`, `memory.py`, `settings.py`, `properties.py`, `errors.py` (child 1),
  and `pyproject.toml` (R03 owns the `amqp` extra and the lock; this lane adds no `packages` entry).
- Topology (#359), publishing dispatches (#360), consuming project queues (#361), queue depth, consumer
  count, exclusive consume and the exclusive-queue lease (ADR-0046 L21, ADR-0045 T21, ADR-0047 S07).
- Anything under `src/vibey/`.
- CHANGELOG.md (root and tenant), docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push or change remotes. Commit locally with the Title as the subject.

## Conventions this lane relies on (everything needed is here)
**Child 1's contract** (in `vibey_bootstrap/amqp/`, already on the branch; read it, do not change it):
- `AmqpSettings` (frozen dataclass, `settings.py`): `url: str` (must start `amqp://` or `amqps://`),
  `connection_name: str = "vibey"`, `heartbeat_seconds: int = 60`, `publish_timeout_seconds: float = 10.0`,
  `redacted_url() -> str`.
- `AmqpProperties` (frozen dataclass, `properties.py`): `message_id: str | None = None`,
  `correlation_id: str | None = None`, `reply_to: str | None = None`, `type: str | None = None`,
  `content_type: str = "application/json"`, `delivery_mode: int = 2`, `priority: int | None = None`,
  `headers: Mapping[str, object] = field(default_factory=dict)`.
- `errors.py`: `AmqpError(Exception)`, `AmqpPublishError(AmqpError)`, `AmqpNotConnected(AmqpError)`.
- `interfaces/client_interface.py`, both `@runtime_checkable` Protocols:
  ```python
  class AmqpDeliveryInterface(Protocol):
      body: bytes; properties: AmqpProperties; routing_key: str; redelivered: bool; delivery_count: int
      async def complete(self) -> bool: ...
      async def abandon(self) -> bool: ...
      async def dead_letter(self) -> bool: ...

  class AmqpClientInterface(Protocol):
      async def connect(self) -> None: ...
      async def close(self) -> None: ...
      async def declare_exchange(self, name: str, kind: str) -> None: ...
      async def declare_queue(self, name: str, *, arguments: Mapping[str, object] | None = None,
                              durable: bool = True, exclusive: bool = False, auto_delete: bool = False) -> str: ...
      async def bind(self, queue: str, exchange: str, routing_key: str) -> None: ...
      async def publish(self, exchange: str, routing_key: str, body: bytes,
                        properties: AmqpProperties, *, mandatory: bool = True) -> None: ...
      async def consume(self, queue: str, *, prefetch: int,
                        handler: Callable[[AmqpDeliveryInterface], Awaitable[None]]) -> str: ...
      async def cancel(self, tag: str) -> None: ...
      async def get(self, queue: str) -> AmqpDeliveryInterface | None: ...
  ```
- The in-memory broker raises the same texts, and this client must word them identically:
  `AmqpError(f"PRECONDITION_FAILED - exchange {name!r} was declared with other arguments")` (and `queue`
  for a queue), `ValueError(f"exchange kind must be direct, topic or fanout, not {kind!r}")`,
  `ValueError("prefetch must be at least 1")`, and after `close()` `AmqpNotConnected` (the in-memory text
  names `InMemoryAmqpClient`, this one `AmqpClient`: `"AmqpClient is closed; call connect() first"`).

**The heartbeat** (`vibey_bootstrap/heartbeat/__init__.py`): `record_message_settled()` (`:41`) and
`record_consumer_iteration()` (`:51`), both best-effort and never raising; `reset_state()` (test-only,
allowed because `test/conftest.py` sets `AZURE_BOOTSTRAP_ALLOW_RESET=1`) and `metrics_snapshot()`, whose
keys are `last_sb_settle_age_seconds` and `last_consumer_iteration_age_seconds` (`None` until stamped).

**aio-pika** (read from 10.0.1; `uv.lock` pins the version R03 locked, `>=9.5`):
- `aio_pika.connect_robust(url, ...)` → `aio_pika.abc.AbstractRobustConnection`; `await connection.channel(publisher_confirms=..., on_return_raises=...)`; `await connection.close()`.
- On a channel: `declare_exchange(name, type, *, durable=...)`, `declare_queue(name, *, durable, exclusive, auto_delete, arguments)` (returns a queue with `.name`), `get_exchange(name, *, ensure=False)` and `get_queue(name, *, ensure=False)` (build without a broker round trip; both are `async`), `set_qos(prefetch_count=...)`.
- `exchange.publish(message, routing_key, *, mandatory=True, timeout=...)` returns the confirmation frame; with confirms a `pamqp.commands.Basic.Ack` means accepted, a nack raises `aio_pika.exceptions.DeliveryError`, a return on an `on_return_raises=True` channel raises `aio_pika.exceptions.PublishError` (a `DeliveryError`), and a timeout raises `TimeoutError`.
- `queue.bind(exchange, routing_key=...)`, `queue.consume(callback) -> str`, `queue.cancel(tag)`, `queue.get(no_ack=False, fail=False) -> IncomingMessage | None`.
- An incoming message has `body`, `headers`, `routing_key`, `redelivered`, `message_id`, `correlation_id`, `reply_to`, `type`, `content_type`, `delivery_mode`, `priority`, the `processed` property, and `ack()`, `nack(requeue=True)`, `reject(requeue=False)`; a second settle raises `aio_pika.exceptions.MessageProcessError`.
- `aio_pika.exceptions` exports `AMQPError`, `DeliveryError`, `PublishError`, `ChannelPreconditionFailed`, `ChannelInvalidStateError` and `MessageProcessError`. `pamqp.commands.Basic` has `Ack(delivery_tag=0, multiple=False)`, `Nack(delivery_tag=0, multiple=False, requeue=True)` and `Return(reply_code, reply_text, exchange, routing_key)`.
- RabbitMQ quorum queues count a message's returns in `x-delivery-count` and dead-letter it once that count exceeds `x-delivery-limit`.

## Standing constraints
### Lane card
- **Wave:** 2, after R03 (aio-pika locked, the `amqp` extra) and child 1.
- **Files touched:** `vibey_bootstrap/amqp/{client,delivery}.py` (new), `vibey_bootstrap/amqp/__init__.py`
  (two exports, one docstring sentence), `test/amqp/{test_client_unit,test_client_integration}.py` (new),
  all under `src/vibey_tools/bootstrap/`.
- **Must keep passing unchanged:** child 1's `test/amqp/test_settings.py` and `test_memory_client.py`,
  the whole vibey-bootstrap suite, the root suite, all protected tests.

### For every RabbitMQ lane
- **Protected tests are never edited:** `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`,
  `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`
  (`.vibey-gh.toml`, `.github/CODEOWNERS`). They must keep passing.
- **The first line of every new source file** is the provenance comment, copied byte-for-byte from line 1
  of a sibling file (`vibey-gh check` compares it exactly).
- **The default run needs no outside service.** Tests against a real broker are marked `integration` and
  skip unless `VIBEY_TEST_AMQP_URL` is set.
- **Substitution at a declared seam only:** constructor or keyword injection (here, `connector=`); never
  `monkeypatch.setattr` on a module attribute, `mock.patch`, `MagicMock` or `AsyncMock`.
- **Defaults stay today's until #381 (R34):** `queue.backend = "postgres"` and
  `engines.invocation = "subprocess"`.
- Arch Linux and macOS both: the commands above use only `python3`, `pip` and `uv`; the integration
  test needs only a reachable RabbitMQ URL.

**Depends on:** rmq-r03-amqp-dependency, split-351-1-amqp-contract
- rmq-r03-amqp-dependency: `aio-pika>=9.5` in the lock, in the tenant's new `amqp` extra and in its `all` extra (so `pip install -e ".[test,all,dev]"` brings it).
- split-351-1-amqp-contract: the package, `AmqpSettings`, `AmqpProperties`, the three errors and the two Protocols this client implements.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
