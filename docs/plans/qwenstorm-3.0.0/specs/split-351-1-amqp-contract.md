<!-- split of #351: child 1 of 2; audit: issue-audit/updates/351.md -->
## Title
feat(bootstrap): vibey_bootstrap.amqp's contract, value types and in-memory broker

## Why
Sub-doctrine 10.e (`src/vibey_tools/gh/docs/doctrines.md:417`) closes a capability gap by teaching the
family, and the family's only consumer machinery is sync Azure Service Bus
(`src/vibey_tools/bootstrap/vibey_bootstrap/servicebus/consumer_wrapper.py:26-34` for its Protocols,
`:53-92` for `_settle`), whose settle vocabulary is `complete`, `abandon` and `dead_letter`. ADR-0044 §14
(`docs/architecture/decisions/0044-job-queue-port-and-loop-services.md:511-515`) puts the RabbitMQ transport in `vibey_bootstrap.amqp` under that vocabulary, so vibey's
queue backend (#359–#363), the test-harness queue (draft ADR-0045) and the surface lanes (draft
ADR-0047) share one client and one in-memory double. This lane ships what every later lane's unit tests
need first: the contract (interfaces), the value types and `InMemoryAmqpClient`, a real in-memory broker
with no network and no `aio_pika` import. Child 2 (`split-351-2-amqp-client`) adds the aio-pika
transport behind the same contract. Verified at integration `4317cff6`.

## Required behaviour
All paths below are under `src/vibey_tools/bootstrap/vibey_bootstrap/amqp/`.

1. **`settings.py`:** `AmqpSettings`, a `@dataclass(frozen=True)`:
   - `url: str`. `__post_init__` raises `ValueError("AmqpSettings.url must start with amqp:// or amqps://")`
     unless it starts with `amqp://` or `amqps://`. The message never repeats the URL (it can carry a password).
   - `connection_name: str = "vibey"`
   - `heartbeat_seconds: int = 60`
   - `publish_timeout_seconds: float = 10.0`
   - `redacted_url(self) -> str` replaces the password with `***` and keeps everything else:
     `amqp://vibey:s3cret@broker:5672/%2F` becomes `amqp://vibey:***@broker:5672/%2F`. A URL with no
     password is returned unchanged. Use `urllib.parse.urlsplit`/`urlunsplit` (the userinfo is the part
     of the netloc before the last `@`; the user is the part of it before the first `:`).
2. **`properties.py`:** `AmqpProperties`, a `@dataclass(frozen=True)`:
   `message_id: str | None = None`, `correlation_id: str | None = None`, `reply_to: str | None = None`,
   `type: str | None = None`, `content_type: str = "application/json"`, `delivery_mode: int = 2`,
   `priority: int | None = None`, `headers: Mapping[str, object] = field(default_factory=dict)`.
3. **`errors.py`:** `class AmqpError(Exception)`, `class AmqpPublishError(AmqpError)`,
   `class AmqpNotConnected(AmqpError)`, each with a one-line docstring.
