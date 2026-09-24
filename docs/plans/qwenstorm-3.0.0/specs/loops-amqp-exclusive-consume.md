## Title
feat(bootstrap): vibey_bootstrap.amqp consumes exclusively and names a refusal (AmqpExclusiveConsumerRefused)

ADR-0046 lane L21b (slug `loops-amqp-exclusive-consume`).

## Why
Draft ADR-0046 §3 (`specs/ADR-two-loops.md:155`): "8.c is enforced by the broker, per model …
Every seat queue is consumed by exactly one **seat host** with an *exclusive* consumer, so a
second instance for the same model is refused at the broker and exits with an 8.c message. Each
loop's **router** consumes its intake queue exclusively too." Security impact (`:390`): "The
exclusive intake consumer stops a rogue second instance from draining a loop's queue."
Non-negotiable 5 (`:337`) teaches the capability to `vibey_bootstrap.amqp` (10.e,
`src/vibey_tools/gh/docs/doctrines.md:417`); sub-doctrine 8.c (`doctrines.md:196`) is the rule it
enforces. *Verification owed* V-AMQP1 (`:460`): "A quorum queue refuses a second consumer when
the first holds `exclusive=True`. Lane L21; integration test against the pinned
`rabbitmq:4-management-alpine`." This lane owns that test.

At integration `d3b4a388` `vibey_bootstrap.amqp` does not exist; lane `split-351-2-amqp-client`
(split into `split-351-1-amqp-contract`, which adds `memory.py`, `errors.py` and the interfaces,
and `split-351-2-amqp-client`, which adds `client.py`) brings a `consume(queue, *, prefetch, handler)`
with no way to ask for exclusivity and no way to tell a refusal from any other channel error.
Lane `loops-amqp-queue-depth` (the same three files) lands first; this lane follows the same T21
layout (`specs/test-harness-lanes.md`, "Lane T21").

## Required behaviour
1. **`errors.py`** gains:
   ```python
   class AmqpExclusiveConsumerRefused(AmqpError):
       """The broker refused a consumer because of exclusivity: the queue is already consumed
       exclusively, or an exclusive consumer was asked for while another consumer exists
       (AMQP ACCESS_REFUSED 403, or RESOURCE_LOCKED 405). ADR-0046 §3 turns it into
       sub-doctrine 8.c's single instance per model."""

       def __init__(self, queue: str) -> None:
           super().__init__(
               f"queue {queue!r} refused the consumer: it is, or would be, consumed exclusively"
           )
           self.queue = queue
   ```
   and `vibey_bootstrap.amqp`'s `__init__.py` exports it (import and `__all__`).
2. **`AmqpClientInterface.consume`** becomes
   `async def consume(self, queue: str, *, prefetch: int, handler: Callable[[AmqpDeliveryInterface], Awaitable[None]], exclusive: bool = False) -> str`;
   its docstring says: with `exclusive=True` no other consumer may consume `queue` while this one
   is active, and a refusal raises `AmqpExclusiveConsumerRefused`.
