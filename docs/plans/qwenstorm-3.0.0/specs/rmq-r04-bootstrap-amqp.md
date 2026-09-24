## Title
feat(bootstrap): vibey_bootstrap.amqp, the family's RabbitMQ client

## Why
Sub-doctrine 10.e: a capability gap is closed by teaching the family, not by writing a
private copy in one consumer.

The family's only consumer machinery is Azure Service Bus
(`vibey_bootstrap/servicebus/consumer_wrapper.py:26-35` and `:53-92`), and it is sync.
Its settle vocabulary is `complete`, `abandon` and `dead_letter`. ADR-0044 §14 puts
the RabbitMQ transport here, under that same vocabulary, so that both vibey's queue
backend and its loop services use one client. The module's docstring carries the
written capability-gap reason.

## Required behaviour
1. **`settings.py`:** `AmqpSettings`, a frozen dataclass:
   - `url: str`, which must start with `amqp://` or `amqps://`, else `ValueError`
   - `connection_name: str = "vibey"`
   - `heartbeat_seconds: int = 60`
   - `publish_timeout_seconds: float = 10.0`
   - `redacted_url() -> str` replaces the password with `***`
2. **`properties.py`:** `AmqpProperties`, a frozen dataclass:
   - `message_id: str | None = None`
   - `correlation_id: str | None = None`
   - `reply_to: str | None = None`
   - `type: str | None = None`
   - `content_type: str = "application/json"`
   - `delivery_mode: int = 2`
   - `priority: int | None = None`
   - `headers: Mapping[str, object] = {}` (use `field(default_factory=dict)`)
3. **`delivery.py`:** `AmqpDelivery`, with these attributes:
   - `body: bytes`
   - `properties: AmqpProperties`
   - `routing_key: str`
   - `redelivered: bool`
   - `delivery_count: int`, read from the `x-delivery-count` header, 0 when absent

   It has three async settle methods, each returning `True` when it settled and
   `False` if the delivery was already settled:
   - `complete()` = `basic.ack`
   - `abandon()` = `basic.nack(requeue=True)`
   - `dead_letter()` = `basic.reject(requeue=False)`

   Each settle calls `vibey_bootstrap.heartbeat.record_message_settled()`.
4. **`errors.py`:** `AmqpError`, `AmqpPublishError(AmqpError)` and
   `AmqpNotConnected(AmqpError)`.
5. **`client.py`:** `AmqpClient(settings, *, connector=aio_pika.connect_robust)`. The
   connector is injected so that unit tests pass a fake, with no patching.
   - `connect()` opens a robust connection with
     `client_properties={"connection_name": ...}` and `heartbeat`, plus one publish
     channel with `publisher_confirms=True`.
   - `close()` closes it.
   - Any other method called before `connect()` connects lazily.
   - `declare_exchange(name, kind)`: `kind` is `direct`, `topic` or `fanout`; durable.
   - `declare_queue(name, *, arguments=None, durable=True, exclusive=False, auto_delete=False) -> str`
     returns the real name. Pass `""` for a server-named queue.
   - `bind(queue, exchange, routing_key)`.
   - `publish(exchange, routing_key, body, properties, *, mandatory=True)` waits for
     the confirm, and raises `AmqpPublishError` on a nack, a return (unroutable while
     mandatory), or a timeout.
   - `consume(queue, *, prefetch, handler) -> str` opens a dedicated channel per
     consumer with `set_qos(prefetch_count=prefetch)`. It calls
     `handler(AmqpDelivery)` for each message, calls
     `vibey_bootstrap.heartbeat.record_consumer_iteration()` per message, and returns
     the consumer tag.
   - `cancel(tag)`.
   - `get(queue) -> AmqpDelivery | None` is `basic.get` without auto-ack.
6. **`memory.py`:** `InMemoryAmqpClient`, which implements the same interface with no
   network:
   - direct routing, topic routing (`*` and `#`) and fanout routing;
   - FIFO queues;
   - push to consumers up to `prefetch` unsettled messages;
   - `abandon` requeues at the head and increments `x-delivery-count`;
   - a queue declared with `x-delivery-limit` dead-letters, to its
     `x-dead-letter-exchange` with the routing key kept, any message whose count would
     exceed the limit;
   - `dead_letter()` routes to the queue's DLX;
   - `simulate_channel_close(tag)` returns every unsettled delivery of that consumer,
     with its count incremented;
   - `expire(queue)` dead-letters every message of a queue declared with
     `x-message-ttl` to its DLX, keeping the routing key. Tests call it instead of
     sleeping;
   - `published` is a list of `(exchange, routing_key, body, properties)` for
     assertions;
   - a mandatory publish that routes nowhere raises `AmqpPublishError`.
7. **`interfaces/client_interface.py`:** `AmqpClientInterface` and
   `AmqpDeliveryInterface`, both `runtime_checkable` Protocols. Mirror the layout of
   `vibey_bootstrap/services/interfaces/`.