4. **`interfaces/client_interface.py`:** two `@runtime_checkable` Protocols, copying the Protocol
   style of `vibey_bootstrap/servicebus/consumer_wrapper.py:26-34`:
   ```python
   @runtime_checkable
   class AmqpDeliveryInterface(Protocol):
       body: bytes
       properties: AmqpProperties
       routing_key: str
       redelivered: bool
       delivery_count: int          # the x-delivery-count header, 0 when absent

       async def complete(self) -> bool: ...     # basic.ack
       async def abandon(self) -> bool: ...      # basic.nack(requeue=True)
       async def dead_letter(self) -> bool: ...  # basic.reject(requeue=False)

   @runtime_checkable
   class AmqpClientInterface(Protocol):
       async def connect(self) -> None: ...
       async def close(self) -> None: ...
       async def declare_exchange(self, name: str, kind: str) -> None: ...
       async def declare_queue(
           self, name: str, *, arguments: Mapping[str, object] | None = None,
           durable: bool = True, exclusive: bool = False, auto_delete: bool = False,
       ) -> str: ...
       async def bind(self, queue: str, exchange: str, routing_key: str) -> None: ...
       async def publish(
           self, exchange: str, routing_key: str, body: bytes,
           properties: AmqpProperties, *, mandatory: bool = True,
       ) -> None: ...
       async def consume(
           self, queue: str, *, prefetch: int,
           handler: Callable[[AmqpDeliveryInterface], Awaitable[None]],
       ) -> str: ...
       async def cancel(self, tag: str) -> None: ...
       async def get(self, queue: str) -> AmqpDeliveryInterface | None: ...
   ```
   Each settle returns `True` when it settled and `False` when the delivery was already settled.
   `kind` is one of `direct`, `topic`, `fanout`, and exchanges are durable. `declare_queue` returns the
   real name; `""` asks for a server-named queue. `consume` returns the consumer tag. `get` is
   `basic.get` without auto-ack. Give each method a one-line docstring saying exactly this.
   `interfaces/__init__.py` re-exports both names in `__all__`, the way
   `vibey_bootstrap/services/interfaces/__init__.py` does.
