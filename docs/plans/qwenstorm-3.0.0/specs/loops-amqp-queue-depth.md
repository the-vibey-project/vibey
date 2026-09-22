## Title
feat(bootstrap): vibey_bootstrap.amqp can say how many messages wait in a queue

ADR-0046 lane L21a (slug `loops-amqp-queue-depth`).

## Why
Draft ADR-0046 §4, "Backlog" (`specs/ADR-two-loops.md:214`): "The depth of each seat comes from a
passive queue declare, added to the family client (10.e, lane L21)." sovereignloop's residency
schedule switches models only on evidence of waiting work, and its router reports each seat's
depth in `RunRouted` and `LoopRouted` (sub-doctrine 8.g, `src/vibey_tools/gh/docs/doctrines.md:316-324`:
every queue reports its depth). Non-negotiable 5 (`:337`): "AMQP goes through
`vibey_bootstrap.amqp`, and the two capabilities it lacked (queue depth, exclusive consume) are
taught to it." Sub-doctrine 10.e (`doctrines.md:417`) closes a family gap in the family. ADR-0046
*Verification owed* V-AMQP2 (`:461`): "A passive `queue.declare` returns `message_count` for a
quorum queue, via aio-pika's `declaration_result.message_count`." This lane owns that test.

At integration `d3b4a388` `vibey_bootstrap.amqp` does not exist yet: it arrives with lane
`split-351-2-amqp-client` (#351, split into `split-351-1-amqp-contract` — the contract, the value
types and `InMemoryAmqpClient` in `memory.py` — and `split-351-2-amqp-client` — `AmqpClient` in
`client.py` and `AmqpDelivery` in `delivery.py`). Lane `harness-T21-amqp-consumer-count`
(`specs/test-harness-lanes.md`, "Lane T21") then adds `consumer_count(queue)` by a passive declare
on a temporary channel. This lane is T21's twin and follows its structure exactly: the same three
source files, the same three test modules, a message count instead of a consumer count.

## Required behaviour
1. **`AmqpClientInterface.queue_depth(self, queue: str) -> int | None`** (async), declared in
   `vibey_bootstrap/amqp/interfaces/client_interface.py` right after T21's `consumer_count`:
   ```python
       async def queue_depth(self, queue: str) -> int | None:
           """How many messages are ready in `queue` (delivered-but-unsettled ones excluded),
           by a passive declare; None when the queue does not exist (ADR-0046 §4)."""
           ...
   ```
2. **`AmqpClient.queue_depth(queue)`** in `client.py` is a copy of T21's `consumer_count` with one
   difference, the attribute read:
   1. it connects lazily, and on a closed client raises
      `AmqpNotConnected("AmqpClient is closed; call connect() first")`, as every other method does;
   2. it opens a **temporary** channel on the connection;
   3. `q = await channel.declare_queue(queue, passive=True)`;
   4. it returns `q.declaration_result.message_count`;
   5. a missing queue (`aio_pika.exceptions.ChannelNotFoundEntity`) returns `None`;
   6. it always closes the temporary channel, ignoring one the broker already closed, exactly as
      `consumer_count` does.
   A passive declare never creates, changes or deletes a queue.
3. **`InMemoryAmqpClient.queue_depth(queue)`** in `memory.py` returns the number of **ready**
   messages of a declared queue — in the queue and not currently delivered-and-unsettled — and
   `None` for a queue never declared (or deleted). A `get()` without settling lowers it by one; an
   `abandon()` of that delivery raises it again; a `complete()` does not. It is the same count
   RabbitMQ reports in `message_count`. If lane `surfaces-amqp-queue-limits` has already added a
   ready-count helper to `memory.py`, use it rather than counting a second way.
4. No other method changes. Every existing test under `src/vibey_tools/bootstrap/test/amqp/`
   passes unedited.

## Where to change
Read `/private/tmp/claude-501/storm/qwenstorm-3.0.0/EDITING-RULES.md` first; `memory.py` and
`client.py` are long, so change them with `edit_file` only. All source paths are under
`src/vibey_tools/bootstrap/vibey_bootstrap/amqp/`, all test paths under
`src/vibey_tools/bootstrap/test/amqp/`.
- `interfaces/client_interface.py`: behaviour 1.
- `client.py`: `queue_depth` directly after `consumer_count`, written as its copy (behaviour 2).
  Read `consumer_count` first and reuse its temporary-channel open/close and its not-found
  handling line for line; do not refactor `consumer_count`.
- `memory.py`: `queue_depth` directly after `consumer_count` (behaviour 3), reading the
  per-queue message list split-351-1 keeps.
