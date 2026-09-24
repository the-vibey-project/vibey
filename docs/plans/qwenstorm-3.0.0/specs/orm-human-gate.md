## Title
refactor(db): human gates go through the ORM seam, notify with pg_notify, and get their declared contract

## Why
Every persistence access goes through the ORM behind a declared interface (ADR-0016,
sub-doctrine 9.b; draft ADR `specs/ADR-orm.md`). `PostgresHumanGateRepository`
(`src/vibey/infrastructure/db/human_gate_repository.py:34-116`) is eight raw asyncpg
statements, two of them `NOTIFY` built with f-strings (`:58`, `:85`), plus two 9.b gaps: no
contract beside the adapter (the port is `HumanGateRepository`,
`src/vibey/application/interfaces/gates.py:17`, which does not declare `get`), and two bare
module functions (`_require` `:11-14`, `_row_to_record` `:17-31`). The answer path is
load-bearing: answering re-readies the parked job **in the same transaction** as the
answer and wakes the workers (`:64-86`; ADR-0009, never block a worker on a human).
`pg_notify(channel, payload)` is the function form of `NOTIFY`: inside a transaction it is
delivered at commit and duplicates fold, exactly as `NOTIFY` is — and both of its arguments
are bound parameters, so no identifier is ever formatted into SQL text.

## Required behaviour
1. `class HumanGateRowMapper` with `to_record(self, row: Mapping[str, Any]) -> HumanGateRecord`:
   today's mapping, except `options=tuple(JSON_COLUMNS.sequence(row["options"]))` and
   `answer=JSON_COLUMNS.optional_mapping(row["answer"])` (lane `orm-tables`).
   `GATE_ROWS: Final[HumanGateRowMapperInterface] = HumanGateRowMapper()`. `_row_to_record` is deleted.
2. `_require` becomes a `@staticmethod` `_required(row, *, context)` on the repository, same
   message (`f"{context}: expected a row but got none"`).
3. `PostgresHumanGateRepository.__init__(self, orm: PostgresOrmInterface, *, rows: HumanGateRowMapperInterface = GATE_ROWS)`.
4. With `GATES = TABLES.table("human_gate")` and `JOBS = TABLES.table("job")`:
   - `raise_gate`: in one `self._orm.transaction()`:
     `insert(GATES).values(project_id=…, job_id=…, kind=request.kind, prompt=request.prompt, options=list(request.options), default_answer=…, timeout_at=…).returning(*GATES.c)`,
     then `await conn.execute(select(func.pg_notify("vibey_gate_raised", str(row["gate_id"]))))`.
   - `answer`: in one `self._orm.transaction()`:
     `update(GATES).where(GATES.c["gate_id"] == gate_id).values(answer=dict(answer), answered_at=func.now(), answered_by=answered_by).returning(*GATES.c)`;
     `_required(row, context=f"answer: no gate {gate_id}")`; when `row["job_id"]` is not
     `None`: `update(JOBS).where(JOBS.c["id"] == row["job_id"], JOBS.c["state"] == "awaiting_human").values(state="ready", updated_at=func.now())`,
     then `select(func.pg_notify("vibey_job_ready", str(row["project_id"])))`.
   - `get`, `open_for_project`, `latest_for_job`: the same filters and orderings as
     `:88-116`, as `select(GATES)…` in `self._orm.connect()`
     (`order_by(GATES.c["raised_at"].asc(), GATES.c["gate_id"].asc())` and
     `order_by(GATES.c["raised_at"].desc(), GATES.c["gate_id"].desc()).limit(1)`).
5. Interfaces in the new `src/vibey/infrastructure/db/interfaces/human_gate_repository_interface.py`:
   `HumanGateRowMapperInterface` (`to_record`), exported from `interfaces/__init__.py`.
6. A new contract in `src/vibey/infrastructure/interfaces/class_contracts.py`:
   ```python
   @runtime_checkable
   class PostgresHumanGateRepositoryInterface(HumanGateRepository, Protocol):
       """The Postgres implementation of the human-gate port, with its point read."""

       async def get(self, gate_id: UUID) -> HumanGateRecord | None: ...
   ```
   exported from `src/vibey/infrastructure/interfaces/__init__.py`.
7. `build_app` passes `gates=PostgresHumanGateRepository(orm)` (`src/vibey/bootstrap.py:919`).

## Where to change
- `src/vibey/infrastructure/db/human_gate_repository.py`
- `src/vibey/infrastructure/db/interfaces/human_gate_repository_interface.py` (new)
- `src/vibey/infrastructure/db/interfaces/__init__.py`
- `src/vibey/infrastructure/interfaces/class_contracts.py`, `src/vibey/infrastructure/interfaces/__init__.py`
- `src/vibey/bootstrap.py` (one line)
- `tests/infrastructure/db/test_human_gate_repository.py` (append only)
- New `tests/infrastructure/orm/test_human_gate_row_mapper.py` (no database)

Rules every ORM lane keeps: production code reaches PostgreSQL only through
`PostgresOrmInterface`; no new `import asyncpg`, `text()`, `exec_driver_sql()` or SQL strings
in `src/`; substitute at the declared seam, never by patching an import; never edit a
protected test; the first line of every new file is the provenance comment copied
byte-for-byte from a sibling.

## Acceptance criteria
- [ ] `grep -n "asyncpg\|NOTIFY\|f\"NOTIFY" src/vibey/infrastructure/db/human_gate_repository.py` prints nothing.
- [ ] A listener on `vibey_gate_raised` receives the new gate's id after `raise_gate`; a listener on `vibey_job_ready` receives the project id after answering a gate that has a job.
- [ ] Answering re-readies only an `awaiting_human` job, in the answer's transaction (existing tests `:21-101` unchanged).
- [ ] `isinstance(repo, PostgresHumanGateRepositoryInterface)` and `isinstance(repo, HumanGateRepository)`.
- [ ] `tests/infrastructure/test_operator_handlers.py` and `tests/cli/test_main_integration.py` pass.
- [ ] 100% branch coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
Append to `tests/infrastructure/db/test_human_gate_repository.py` (integration). For a
listener, take a raw connection from the fixture (tests may use asyncpg):
`conn = await migrated_pool.acquire()`, `await conn.add_listener(channel, callback)` with a
callback that puts the payload on an `asyncio.Queue`; release it in `finally`.
- `test_raising_a_gate_notifies_its_id`
- `test_answering_a_gate_notifies_its_project`
- `test_the_repository_is_its_declared_contract`
`tests/infrastructure/orm/test_human_gate_row_mapper.py` (no database):
- `test_decoded_and_text_json_columns_map_the_same` (`options` as a list and as `'["a"]'`; `answer` as a dict, as JSON text and as `None`)
- `test_the_mapper_is_its_declared_seam`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    # Postgres-backed (integration tier):
    uv run pytest -q -p no:cacheprovider tests/infrastructure/db/test_human_gate_repository.py tests/infrastructure/test_operator_handlers.py tests/cli/test_main_integration.py
    # No-services unit tests (need no database once the in-memory-fakes work lands; today the root conftest still opens one at startup):
    uv run pytest -q -p no:cacheprovider tests/infrastructure/orm/test_human_gate_row_mapper.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The dispatch writer that `rmq-r15-gate-redispatch` adds to `answer` (it lands after this
  lane and builds on it). The notifier (`orm-notifier`). Docs, CHANGELOG.
Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