5. **`memory.py`:** `class InMemoryAmqpClient` implements `AmqpClientInterface` with no network, and
   `class InMemoryAmqpDelivery` implements `AmqpDeliveryInterface`. Keep each queue's messages and
   consumers as plain per-queue lists (private `@dataclass` records such as `_StoredMessage`,
   `_QueueState`, `_ConsumerState`, holding data only), so that the later lanes which teach this client
   queue depth, consumer count, exclusive consume and an exclusive-queue lease (ADR-0046 §10 lane L21,
   ADR-0045 T21, ADR-0047 S07) can add them without restructuring it. Exact behaviour:
   1. **Lifecycle.** `connect()` opens the client; every other method called before `connect()` opens it
      lazily. `close()` returns every unsettled delivery of every consumer to its queue exactly as
      `simulate_channel_close(tag)` does (item 11), returns every unsettled delivery taken with `get`
      the same way (a real connection close returns those too), removes every consumer, and marks the
      client closed. While closed, every method except `connect()` and `close()` raises
      `AmqpNotConnected("InMemoryAmqpClient is closed; call connect() first")`; `connect()` reopens it.
      `close()` on a closed client does nothing.
   2. **Declarations.** `declare_exchange(name, kind)` raises
      `ValueError(f"exchange kind must be direct, topic or fanout, not {kind!r}")` for any other kind.
      Declaring the same exchange again with the same kind, or the same queue again with equal
      `arguments`, `durable`, `exclusive` and `auto_delete`, is a no-op (the queue call returns its
      name). With a different kind or different arguments it raises (the broker's
      `PRECONDITION_FAILED`): `AmqpError(f"PRECONDITION_FAILED - exchange {name!r} was declared with other arguments")`,
      and the same text with `queue` for a queue. `declare_queue("")` creates a new queue named
      `f"amq.gen-{n}"`, where `n` counts up from 1 per client, and returns that name.
   3. **Unknown names.** `bind`, `consume`, `get` and `expire` on a queue never declared raise
      `AmqpError(f"NOT_FOUND - no queue {name!r}")`; `bind` to an exchange never declared raises
      `AmqpError(f"NOT_FOUND - no exchange {name!r}")`; `publish` to an exchange never declared raises
      `AmqpPublishError(f"NOT_FOUND - no exchange {exchange!r}")`, whatever `mandatory` is. Binding the
      same `(queue, exchange, routing_key)` twice keeps one binding.
   4. **Routing.** A `direct` exchange routes to every queue bound with a binding key equal to the
      routing key; `fanout` to every bound queue whatever the key; `topic` to every queue whose binding
      pattern matches, where the pattern and the key are split on `.`, `*` matches exactly one word and
      `#` matches zero or more words. Implement the match as a private method on the client (not a
      module function), for example:
      ```python
      def _topic_matches(self, pattern: list[str], words: list[str]) -> bool:
          if not pattern:
              return not words
          head, rest = pattern[0], pattern[1:]
          if head == "#":
              return any(self._topic_matches(rest, words[i:]) for i in range(len(words) + 1))
          if not words:
              return False
          return (head == "*" or head == words[0]) and self._topic_matches(rest, words[1:])
      ```
      A message routed to several queues is copied into each, once per queue (bindings in declaration
      order, duplicates removed). Every queue is FIFO: new messages go to the tail.
   5. **Publish.** `publish(exchange, routing_key, body, properties, *, mandatory=True)` routes the
      message (item 4). A publish that routes to no queue raises
      `AmqpPublishError(f"NO_ROUTE - {exchange!r} has no queue bound for routing key {routing_key!r}")`
      when `mandatory` is true, and is silently dropped when it is false. Every publish that does not
      raise `NOT_FOUND` or `NO_ROUTE` appends `(exchange, routing_key, body, properties)` to the public
      list `published`, before any push, so a handler that raises during the push (item 6) does not
      hide the publish from `published`.
   6. **Consume and prefetch.** `consume(queue, *, prefetch, handler)` raises
      `ValueError("prefetch must be at least 1")` when `prefetch < 1`. Otherwise it registers a consumer
      with a tag `f"ctag-{n}"` (`n` counts up from 1 per client), then pushes. A push takes the message at
      the head of the queue and gives it to the first consumer, in registration order, that holds fewer
      than `prefetch` unsettled deliveries; it records the delivery as held by that consumer, calls
      `vibey_bootstrap.heartbeat.record_consumer_iteration()`, then awaits `handler(delivery)`. The
      client pushes after every `consume`, every `publish`, every settle and every return to a queue,
      until the queue is empty or no consumer has room. Guard the loop with a per-queue "pushing" flag
      reset in `finally`, so a handler that settles inline does not re-enter it. An exception raised by
      a handler propagates to the caller of the operation that caused the push; the delivery stays
      held (unsettled) by its consumer.
   7. **Delivery contents.** An `InMemoryAmqpDelivery` has the published `body` and `routing_key`;
      `delivery_count` is the number of times the message was returned to this queue (0 for a fresh
      message); `redelivered` is `delivery_count >= 1`; `properties` equals the published properties,
      except that when `delivery_count >= 1` its `headers` also carry `"x-delivery-count": delivery_count`
      (use `dataclasses.replace`).
   8. **`complete()`** removes the message for good.
   9. **`abandon()`** increments the message's count and puts it back at the **head** of its queue. If
      the queue was declared with an integer `x-delivery-limit` and the new count is greater than that
      limit, the message is dead-lettered instead (item 10). With `x-delivery-limit: 1`: the first abandon
      requeues it with count 1; the second dead-letters it.
   10. **`dead_letter()`** sends the message to the exchange named by its queue's
       `x-dead-letter-exchange` argument, with its routing key kept, as a fresh message (count 0) routed
       like a non-mandatory publish (not added to `published`). A queue with no `x-dead-letter-exchange`,
       or a dead-letter exchange that routes nowhere, drops it.
   11. **`simulate_channel_close(tag)`** returns every unsettled delivery that consumer holds to the head
       of its queue, in their original order, each with its count incremented and the delivery limit
       applied as in item 9, then removes the consumer. Those deliveries now count as settled: settling
       one later returns `False`. An unknown tag raises `AmqpError(f"no consumer {tag!r}")`.
   12. **`cancel(tag)`** removes the consumer so nothing more is pushed to it. The deliveries it already
       holds stay unsettled and can still be settled. An unknown tag does nothing.
   13. **`expire(queue)`** raises `AmqpError(f"queue {queue!r} has no x-message-ttl")` for a queue
       declared without `x-message-ttl`. Otherwise it dead-letters every message waiting in that queue
       (not the held ones), head first, as in item 10. Tests call it instead of sleeping.
   14. **`get(queue)`** returns `None` for an empty queue; otherwise it takes the head message and returns
       a delivery held by no consumer (no `record_consumer_iteration()` call). Its settles behave as in
       items 8–10, followed by a push.
   15. **Settling.** Each of `complete`, `abandon` and `dead_letter` returns `False` without doing
       anything when the delivery is already settled (or was returned by item 1 or 11). Otherwise it
       settles, calls `vibey_bootstrap.heartbeat.record_message_settled()`, pushes, and returns `True`.
       The two heartbeat functions are at `vibey_bootstrap/heartbeat/__init__.py:41` and `:51`; child 2's
       real client calls them at the same points.
