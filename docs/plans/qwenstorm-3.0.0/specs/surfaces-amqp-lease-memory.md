## Title
feat(bootstrap): vibey_bootstrap.amqp declares an exclusive lease, with an in-memory implementation

## Why
Draft ADR-0047 §1 (`specs/ADR-surface-lanes.md`) enforces "one instance per surface per
deployment" (sub-doctrine 8.f, `src/vibey_tools/gh/docs/doctrines.md`, and 8.c's "a restart,
never a second copy") with a **broker lease**: the lane first declares an exclusive,
auto-delete queue `<prefix>.surface.<name>.lock`; RabbitMQ lets only one connection own an
exclusive queue. `x-single-active-consumer` cannot do this, because it is per queue and a lane
owns two queues ("What does not fit", first bullet).

The family has no one-owner primitive. Sub-doctrine 10.e says teach the family. This lane
declares the seam and ships its in-memory implementation, so every later lane can be tested
with no broker. `surfaces-amqp-lease-client` adds the aio-pika implementation behind the same
interface. It is a separate interface from `AmqpClientInterface`, so the two implementations
can land in separate lanes without breaking either (ADR-0047 lane S07, part 2).

## Required behaviour
1. **`vibey_bootstrap/amqp/interfaces/lease_interface.py`** (new), two `@runtime_checkable`
   Protocols:
   ```python
   class AmqpLeaseInterface(Protocol):
       @property
       def name(self) -> str: ...
       def is_lost(self) -> bool: ...          # True once the broker no longer guarantees ownership
       async def wait_lost(self) -> None: ...  # returns when the lease is lost
       async def release(self) -> None: ...    # gives the lease up; idempotent

   class AmqpLeasesInterface(Protocol):
       async def acquire_exclusive(self, name: str) -> AmqpLeaseInterface | None: ...
       async def close(self) -> None: ...      # releases every lease this object acquired
   ```
   Docstrings: `acquire_exclusive` returns `None` when another holder owns `name`, never
   blocks and never retries; a lost lease is never reclaimed by the same object (the holder
   exits and its supervisor restarts it, ADR-0047 §1).
2. **`vibey_bootstrap/amqp/memory_lease.py`** (new):
   - `class InMemoryAmqpLeases` (implements `AmqpLeasesInterface`). It keeps
     `_holders: dict[str, InMemoryAmqpLease]`. `acquire_exclusive(name)`:
     - an empty `name` raises `ValueError("a lease needs a name")`;
     - when `name` is held by a lease that is neither lost nor released, return `None`;
     - otherwise create, store and return a new `InMemoryAmqpLease`.
     `close()` releases every lease it holds. `holder(name) -> InMemoryAmqpLease | None`
     returns the current holder, for tests.
     Two "processes" in a test share one `InMemoryAmqpLeases`, as two connections share one
     broker.
   - `class InMemoryAmqpLease` (implements `AmqpLeaseInterface`), built by the leases object
     with its name and owner. It holds an `asyncio.Event` for loss.
     - `release()` marks it released, removes it from the owner's holders, and is a no-op the
       second time. A released lease is not lost (`is_lost()` stays `False`).
     - `simulate_loss()` (test helper, like `simulate_channel_close`) sets the event, marks it
       lost and removes it from the holders, as a dropped connection deletes an exclusive
       queue.
     - `wait_lost()` awaits the event.
3. **Exports.** `vibey_bootstrap/amqp/interfaces/__init__.py` exports both Protocols;
   `vibey_bootstrap/amqp/__init__.py` exports them and `InMemoryAmqpLeases`,
   `InMemoryAmqpLease`. Its module docstring gains one sentence: "The exclusive lease exists
   because the family had no one-owner primitive: `x-single-active-consumer` is per queue,
   and a surface lane owns two queues (ADR-0047 §1)."
4. No `aio_pika` import in either new module.

## Where to change
- New `src/vibey_tools/bootstrap/vibey_bootstrap/amqp/interfaces/lease_interface.py`,
  `src/vibey_tools/bootstrap/vibey_bootstrap/amqp/memory_lease.py`.
- `src/vibey_tools/bootstrap/vibey_bootstrap/amqp/interfaces/__init__.py`,
  `src/vibey_tools/bootstrap/vibey_bootstrap/amqp/__init__.py` (exports only).
- New `src/vibey_tools/bootstrap/test/amqp/test_memory_lease.py`.
- No `pyproject.toml` change: both modules are inside packages R04 already lists.

## Acceptance criteria
- [ ] The first `acquire_exclusive("x")` returns a lease; a second returns `None` until the first is released or lost; then a new acquire succeeds.
- [ ] `simulate_loss()` makes `is_lost()` true and `wait_lost()` return; `release()` does neither.
- [ ] `close()` frees every name it held.
- [ ] `isinstance(InMemoryAmqpLeases(), AmqpLeasesInterface)` and the lease satisfies `AmqpLeaseInterface`.
- [ ] `grep -n aio_pika src/vibey_tools/bootstrap/vibey_bootstrap/amqp/memory_lease.py` prints nothing.
- [ ] The tenant keeps its 100% line floor; mypy and bandit pass.

## Tests to write first (TDD)
`test/amqp/test_memory_lease.py` (no service; `pytest.mark.asyncio` as the tenant's other async tests do):
- `test_a_held_name_cannot_be_acquired_again`
- `test_release_frees_the_name_and_is_idempotent`
- `test_loss_frees_the_name_and_wakes_the_waiter`
- `test_a_released_lease_is_not_lost`
- `test_close_releases_everything_it_acquired`
- `test_an_empty_name_is_refused`
- `test_both_classes_satisfy_their_interfaces`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    (cd src/vibey_tools/bootstrap && uv run python -m pytest -q -p no:cacheprovider --no-cov test/amqp test/test_packaging.py)
    (cd src/vibey_tools/bootstrap && uv run python -m pytest -q -p no:cacheprovider test/ -m "not integration")
    (cd src/vibey_tools/bootstrap && uv run python -m mypy vibey_bootstrap/ && uv run python -m bandit -r vibey_bootstrap/ -ll -q)
    uv run lint-imports

## Out of scope
- The aio-pika lease (`surfaces-amqp-lease-client`). Anything under `src/vibey/`.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees
  (`surfaces-docs-wave`). Do not push, open PRs or change remotes. Commit locally with the
  Title as the subject.

## Lane card
- **Depends on:** `split-351-1-amqp-contract` (#351 child 1: the `amqp` package and its `interfaces/`).
- **Shares a file with:** the two `__init__.py` files (exports only; R04, T21, L21 add others).
- **Must keep passing unchanged:** every existing vibey-bootstrap test; all protected root tests.
- **Standing constraints (every vibey-bootstrap surfaces lane):**
  - Read `/private/tmp/claude-501/storm/qwenstorm-3.0.0/EDITING-RULES.md` first.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from a sibling.
  - No `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`.
  - The default run needs no broker.
  - If `src/vibey_tools/bootstrap/test/fakes/registry.py` exists, register
    `AmqpLeasesInterface → InMemoryAmqpLeases` there.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
