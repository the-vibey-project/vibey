## Title
feat(bootstrap): AmqpLeases takes an exclusive-queue lease on its own non-robust connection

## Why
Draft ADR-0047 §1 (`specs/ADR-surface-lanes.md`): a surface lane owns its surface by owning
the exclusive, auto-delete queue `<prefix>.surface.<name>.lock`. A second connection that
declares it is refused with `RESOURCE_LOCKED` (reply code 405), and the broker deletes the
queue when the owner's connection closes. **When the connection is lost, the lane exits and
does not reclaim its lease** ("An exclusive lease that reconnects silently" is rejected under
*Alternatives*).

aio-pika's robust connection re-declares every queue it declared when it reconnects. A lease on
the robust connection that `AmqpClient` shares (child 2 of #351) could therefore be re-taken
silently after a network blip, which is a second instance however briefly. So the lease uses
**its own plain (non-robust) connection**: nothing reconnects it, and its close callback is the
loss signal. `surfaces-amqp-lease-memory` declared `AmqpLeasesInterface`; this lane implements
it over aio-pika (ADR-0047 lane S07, part 3; sub-doctrine 10.e).

## Required behaviour
1. **`vibey_bootstrap/amqp/lease.py`** (new):
   - `class AmqpLeases` (implements `AmqpLeasesInterface`):
     `__init__(self, settings: AmqpSettings, *, connector: Callable[..., Awaitable[aio_pika.abc.AbstractConnection]] = aio_pika.connect)`.
     `aio_pika.connect` is the **non-robust** connector; the docstring says why (the paragraph
     above, in two sentences).
   - `async acquire_exclusive(self, name: str) -> AmqpLease | None`:
     1. an empty `name` raises `ValueError("a lease needs a name")`;
     2. `connection = await self._connector(self._settings.url, client_properties={"connection_name": f"{self._settings.connection_name}.lease.{name}"}, heartbeat=self._settings.heartbeat_seconds)`;
     3. `channel = await connection.channel()`;
     4. `await channel.declare_queue(name, exclusive=True, auto_delete=True, durable=False)`;
     5. if that raises `aiormq.exceptions.ChannelLockedResource` (reply code 405,
        `RESOURCE_LOCKED`): `await connection.close()` and return `None`;
     6. any other exception: close the connection (ignoring a close error) and raise
        `AmqpError(f"could not take the lease {name!r}: {exc}")` from it;
     7. otherwise return `AmqpLease(name, connection)` and remember it.
   - `async close(self) -> None` releases every lease it returned that is still held.
2. **`class AmqpLease`** (implements `AmqpLeaseInterface`):
   - on construction it registers a close callback: `connection.close_callbacks.add(self._on_close)`.
     `_on_close(self, sender: object, exc: BaseException | None) -> None` marks the lease lost
     and sets its `asyncio.Event`, **unless** the lease was released first.
   - `release()` marks it released, then `await connection.close()`; a second call is a no-op.
   - `is_lost()` and `wait_lost()` read the event, as the in-memory lease does.
3. **Exports.** `vibey_bootstrap/amqp/__init__.py` exports `AmqpLeases` and `AmqpLease`.
4. **Verify the exception name first.** Before writing, run
   `uv run python -c "import aiormq.exceptions as e; print(e.ChannelLockedResource.__mro__)"`.
   If the class does not exist, stop and report; do not guess another name.

## Where to change
- New `src/vibey_tools/bootstrap/vibey_bootstrap/amqp/lease.py`.
- `src/vibey_tools/bootstrap/vibey_bootstrap/amqp/__init__.py` (exports only).
- New `src/vibey_tools/bootstrap/test/amqp/test_lease_unit.py` and
  `src/vibey_tools/bootstrap/test/amqp/test_lease_integration.py`.

## Acceptance criteria
- [ ] Against a fake connector (classes in the test module), a successful acquire declares `name` exclusive, auto-delete, not durable, on a connection named `<connection_name>.lease.<name>`.
- [ ] A fake channel that raises `ChannelLockedResource` makes `acquire_exclusive` return `None` and close its connection.
- [ ] Any other declare error closes the connection and raises `AmqpError` naming the lease.
- [ ] Calling the registered close callback marks the lease lost and wakes `wait_lost()`; after `release()` the same callback does not.
- [ ] Integration (`VIBEY_TEST_AMQP_URL`, pinned `rabbitmq:4-management-alpine`): a second `AmqpLeases` gets `None` while the first holds the name, and succeeds once the first releases. This is the ADR's first *Verification owed* item.
- [ ] 100% line coverage of `lease.py` from the unit tests alone; mypy and bandit pass.

## Tests to write first (TDD)
`test/amqp/test_lease_unit.py` (no service; fake connector, connection with `channel()`, `close()` and a `close_callbacks` set, and a channel whose `declare_queue` can raise on cue — all small classes in the module):
- `test_acquire_declares_an_exclusive_auto_delete_queue_on_its_own_connection`
- `test_a_locked_name_returns_none_and_closes_the_connection`
- `test_another_declare_error_is_an_amqp_error_naming_the_lease`
- `test_a_closed_connection_marks_the_lease_lost`
- `test_release_is_idempotent_and_is_not_a_loss`
- `test_close_releases_every_held_lease`
- `test_an_empty_name_is_refused`
`test/amqp/test_lease_integration.py` (`@pytest.mark.integration`, skipped without `VIBEY_TEST_AMQP_URL`):
- `test_a_second_holder_is_refused_until_the_first_releases`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    (cd src/vibey_tools/bootstrap && uv run python -m pytest -q -p no:cacheprovider --no-cov test/amqp)
    (cd src/vibey_tools/bootstrap && uv run python -m pytest -q -p no:cacheprovider test/ -m "not integration")
    (cd src/vibey_tools/bootstrap && uv run python -m mypy vibey_bootstrap/ && uv run python -m bandit -r vibey_bootstrap/ -ll -q)
    # When a broker is available (record in the commit body whether it ran):
    (cd src/vibey_tools/bootstrap && VIBEY_TEST_AMQP_URL="$VIBEY_TEST_AMQP_URL" uv run python -m pytest -q -p no:cacheprovider --no-cov -m integration test/amqp/test_lease_integration.py)

## Out of scope
- Changing `AmqpClient` or the robust connection it shares. Anything under `src/vibey/`.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees
  (`surfaces-docs-wave`). Do not push, open PRs or change remotes. Commit locally with the
  Title as the subject.

## Lane card
- **Depends on:** `surfaces-amqp-lease-memory` (the interface), `rmq-r03-amqp-dependency` (aio-pika locked), `split-351-2-amqp-client` (#351 child 2: `AmqpSettings` in use, `AmqpError` exported).
- **Must keep passing unchanged:** every existing vibey-bootstrap test; all protected root tests.
- **Standing constraints (every vibey-bootstrap surfaces lane):**
  - Read `/private/tmp/claude-501/storm/qwenstorm-3.0.0/EDITING-RULES.md` first.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from a sibling.
  - No `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`: the connector is injected.
  - The default run needs no broker.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