6. **`__init__.py`** exports `AmqpSettings`, `AmqpProperties`, `AmqpError`, `AmqpPublishError`,
   `AmqpNotConnected`, `AmqpClientInterface`, `AmqpDeliveryInterface` and `InMemoryAmqpClient` in
   `__all__`. Its module docstring states the 10.e reason, verbatim: "The family had no AMQP client; the
   management HTTP API's `get` is a diagnostics endpoint with at-most-once, prefetch-free semantics
   (vibey/infrastructure/bus/rabbitmq.py). ADR-0044 §14."
7. **Packaging.** In `src/vibey_tools/bootstrap/pyproject.toml`, `[tool.setuptools] packages`
   (`:196-250`) gains `"vibey_bootstrap.amqp",` and `"vibey_bootstrap.amqp.interfaces",` directly after
   `"vibey_bootstrap.alerts",` (`:199`). `test/test_packaging.py` fails without them.

## Where to change
- New package `src/vibey_tools/bootstrap/vibey_bootstrap/amqp/`: `__init__.py`, `settings.py`,
  `properties.py`, `errors.py`, `memory.py`, `interfaces/__init__.py`, `interfaces/client_interface.py`.
- `src/vibey_tools/bootstrap/pyproject.toml`: the two `packages` lines only.
- New tests `src/vibey_tools/bootstrap/test/amqp/__init__.py` (the provenance line only),
  `test/amqp/test_settings.py`, `test/amqp/test_memory_client.py`.
- Why more than one source file and one test file: the audit fixed this layout (value types, errors, the
  interface module beside the two classes that implement it, ADR-0016 / 9.b at `doctrines.md:349`), and
  child 2 adds its transport into the same package.
- Copy the Protocol style of `vibey_bootstrap/servicebus/consumer_wrapper.py:26-34`, the package layout
  of `vibey_bootstrap/services/interfaces/` and line 1 (the provenance comment) of any sibling file,
  byte for byte. `AmqpSettings`, `AmqpProperties` and the private records are value types and need no
  interface; the two behaviour classes have theirs in `interfaces/client_interface.py`.

## Acceptance criteria
- [ ] `test/amqp/test_memory_client.py` passes: the in-memory client routes (direct, topic, fanout),
      respects prefetch, counts deliveries, dead-letters at the limit with the routing key, expires TTL
      queues, refuses an unroutable mandatory publish, and settling twice returns `False`.
- [ ] `isinstance(InMemoryAmqpClient(), AmqpClientInterface)` and its deliveries satisfy
      `AmqpDeliveryInterface` (`test_the_client_and_its_deliveries_satisfy_their_interfaces`).
- [ ] `grep -rn "aio_pika" src/vibey_tools/bootstrap/vibey_bootstrap/amqp` prints nothing.
- [ ] `test/test_packaging.py` passes, and the whole tenant suite keeps its 100% line floor
      (`fail_under = 100`, `src/vibey_tools/bootstrap/pyproject.toml:402`).
- [ ] The tenant's static gates pass (its mypy and bandit, below), and root `ruff check` / `ruff format --check` pass.

## Tests to write first (TDD)
All need no service. Async tests are plain `async def test_...` (the tenant sets `asyncio_mode = "auto"`).
A handler in these tests is a small local `async def` that appends each delivery to a list, optionally
settling it.