3. **`AmqpClient.consume`** passes `exclusive=exclusive` to aio-pika's `queue.consume(callback, exclusive=...)`.
   When the broker refuses — aiormq's `ChannelAccessRefused` or `ChannelLockedResource`
   (`from aiormq.exceptions import ChannelAccessRefused, ChannelLockedResource`; aio-pika raises
   aiormq's channel errors) — it closes that consumer's dedicated channel (ignoring
   `aio_pika.exceptions.ChannelInvalidStateError` and `aio_pika.exceptions.AMQPError`, since the
   broker already closed it), records no tag, and raises `AmqpExclusiveConsumerRefused(queue)`
   `from` the broker's error. The default (`exclusive=False`) path is unchanged byte for byte.
4. **`InMemoryAmqpClient.consume`** takes the same keyword and models the broker:
   - `exclusive=True` on a queue that has any active consumer raises
     `AmqpExclusiveConsumerRefused(queue)`;
   - any consumer on a queue that has an active exclusive consumer raises it too;
   - a refused call registers nothing and pushes nothing;
   - `cancel(tag)` or `simulate_channel_close(tag)` of the exclusive consumer frees the queue
     (its unsettled deliveries go back as today).
   Record the flag with the per-consumer record split-351-1 keeps.
5. Every existing call and test of `consume` (which never passes `exclusive`) behaves as before;
   every test under `src/vibey_tools/bootstrap/test/amqp/` passes unedited.

## Where to change
Read `STORM/EDITING-RULES.md` first; `memory.py` and
`client.py` are long, so `edit_file` only. Source paths are under
`src/vibey_tools/bootstrap/vibey_bootstrap/amqp/`, test paths under
`src/vibey_tools/bootstrap/test/amqp/`.
- `errors.py`, `__init__.py`: behaviour 1.
- `interfaces/client_interface.py`: behaviour 2 (the signature and docstring of `consume` only).
- `client.py`: behaviour 3, inside `consume`, around its `await q.consume(...)` call.
- `memory.py`: behaviour 4, inside `consume` (and nothing else: `cancel` and
  `simulate_channel_close` already remove the consumer record, which is what frees the queue).
- Before editing, run `grep -rn "AmqpClientInterface" src/vibey_tools src/vibey tests`: every class
  that implements it must accept `exclusive`. If one exists outside `client.py` and `memory.py`,
  stop and report. If the tenant registry `src/vibey_tools/bootstrap/test/fakes/registry.py`
  exists, keep `InMemoryAmqpClient` registered.
- Tests: append to `test_memory_client.py`, `test_client_unit.py` and `test_client_integration.py`.
  In `test_client_unit.py`, give the fake queue's `consume` an `exclusive=False` keyword it
  records, and a settable exception it raises instead of returning a tag; give the fake channel a
  `close()` that records the call if T21's temporary channel did not already add one.

## Acceptance criteria
- [ ] In memory: an exclusive consumer refuses every other consumer, exclusive or not; an
      exclusive consumer is refused beside an existing one; cancelling or closing the exclusive
      one frees the queue; a refused call receives nothing.
- [ ] Unit (fake connector): `exclusive` reaches `queue.consume`; both aiormq refusals become
      `AmqpExclusiveConsumerRefused` naming the queue, the channel's close was attempted, and the
      tag was never recorded (`cancel(tag)` of it does nothing).
- [ ] Integration (V-AMQP1, `@pytest.mark.integration`, skipped without `VIBEY_TEST_AMQP_URL`)
      against the pinned `rabbitmq:4-management-alpine`, on a quorum queue.
- [ ] `grep -nE "monkeypatch|mock\.patch|MagicMock|AsyncMock" src/vibey_tools/bootstrap/test/amqp/*.py` prints nothing.
- [ ] The whole tenant suite keeps its 100% line floor; the tenant's mypy and bandit pass.

## Tests to write first (TDD)
- `test_memory_client.py`:
  - `test_an_exclusive_consumer_refuses_every_other_consumer`: `consume(q, prefetch=1, handler=h, exclusive=True)`
    returns a tag; `consume(q, prefetch=1, handler=h)` and `consume(q, prefetch=1, handler=h, exclusive=True)`
    each raise `AmqpExclusiveConsumerRefused` with `.queue == q`.
  - `test_an_exclusive_consumer_is_refused_beside_an_existing_one`: after a plain consumer,
    `exclusive=True` raises; a second plain consumer still succeeds.
  - `test_cancelling_or_closing_the_exclusive_consumer_frees_the_queue`: after `cancel(tag)` a new
    exclusive consumer succeeds; after `simulate_channel_close(tag2)` a plain one succeeds.
  - `test_a_refused_consumer_receives_nothing`: publish two messages after a refusal; only the
    exclusive consumer's handler saw them.
  - `test_the_refusal_is_an_amqp_error_naming_the_queue`: `isinstance(exc, AmqpError)` and
    `str(exc) == "queue 'q' refused the consumer: it is, or would be, consumed exclusively"`;
    `from vibey_bootstrap.amqp import AmqpExclusiveConsumerRefused` works.
- `test_client_unit.py`:
  - `test_consume_passes_exclusive_to_the_broker`: the fake queue recorded `exclusive=True` for an
    exclusive call and `exclusive=False` for a plain one.
  - `test_a_broker_refusal_becomes_amqp_exclusive_consumer_refused` (parametrized over
    `aiormq.exceptions.ChannelAccessRefused("ACCESS_REFUSED")` and
    `aiormq.exceptions.ChannelLockedResource("RESOURCE_LOCKED")`): `consume` raises
    `AmqpExclusiveConsumerRefused` whose `__cause__` is the broker's error; the dedicated channel's
    `close()` was called; no tag was recorded.
- `test_client_integration.py` (under the module's existing `pytestmark`):
  - `test_a_quorum_queue_refuses_a_second_consumer_beside_an_exclusive_one`: `suffix = uuid4().hex[:8]`;
    client A declares `f"vibey.test.exclusive.{suffix}"` with
    `{"x-queue-type": "quorum", "x-expires": 600000}` and consumes it with `exclusive=True`; a
    second `AmqpClient` B (its own connection) calling `consume` on it, plain and exclusive, raises
    `AmqpExclusiveConsumerRefused` each time (a fresh B for each attempt: a refusal closes B's
    channel); after A cancels its tag, a fresh B consumes with `exclusive=True`; then that B's
    exclusive consumer makes A's plain `consume` raise. `close()` every client in `finally`.
    **If the broker disagrees (for example, a quorum queue accepts the second consumer), do not
    change the assertion: stop and report the observed behaviour** (that is V-AMQP1's evidence).

## Checks the lane must run (all must pass)
First run `uv run ruff format src/vibey_tools/bootstrap/vibey_bootstrap/amqp src/vibey_tools/bootstrap/test/amqp`.

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
# The real broker (V-AMQP1), only when one is configured
(cd src/vibey_tools/bootstrap && if [ -n "${VIBEY_TEST_AMQP_URL:-}" ]; then .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov -m integration test/amqp/test_client_integration.py; fi)
# The whole tenant suite at its 100% line floor (CI's `test` command, verbatim)
(cd src/vibey_tools/bootstrap && .venv/bin/python -m pytest test/ -m "not integration" --cov=vibey_bootstrap --cov-report=term)
# The tenant's static gates (CI's `static` command, verbatim)
(cd src/vibey_tools/bootstrap && .venv/bin/python -m mypy vibey_bootstrap/ && .venv/bin/python -m bandit -r vibey_bootstrap/ -ll -q)
! grep -nE "monkeypatch|mock\.patch|MagicMock|AsyncMock" src/vibey_tools/bootstrap/test/amqp/*.py
git diff --stat
```

## Out of scope
- `LoopInstanceRefused` and the 8.c exit (lanes `loops-seat-host-core`, `loops-router-routing`,
  `loops-cli-loop-service`); single-active-consumer (`surfaces-amqp-queue-limits`).
- Anything under `src/vibey/`; `pyproject.toml` (aiormq comes with aio-pika, lane
  `rmq-r03-amqp-dependency`); the tenant's CHANGELOG.
- Protected tests: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`,
  `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.
- Do not push, open PRs or change remotes. Commit locally with the Title as the subject.

**Depends on:** `loops-amqp-queue-depth`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
