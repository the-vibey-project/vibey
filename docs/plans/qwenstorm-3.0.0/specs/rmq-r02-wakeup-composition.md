## Title
refactor(worker): the composition root builds the job-ready wakeup

## Why
ADR-0044 §1 says the composition root is the only place that knows which queue backend
runs. Today the CLI knows:

- `vibey worker` imports and builds `PostgresJobReadyNotifier(database_url())` itself
  (`src/vibey/cli/main.py:1467` and `:1715-1716`);
- `AppResources` types `jobs` as the concrete `PostgresJobRepository`
  (`src/vibey/bootstrap.py:136`).

This lane moves that choice into `bootstrap.py` and changes no behaviour.

## Required behaviour
1. `AppResources.jobs` is annotated as the `JobRepository` Protocol
   (`vibey.application.interfaces.queue`, `:89`). The value is still
   `PostgresJobRepository(pool)` (`bootstrap.py:918`).
2. There is a new class `JobWakeupOpener` in `src/vibey/bootstrap.py`. It is
   constructed with the DSN and has two methods:
   - `async def open(self) -> JobReadyNotifier` does
     `from vibey.infrastructure.db import notifier as db_notifier` **inside the method
     body**, builds `db_notifier.PostgresJobReadyNotifier(self._dsn)`, awaits
     `connect()`, and returns it. The import must be at call time so that the existing
     tests' `patch("vibey.infrastructure.db.notifier.PostgresJobReadyNotifier")` still
     reaches it.
   - `async def close(self, notifier: JobReadyNotifier) -> None` awaits
     `notifier.close()` when the notifier has one.
3. `AppResources` gains a required field `wakeup: JobWakeupOpenerInterface`, built in
   `build_app` from `url or database_url()`. There is exactly one construction
   (`bootstrap.py:916`).
4. `vibey worker` gets its notifier from `await resources.wakeup.open()` and closes it
   with `await resources.wakeup.close(notifier)` in the existing `finally`
   (`cli/main.py:1756-1760`). The import at `:1467` goes away.
5. Behaviour is unchanged: same channel, same 5 s wait, same output lines.

## Where to change
- `src/vibey/bootstrap.py`: `AppResources` (`:134-171`), `build_app` (`:694-916`).
- `src/vibey/bootstrap_interface.py`:
  - Add `JobWakeupOpenerInterface`, a Protocol with `open` and `close`.
  - Add a `wakeup` property to `AppResourcesInterface`.
  - Follow the style of the existing Protocols in that file.
- `src/vibey/cli/main.py:1467`, `:1715-1716` and the `finally` near `:1756`.

## Acceptance criteria
- [ ] `grep -n PostgresJobReadyNotifier src/vibey/cli/main.py` prints nothing.
- [ ] Both existing CLI tests that patch the notifier class pass without edits.
- [ ] `JobWakeupOpener` satisfies `JobWakeupOpenerInterface`.
- [ ] 100% coverage on `cli/` and `infrastructure/`. `bootstrap.py` sits outside the layer gates, but its new code is still tested.

## Tests to write first (TDD)
- `tests/test_bootstrap.py`:
  - `test_the_wakeup_opener_builds_the_postgres_notifier_at_call_time` (patch the class, assert it was built with the DSN and connected)
  - `test_the_wakeup_opener_closes_what_it_opened`
  - `test_the_wakeup_opener_is_its_declared_seam`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/test_bootstrap.py tests/cli tests/infrastructure/db/test_notifier.py tests/system/test_full_worker_faked.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Choosing a backend (R17).
- The RabbitMQ wakeup (R14).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

## Lane card
- **Depends on:** none.
- **Wave:** 1.
- **Files touched:**
  - `src/vibey/bootstrap.py`
  - `src/vibey/bootstrap_interface.py`
  - `src/vibey/cli/main.py`
  - `tests/test_bootstrap.py`
- **Parallel-safe with:** every other wave-1 lane. It is the start of the
  `bootstrap.py` / `cli/main.py` chain.
- **Must keep passing unchanged:**
  - `tests/cli/test_operational_commands.py`, which patches `vibey.infrastructure.db.notifier.PostgresJobReadyNotifier` at `:1255`
  - `tests/cli/test_sovereign_provider_options.py` (the same patch at `:151`)
  - `tests/infrastructure/db/test_notifier.py`
  - `tests/cli/test_main_integration.py`
  - `tests/test_bootstrap.py`
  - `tests/system/test_full_worker_faked.py`
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
