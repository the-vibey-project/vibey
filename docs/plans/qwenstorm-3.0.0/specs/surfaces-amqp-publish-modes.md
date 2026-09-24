## Title
feat(bootstrap): vibey_bootstrap.amqp publishes without waiting for a confirm, and to the default exchange

## Why
Draft ADR-0047 (`specs/ADR-surface-lanes.md` §4, §6, §10, §12) sends every surface **read** as a
transient message to a classic queue **without waiting for a publisher confirm**, and every
answer back on the caller's server-named reply queue named in `reply_to`. A reply to
`reply_to` is a publish to the AMQP **default exchange** (`""`), which routes by queue name.

`vibey_bootstrap.amqp` (lane `split-351-1-amqp-contract`, #351, and its child 2, the aio-pika
`AmqpClient`, `issue-audit/updates/351.md` "Proposed child lanes" 2) offers neither: every
`publish` waits for the confirm, and neither child names the default exchange. Sub-doctrine
10.e (`src/vibey_tools/gh/docs/doctrines.md`, "family first") says a gap is closed by teaching
the family. This is ADR-0047 lane S07, part 1 of 3 (the lease is `surfaces-amqp-lease-memory`
and `surfaces-amqp-lease-client`).

## Required behaviour
1. **`AmqpClientInterface.publish`** (`vibey_bootstrap/amqp/interfaces/client_interface.py`)
   becomes
   `async def publish(self, exchange: str, routing_key: str, body: bytes, properties: AmqpProperties, *, mandatory: bool = True, confirm: bool = True) -> None`.
   Its docstring adds: "`confirm=False` returns once the frame is handed to the connection and
   never reports routing; it requires `mandatory=False`. `exchange=""` is the AMQP default
   exchange, which routes to the queue named `routing_key`."
2. **Both implementations** raise
   `ValueError("an unconfirmed publish cannot be mandatory: a return would arrive after the call returned")`
   when `confirm=False` and `mandatory=True`, before anything is sent or recorded.
3. **`InMemoryAmqpClient`** (`vibey_bootstrap/amqp/memory.py`):
   - `exchange == ""` routes to the declared queue whose name equals `routing_key`, and to
     nothing else. Declaring an exchange named `""` is not needed and not allowed
     (`declare_exchange("")` raises `AmqpError("the default exchange cannot be declared")`).
   - `confirm=True` keeps today's behaviour: an unroutable mandatory publish raises
     `AmqpPublishError`.
   - `confirm=False`: the publish is appended to `published` as today. If it routes to no
     queue, it is also appended to a new public list `dropped:
     list[tuple[str, str, bytes, AmqpProperties]]` and nothing is raised.
4. **`AmqpClient`** (`vibey_bootstrap/amqp/client.py`, child 2):
   - on the first unconfirmed publish it opens, and keeps, a second channel
     `await connection.channel(publisher_confirms=False)`. `close()` closes it too, ignoring
     an already-closed channel.
   - `confirm=False` publishes on that channel with `mandatory=False` and returns without
     waiting for anything.
   - `exchange == ""` uses `channel.default_exchange` (on whichever channel the publish
     uses); any other name is resolved exactly as the confirmed path resolves it today.
   - The confirmed path (`confirm=True`) is unchanged apart from accepting `""`.
5. Nothing else in the package changes. Every existing R04 and T21 test passes unchanged.

## Where to change
- `src/vibey_tools/bootstrap/vibey_bootstrap/amqp/interfaces/client_interface.py` (the
  `publish` signature and docstring).
- `src/vibey_tools/bootstrap/vibey_bootstrap/amqp/memory.py` (`publish`, `declare_exchange`,
  the new `dropped` list initialised in `__init__`).
- `src/vibey_tools/bootstrap/vibey_bootstrap/amqp/client.py` (`publish`, `close`).
- Tests: append to `src/vibey_tools/bootstrap/test/amqp/test_memory_client.py` and to
  `src/vibey_tools/bootstrap/test/amqp/test_client_unit.py` (reuse the fake connector,
  channel and exchange classes child 2 wrote in that module; give the fake channel a
  `default_exchange` attribute and a `publisher_confirms` record if it has none).

