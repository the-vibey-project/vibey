## Title
feat(gates): answering a gate re-dispatches its job

## Why
ADR-0044 §6. A parked job holds no delivery. Its answer re-readies it in the same
transaction as the answer (`src/vibey/infrastructure/db/human_gate_repository.py:61-86`).
In the RabbitMQ backend, that same transaction must also start a new dispatch episode
and write its outbox row, or the answered job would sit `ready` with no message until
the lost-dispatch sweep found it.

The PostgreSQL backend's SQL stays exactly as it is today.

*(Amended 2026-09-22 for the ORM wave, draft ADR `specs/ADR-orm.md`: this lane lands after
`orm-human-gate`, so the repository takes `PostgresOrmInterface`, `answer` runs in one
`self._orm.transaction()`, and its statements are SQLAlchemy Core over
`TABLES.table("human_gate")` and `TABLES.table("job")`, with `pg_notify` for the
notifications. The SQL block below states the new statement's semantics; the code builds
it as Core. Semantics unchanged.)*

## Required behaviour
1. `PostgresHumanGateRepository.__init__(orm, *, rows=GATE_ROWS, dispatch_writer: DispatchOutboxWriterInterface | None = None)`.
   The default `None` keeps today's behaviour exactly (the same statements, the same
   notifications).
2. With a writer set, the re-ready statement in `answer` becomes:
   ```sql
   UPDATE job SET state='ready', updated_at=now(),
                  dispatch_seq=dispatch_seq+1, dispatched_at=NULL
   WHERE id=$1 AND state='awaiting_human'
   RETURNING id, project_id, dispatch_seq, kind, run_after
   ```
   Build it as `update(JOBS).where(JOBS.c["id"] == row["job_id"], JOBS.c["state"] == "awaiting_human").values(state="ready", updated_at=func.now(), dispatch_seq=JOBS.c["dispatch_seq"] + 1, dispatched_at=None).returning(JOBS.c["id"], JOBS.c["project_id"], JOBS.c["dispatch_seq"], JOBS.c["kind"], JOBS.c["run_after"])`.
   A returned row gets one outbox row (`not_before = run_after`) through the writer, on the
   same `AsyncConnection`, in the same transaction. The `pg_notify('vibey_job_ready', …)`
   stays.
3. Answering a gate whose job is no longer `awaiting_human` writes no outbox row. That
   is today's guard.

## Where to change
- `human_gate_repository.py` (`__init__` and `answer`, as `orm-human-gate` left them).
- Import only the writer's interface, from `infrastructure/db/interfaces/dispatch_records_interface.py`.

## Acceptance criteria
- [ ] With no writer, the SQL and the effects are unchanged, and the existing tests pass.
- [ ] With a writer, the answer bumps the generation and writes exactly one outbox row.
- [ ] An answer to a gate whose job moved on writes none.
- [ ] 100% infrastructure coverage.

## Tests to write first (TDD)
Add to `tests/infrastructure/db/test_human_gate_repository.py`:
- `test_answer_with_a_dispatch_writer_redispatches_the_job`
- `test_answer_writes_no_dispatch_when_the_job_moved_on`
- `test_answer_without_a_writer_is_unchanged`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/db tests/infrastructure/test_operator_handlers.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Composing the writer into `build_app` (R17).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

## Lane card
- **Depends on:** R10, and `orm-human-gate` (amended 2026-09-22).
- **Wave:** 3.
- **Files touched:**
  - `src/vibey/infrastructure/db/human_gate_repository.py`
  - `tests/infrastructure/db/test_human_gate_repository.py` (new tests only)
- **Parallel-safe with:** R11, R12, R22 and R24.
- **Must keep passing unchanged:**
  - every existing test in `tests/infrastructure/db/test_human_gate_repository.py`
  - `tests/infrastructure/test_operator_handlers.py`
  - `tests/cli/test_main_integration.py`
  - all protected tests
- **Standing constraints:** see the header list.

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
- **Persistence goes through the ORM (amended 2026-09-22):** no new `import asyncpg`,
  `text()`, `exec_driver_sql()` or SQL string in `src/vibey`; statements are SQLAlchemy Core
  over the SQLModel tables (`TABLES.table(...)`), executed on a connection from
  `PostgresOrmInterface` (draft ADR `specs/ADR-orm.md`).

---