`src/vibey_tools/bootstrap/test/amqp/test_settings.py`:
- `test_url_scheme_is_required`: `AmqpSettings("http://x")` raises `ValueError`; `amqp://` and `amqps://` URLs build.
- `test_redacted_url_hides_the_password`: `AmqpSettings("amqp://vibey:s3cret@broker:5672/%2F").redacted_url() == "amqp://vibey:***@broker:5672/%2F"`.
- `test_redacted_url_without_a_password_is_unchanged`: `amqp://broker/` and `amqp://vibey@broker/` come back unchanged.

`src/vibey_tools/bootstrap/test/amqp/test_memory_client.py`:
- `test_direct_and_fanout_routing`: a direct exchange delivers only to the queue bound with the equal key; a fanout exchange delivers one copy to each of two bound queues.
- `test_topic_routing_matches_star_and_hash`: `job.*` matches `job.a` but not `job.a.b` or `job`; `*.job.#` matches `w1s.job.a` and `x.job`; `#` matches everything.
- `test_prefetch_bounds_unsettled_pushes`: three messages, `prefetch=2`: the handler receives two; completing one pushes the third; `prefetch=0` raises `ValueError`.
- `test_abandon_requeues_at_head_and_counts`: publish A then B; `get` A, abandon it; the next `get` returns A with `delivery_count == 1`, `redelivered is True` and `properties.headers["x-delivery-count"] == 1`.
- `test_delivery_limit_dead_letters_with_the_routing_key`: a work queue with `{"x-delivery-limit": 1, "x-dead-letter-exchange": "dlx"}` and a queue bound to the topic `dlx` with `#`; abandon twice; the second abandon moves the message to the dead queue with the original routing key and `delivery_count == 0`.
- `test_dead_letter_routes_to_the_dlx`: `dead_letter()` moves the message to the DLX's bound queue with its routing key; on a queue without `x-dead-letter-exchange` it is dropped.
- `test_channel_close_returns_unsettled_deliveries`: a consumer holds two deliveries; `simulate_channel_close(tag)` puts both back at the head in order with count 1; settling either returns `False`; an unknown tag raises `AmqpError`.
- `test_cancel_stops_pushes_but_held_deliveries_still_settle`: after `cancel(tag)` a new publish is not pushed to that handler, and a held delivery's `complete()` returns `True`; `cancel("nope")` does nothing.
- `test_expire_moves_ttl_messages_to_the_dlx`: a queue with `{"x-message-ttl": 1000, "x-dead-letter-exchange": "jobs"}` loses both messages to the queue bound on `jobs`, routing keys kept; `expire` on a queue without TTL raises `AmqpError`.
- `test_unroutable_mandatory_publish_raises`: raises `AmqpPublishError` whose text starts `NO_ROUTE`; with `mandatory=False` it is dropped and recorded in `published`.
- `test_unknown_exchange_or_queue_is_not_found`: publish to an undeclared exchange raises `AmqpPublishError`; `bind`/`consume`/`get` on an undeclared queue raise `AmqpError` starting `NOT_FOUND`.
- `test_redeclaring_with_other_arguments_is_refused`: same arguments is a no-op returning the name; other arguments (and another exchange kind) raise `AmqpError` starting `PRECONDITION_FAILED`; an unknown kind raises `ValueError`; `declare_queue("")` returns `amq.gen-1`, then `amq.gen-2`.
- `test_settling_twice_returns_false`: for each of `complete`, `abandon`, `dead_letter`, the first call returns `True` and a second call on the same delivery returns `False`.
- `test_get_takes_one_message_without_auto_ack`: `get` on an empty queue returns `None`; `get` returns the head message; abandoning it puts it back.
- `test_a_failing_handler_leaves_its_delivery_unsettled`: a handler that raises `RuntimeError` makes `publish` raise it; `simulate_channel_close(tag)` then returns the message to the queue.
- `test_a_closed_client_refuses_work_until_reconnected`: after `close()`, `publish` raises `AmqpNotConnected` and a held delivery is back in its queue; after `connect()`, `get` returns it.
- `test_pushes_and_settles_feed_the_heartbeat`: call `vibey_bootstrap.heartbeat.reset_state()` (the tenant's `test/conftest.py` sets `AZURE_BOOTSTRAP_ALLOW_RESET=1`); after one push and one `complete()`, both `metrics_snapshot()["last_consumer_iteration_age_seconds"]` and `metrics_snapshot()["last_sb_settle_age_seconds"]` are not `None`.
- `test_the_client_and_its_deliveries_satisfy_their_interfaces`: `isinstance` against both Protocols.

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
(cd src/vibey_tools/bootstrap && { .venv/bin/python -m pip show vibey-bootstrap vibey-gh pytest-asyncio mongomock mypy bandit >/dev/null 2>&1 || { .venv/bin/python -m pip install -e ../gh && .venv/bin/python -m pip install -e ".[test,all,dev]"; }; })
# Focused run: a partial run needs --no-cov, because [tool.coverage.report] fail_under = 100 applies to every run
(cd src/vibey_tools/bootstrap && .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov test/amqp test/test_packaging.py)
# The whole tenant suite at its 100% line floor (CI's `test` command, verbatim)
(cd src/vibey_tools/bootstrap && .venv/bin/python -m pytest test/ -m "not integration" --cov=vibey_bootstrap --cov-report=term)
# The tenant's static gates (CI's `static` command, verbatim)
(cd src/vibey_tools/bootstrap && .venv/bin/python -m mypy vibey_bootstrap/ && .venv/bin/python -m bandit -r vibey_bootstrap/ -ll -q)
! grep -rn "aio_pika" src/vibey_tools/bootstrap/vibey_bootstrap/amqp
git diff --stat
```

## Out of scope
- The aio-pika transport (child 2, `split-351-2-amqp-client`) and anything that imports `aio_pika`.
- The default exchange `""`, `x-dead-letter-routing-key`, `x-overflow`, queue depth, consumer count,
  exclusive consume, the exclusive-queue lease and unconfirmed publish (ADR-0046 L21, ADR-0045 T21,
  ADR-0047 S07 and the topology lane #359).
- Anything under `src/vibey/`; the tenant's `vibey_bootstrap/__init__.py`; `test/test_all_extras_import.py`.
- CHANGELOG.md (root and tenant), docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push or change remotes. Commit locally with the Title as the subject.

## Standing constraints
### Lane card
- **Wave:** 1. It imports no `aio_pika`, so it needs no dependency lane.
- **Files touched:** `vibey_bootstrap/amqp/{__init__,settings,properties,errors,memory}.py` (new),
  `vibey_bootstrap/amqp/interfaces/{__init__,client_interface}.py` (new), `pyproject.toml` (two
  `packages` lines), `test/amqp/{__init__,test_settings,test_memory_client}.py` (new), all under
  `src/vibey_tools/bootstrap/`.
- **Must keep passing unchanged:** the whole vibey-bootstrap suite, the root suite, all protected tests.

### For every RabbitMQ lane
- **Protected tests are never edited:** `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`,
  `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`
  (`.vibey-gh.toml`, `.github/CODEOWNERS`). They must keep passing.
- **The first line of every new source file** is the provenance comment, copied byte-for-byte from line 1
  of a sibling file (`vibey-gh check` compares it exactly).
- **The default run needs no outside service.** Tests against a real broker are marked `integration` and
  skip unless `VIBEY_TEST_AMQP_URL` is set. (This lane has none.)
- **Substitution at a declared seam only:** constructor or keyword injection; never
  `monkeypatch.setattr` on a module attribute, `mock.patch`, `MagicMock` or `AsyncMock`.
- **Defaults stay today's until #381 (R34):** `queue.backend = "postgres"` and
  `engines.invocation = "subprocess"`.
- Arch Linux and macOS both: the commands above use only `python3`, `pip` and `uv`, which exist on both.

**Depends on:** none
- none: the lane imports nothing new; the tenant's existing `heartbeat` module is all it uses.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