## Acceptance criteria
- [ ] In memory, a publish to `""` with key `q` lands in queue `q`; with key `nope` it raises (confirmed) or lands in `dropped` (unconfirmed).
- [ ] `confirm=False, mandatory=True` raises `ValueError` in both clients and records nothing.
- [ ] Against the fake connector, an unconfirmed publish opens exactly one extra channel with `publisher_confirms=False`, uses it for every later unconfirmed publish, and awaits no confirm.
- [ ] `isinstance(InMemoryAmqpClient(), AmqpClientInterface)`; `mypy` accepts both classes against the interface.
- [ ] The tenant's whole suite keeps its 100% line floor and its static gates pass.

## Tests to write first (TDD)
Append to `test/amqp/test_memory_client.py`:
- `test_default_exchange_routes_by_queue_name`
- `test_unconfirmed_unroutable_publish_is_dropped_not_raised`
- `test_unconfirmed_mandatory_publish_is_refused`
- `test_the_default_exchange_cannot_be_declared`
Append to `test/amqp/test_client_unit.py`:
- `test_unconfirmed_publish_uses_one_extra_channel_without_confirms`
- `test_default_exchange_publish_uses_the_channel_default_exchange`
- `test_unconfirmed_mandatory_publish_is_refused_before_connecting`
- `test_close_closes_the_unconfirmed_channel`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    (cd src/vibey_tools/bootstrap && uv run python -m pytest -q -p no:cacheprovider --no-cov test/amqp)
    (cd src/vibey_tools/bootstrap && uv run python -m pytest -q -p no:cacheprovider test/ -m "not integration")
    (cd src/vibey_tools/bootstrap && uv run python -m mypy vibey_bootstrap/ && uv run python -m bandit -r vibey_bootstrap/ -ll -q)
    uv run lint-imports

The second command is the whole tenant suite, whose `addopts` enforce the 100% line floor; a
partial run needs `--no-cov`. Formatting is the root `ruff format`; do not run black here.

## Out of scope
- The lease (`surfaces-amqp-lease-memory`, `surfaces-amqp-lease-client`), queue length and
  single-active-consumer semantics in memory (`surfaces-amqp-queue-limits`).
- `inspect_queue` (owned by ADR-0045's `harness-T21a-amqp-consumer-count-client` and
  `harness-T21-amqp-consumer-count`, see `surfaces-lane-meter`) and exclusive consume
  (ADR-0046 lane L21, `loops-queue-depth`).
- Anything under `src/vibey/`. CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and
  the skill trees (`surfaces-docs-wave`). Do not push, open PRs or change remotes. Commit
  locally with the Title as the subject.

## Lane card
- **Depends on:** `split-351-1-amqp-contract` (#351, child 1: the interfaces and
  `InMemoryAmqpClient`) and `split-351-2-amqp-client` (#351 child 2, the aio-pika
  `AmqpClient`; `specs/split-queue.txt`).
- **Shares a file with:** `memory.py`, `client.py` and `client_interface.py` are also extended
  by ADR-0045 T21 (`inspect_queue`) and ADR-0046 L21 (exclusive consume). The storm runs one
  lane at a time; keep every method the earlier lanes added.
- **Must keep passing unchanged:** every R04, R04-child-2 and T21 test; the whole
  vibey-bootstrap suite; the root suite; all protected tests.
- **Standing constraints (every vibey-bootstrap surfaces lane):**
  - Read `STORM/EDITING-RULES.md` first. Change
    existing files with `edit_file` or a checked replacement; append tests, never rewrite a
    test file.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from a sibling.
  - Every new class has a `@runtime_checkable` Protocol in the package's `interfaces/`.
  - No `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`: fakes are small
    classes injected through the constructor (`connector=`).
  - The default run needs no broker: a real-broker test is `@pytest.mark.integration` and
    skips unless `VIBEY_TEST_AMQP_URL` is set.
  - If `src/vibey_tools/bootstrap/test/fakes/registry.py` exists when the lane starts,
    register every new in-memory class there; otherwise do nothing about a registry.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
