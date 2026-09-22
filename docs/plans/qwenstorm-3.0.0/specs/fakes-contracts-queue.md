## Title
test(contracts): the queue contract runs on the in-memory queue by default, and on PostgreSQL and RabbitMQ on opt-in

## Why
Lane R18 (`specs/rmq-r18-queue-contract-suite.md`) writes
`tests/contracts/test_job_queue_contract.py`, parametrized over three backends:
- `postgres`;
- `rabbitmq-memory`: `RabbitMqJobRepository` over PostgreSQL and `InMemoryAmqpClient`,
  which "always runs";
- `rabbitmq`: a real broker, skipped unless `VIBEY_TEST_AMQP_URL` is set.

Two of those need PostgreSQL. So under the operator's standard, R18's "always runs" backend
is not default-tier: the default run has no PostgreSQL. And the queue every worker, handler
and system test uses (`FakeJobRepository`, `tests/fakes/queue.py`) is not in the suite at all.

This lane adds the in-memory queue as the default-tier backend, and moves the two
PostgreSQL-backed parameters to the integration tier. Amendment A5 in
`specs/ADR-test-harness-fakes-amendment.md` records the resolution.

## Required behaviour
1. **In `tests/contracts/test_job_queue_contract.py`,** the `queue` fixture's parameters become:
   - `"memory"`: a `QueueHarness` over `FakeJobRepository` and `FakeHumanGateRepository`
     sharing one `InMemoryQueueStore` (`tests/fakes/queue.py`), unmarked. Its `settle()`
     does nothing, as `postgres` does;
   - `pytest.param("postgres", marks=pytest.mark.integration)`;
   - `pytest.param("rabbitmq-memory", marks=pytest.mark.integration)`, because it needs
     PostgreSQL for its record store;
   - `pytest.param("rabbitmq", marks=pytest.mark.integration)`, which still skips without
     `VIBEY_TEST_AMQP_URL`.
2. **Every R18 contract passes on `memory`:** idempotent enqueue, empty claim, dependency
   gating, future `run_after`, fenced `ack`, `defer` then claimable, `park`/`answer`, reap
   after an expired lease, `grant_attempts`, and `count_unsettled`/`queue_depth` agreement.
   - The lease-expiry case needs time to pass. The `memory` harness builds the store with a
     `FakeClock` (`tests/fakes/system.py`) and advances it in `settle()`, or in a new harness
     method `expire_leases()`. It must not sleep.
   - If a contract fails only on `memory`, fix the fake (`tests/fakes/queue.py`), never the contract.
3. **The chaos twin is unchanged.** `tests/infrastructure/queue/test_rabbitmq_chaos.py` (R18)
   is already `integration` and real-broker-only.
4. **The duplicated cases go.** `tests/fakes/test_fake_queue.py` keeps only the fake's own
   helpers' tests (fault injection, `on_ready`), because the contract now proves the rest.

## Where to change
- `tests/contracts/test_job_queue_contract.py` (the fixture and harness only), `tests/fakes/test_fake_queue.py`.

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider -m "not integration" tests/contracts/test_job_queue_contract.py` passes with no PostgreSQL and no broker, on `memory` only.
- [ ] With PostgreSQL (and optionally a broker), `-m integration` passes on the other backends exactly as R18 left them.
- [ ] `git diff --stat HEAD~1 -- tests/infrastructure/db/test_chaos.py` is empty.

## Tests to write first (TDD)
- Enable `memory` and run the existing contracts. Every one must pass without edits to its body.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/contracts tests/fakes
    uv run pytest -q -p no:cacheprovider -m integration tests/contracts
    git diff --stat HEAD~1 -- tests/infrastructure/db/test_chaos.py

## Out of scope
- Production code, and the RabbitMQ repository. CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-contracts-repositories`, **`rmq-r18-queue-contract-suite`**.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** `tests/infrastructure/db/test_chaos.py` (protected), R18's chaos twin.
- **Standing constraints (every fakes lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`,
    `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`,
    `tests/system/test_delivery_stage_set.py` and `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte-for-byte from a sibling file.
  - A fake is a plain class with real in-memory behaviour for every method of its port.
    `unittest.mock` is never used under `tests/fakes/`. No method body is only `...`, only
    `pass`, only `return None`, or only `raise NotImplementedError`.
  - Substitute at a declared seam: a constructor or keyword argument, or
    `CliRunner.invoke(..., obj=...)`. Never use `monkeypatch.setattr`, `mock.patch` or
    `MagicMock` (sub-doctrine 9.b). `monkeypatch.setenv`, `delenv` and `chdir` stay allowed.
  - Once `fakes-registry` has landed, register every fake you add in `tests/fakes/registry.py`
    and delete its `PENDING` entry. Lower each converted file's numbers in
    `tests/meta/patching_baseline.json` to what the ratchet now counts, and never raise one.
  - A test that needs a real service is marked `integration`, and skips when its
    `VIBEY_TEST_*` variable is unset.
  - Change existing files with `edit_file` or a checked replacement, and never rewrite an
    existing test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