- Before editing, run `grep -rn "AmqpClientInterface" src/vibey_tools src/vibey tests`: every class
  that claims to implement it must gain `queue_depth`. If one exists outside `client.py` and
  `memory.py`, stop and report. If `src/vibey_tools/bootstrap/test/fakes/registry.py` exists
  (lane `fakes-tenant-bootstrap-3`), keep `InMemoryAmqpClient` registered; its parity test checks
  the new signature against the interface.
- Tests: append to `test_memory_client.py`, `test_client_unit.py` and `test_client_integration.py`
  (append only; never rewrite a test file). In `test_client_unit.py`, extend the fake that T21
  gave a passive declare (its fake queue's `declaration_result`) with a scripted `message_count`
  beside `consumer_count`; add nothing else to the fakes.

## Acceptance criteria
- [ ] In memory: an undeclared queue gives `None`; a declared empty one `0`; three published
      messages `3`; after one `get()` without settling `2`; after `abandon()` of it `3`; after a
      second `get()` and `complete()` `2`.
- [ ] Unit (fake connector, no network): the passive declare happens on its own new channel, which
      is then closed; `ChannelNotFoundEntity` maps to `None` and the channel is still closed; a
      closed client raises `AmqpNotConnected`.
- [ ] Integration (V-AMQP2, `@pytest.mark.integration`, skipped without `VIBEY_TEST_AMQP_URL`):
      against the pinned `rabbitmq:4-management-alpine`, a quorum queue's depth follows real
      publishes and excludes an unacknowledged `get`.
- [ ] `grep -nE "monkeypatch|mock\.patch|MagicMock|AsyncMock" src/vibey_tools/bootstrap/test/amqp/*.py` prints nothing.
- [ ] The whole tenant suite keeps its 100% line floor; the tenant's mypy and bandit pass.

## Tests to write first (TDD)
- `test_memory_client.py`:
  - `test_queue_depth_counts_ready_messages_only`: declare a direct exchange and a queue bound to
    it; the sequence and values of the first acceptance item.
  - `test_queue_depth_of_an_undeclared_queue_is_none`.
- `test_client_unit.py`:
  - `test_queue_depth_uses_a_passive_declare_on_its_own_channel`: after `connect()`, the fake
    connection opened one more channel; that channel's `declare_queue` got `passive=True`; the
    result is the scripted `message_count` (7); the channel was closed.
  - `test_queue_depth_of_a_missing_queue_is_none`: the passive declare raises
    `aio_pika.exceptions.ChannelNotFoundEntity("NOT_FOUND")` → `None`, and the channel's close was
    attempted.
  - `test_queue_depth_on_a_closed_client_refuses`: after `close()`, `pytest.raises(AmqpNotConnected)`.
- `test_client_integration.py` (under the module's existing `pytestmark`):
  - `test_queue_depth_against_a_real_broker`: `suffix = uuid4().hex[:8]`; declare the direct
    exchange `vibey.test.amqp.depth`, and the queue `f"vibey.test.depth.{suffix}"` with
    `{"x-queue-type": "quorum", "x-expires": 600000}` bound to it on `f"d.{suffix}"`; publish three
    messages; poll `queue_depth` every 0.1 s for up to 5 s until it is 3; `get()` one without
    settling → poll until 2; `abandon()` it → poll until 3;
    `queue_depth(f"vibey.test.absent.{suffix}")` is `None`; `close()` in `finally`.
    **If the broker disagrees with an assertion, do not change the assertion: stop and report the
    observed values** (that is V-AMQP2's evidence).

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
# The real broker (V-AMQP2), only when one is configured
(cd src/vibey_tools/bootstrap && if [ -n "${VIBEY_TEST_AMQP_URL:-}" ]; then .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov -m integration test/amqp/test_client_integration.py; fi)
# The whole tenant suite at its 100% line floor (CI's `test` command, verbatim)
(cd src/vibey_tools/bootstrap && .venv/bin/python -m pytest test/ -m "not integration" --cov=vibey_bootstrap --cov-report=term)
# The tenant's static gates (CI's `static` command, verbatim)
(cd src/vibey_tools/bootstrap && .venv/bin/python -m mypy vibey_bootstrap/ && .venv/bin/python -m bandit -r vibey_bootstrap/ -ll -q)
! grep -nE "monkeypatch|mock\.patch|MagicMock|AsyncMock" src/vibey_tools/bootstrap/test/amqp/*.py
git diff --stat
```

## Out of scope
- Exclusive consume (lane `loops-amqp-exclusive-consume`); consumer count (T21); queue-length
  limits and publish modes (the `surfaces-amqp-*` lanes).
- Anything under `src/vibey/` (the router and scheduler that call it are the loop-service lanes).
- `pyproject.toml` (no new package, no new dependency) and the tenant's CHANGELOG.
- Protected tests: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`,
  `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.
- Do not push, open PRs or change remotes. Commit locally with the Title as the subject.

**Depends on:** `split-351-2-amqp-client`, `harness-T21-amqp-consumer-count`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