8. **`__init__.py`:** exports the public names. Its module docstring states the 10.e
   reason: "The family had no AMQP client; the management HTTP API's `get` is a
   diagnostics endpoint with at-most-once, prefetch-free semantics
   (vibey/infrastructure/bus/rabbitmq.py). ADR-0044 §14."

## Where to change
- The new package under `src/vibey_tools/bootstrap/vibey_bootstrap/amqp/`.
- Copy the `Protocol` + implementation style of `vibey_bootstrap/servicebus/consumer_wrapper.py`.
- aio-pika API: `aio_pika.connect_robust`, `connection.channel(publisher_confirms=True)`,
  `channel.set_qos`, `channel.declare_exchange`, `channel.declare_queue`,
  `queue.bind`, `exchange.publish(aio_pika.Message(...), routing_key, mandatory=True)`,
  `queue.consume`, `message.ack()`, `message.nack(requeue=True)`,
  `message.reject(requeue=False)`, `queue.get(no_ack=False, fail=False)`.

## Acceptance criteria
- [ ] The in-memory client routes, respects prefetch, counts deliveries, dead-letters at the limit, expires TTL queues, and refuses unroutable mandatory publishes.
- [ ] `AmqpClient` works against a fake connector: it declares, publishes with a confirm, consumes with qos, and settles.
- [ ] The integration test passes against a real broker when `VIBEY_TEST_AMQP_URL` is set, and is skipped otherwise.
- [ ] The tenant's static gates pass (mypy, bandit).

## Tests to write first (TDD)
- `test/amqp/test_settings.py`:
  - `test_url_scheme_is_required`
  - `test_redacted_url_hides_the_password`
- `test/amqp/test_memory_client.py`:
  - `test_topic_routing_matches_star_and_hash`
  - `test_prefetch_bounds_unsettled_pushes`
  - `test_abandon_requeues_at_head_and_counts`
  - `test_delivery_limit_dead_letters_with_the_routing_key`
  - `test_channel_close_returns_unsettled_deliveries`
  - `test_expire_moves_ttl_messages_to_the_dlx`
  - `test_unroutable_mandatory_publish_raises`
  - `test_settling_twice_returns_false`
- `test/amqp/test_client_unit.py`: drive `AmqpClient` through a fake connector object
  (no network), asserting it declares, publishes and waits for the confirm, raises on
  a nack, sets qos per consumer, and maps `complete`, `abandon` and `dead_letter` to
  ack, nack and reject.
- `test/amqp/test_client_integration.py` (`@pytest.mark.integration`, skipped without
  `VIBEY_TEST_AMQP_URL`):
  - `test_round_trip_against_a_real_broker`
  - `test_quorum_delivery_limit_dead_letters_after_channel_closes`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    (cd src/vibey_tools/bootstrap && uv run python -m pytest -q -p no:cacheprovider test/amqp -m "not integration")
    (cd src/vibey_tools/bootstrap && uv run python -m mypy vibey_bootstrap/ && uv run python -m bandit -r vibey_bootstrap/ -ll -q)
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/meta

## Out of scope
- Anything under `src/vibey/`.
- Topology (R12).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

## Lane card
- **Depends on:** R03.
- **Wave:** 2.
- **Files touched:**
  - `src/vibey_tools/bootstrap/vibey_bootstrap/amqp/{__init__,settings,properties,delivery,errors,client,memory}.py` (new)
  - `src/vibey_tools/bootstrap/vibey_bootstrap/amqp/interfaces/{__init__,client_interface}.py` (new)
  - `src/vibey_tools/bootstrap/test/amqp/{__init__,test_settings,test_memory_client,test_client_unit,test_client_integration}.py` (new)
- **Parallel-safe with:** R07, R10, R21 and R29.
- **Must keep passing unchanged:**
  - the whole vibey-bootstrap suite, `(cd src/vibey_tools/bootstrap && pytest test/ -m "not integration")`
  - the root suite
  - all protected tests
- **Standing constraints:** see the list above.

## Standing constraints for every RabbitMQ lane
- **Protected tests are never edited:** `tests/domain/test_noloss*.py`,
  `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`,
  `tests/system/test_delivery_stage_set.py`, `tests/live/**` (`.vibey-gh.toml:78-85`,
  `.github/CODEOWNERS`). They must keep passing.
- **The first line of every new source file** is the provenance comment, copied
  byte-for-byte from line 1 of a sibling file (`vibey-gh check` compares it exactly).
- **No lane needs a running RabbitMQ.** Unit tests use
  `vibey_bootstrap.amqp.memory.InMemoryAmqpClient` (lane R04). Tests against a real
  broker are marked `integration` and skip unless `VIBEY_TEST_AMQP_URL` is set.
- **SQL runs on PostgreSQL 14:** no `MERGE`, no PostgreSQL 15+ syntax. The 14–18 matrix
  runs `tests/infrastructure/db`.
- **Defaults stay today's until R34:** `queue.backend = "postgres"` and
  `engines.invocation = "subprocess"`.

---
