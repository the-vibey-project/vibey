## Title
refactor(db): the ledger search compiles to a SQLAlchemy Core select instead of a $n string

## Why
Every persistence access goes through the ORM behind a declared interface (ADR-0016,
sub-doctrine 9.b; draft ADR `specs/ADR-orm.md`). The ledger search
(`src/vibey/infrastructure/db/ledger_search_repository.py`) hand-builds SQL text: a compiler
appends clause strings and numbers its own `$n` placeholders (`:62-97`, with a `bind`
closure), and the repository runs the string on an asyncpg pool (`:140-148`). Its guarantee
— nothing a searcher typed reaches the SQL text, every value is bound — is exactly what
SQLAlchemy Core gives by construction, without a placeholder counter to get wrong or a
`# nosec B608` to justify (`:90-93`). The `event` row mapper already reads ORM rows (lane
`orm-ledger`).

## Required behaviour
1. `LedgerSearchCompiler.compile(self, project_id, query, *, fetch) -> Select[Any]`, with
   `EVENT = TABLES.table("event")` (lane `orm-tables`) and one clause per criterion, in
   today's order:
   - `EVENT.c["project_id"] == project_id` (always)
   - `event_id`: `EVENT.c["event_id"] == query.event_id`
   - `digest`: `EVENT.c["digest"] == query.digest`
   - `actor`: `self._actor(query.actor)` (below)
   - `since`: `EVENT.c["produced_at"] >= query.since`; `until`: `EVENT.c["produced_at"] < query.until`
   - `kinds` (non-empty): `EVENT.c["kind"].in_(sorted(kind.value for kind in query.kinds))`
   - `text`: `cast(EVENT.c["payload"], Text).ilike(self.contains_pattern(query.text), escape=LIKE_ESCAPE)`
   and returns `select(EVENT).where(*clauses).order_by(EVENT.c["seq"].desc()).limit(fetch)`.
2. `_actor(actor) -> ColumnElement[bool]` (a `@staticmethod`): `SELF` →
   `EVENT.c["engine_id"].is_(None)`; `ENGINE` → `EVENT.c["engine_id"] == actor.name`; any
   other scope → `EVENT.c["provenance"] == actor.name` (bound through the column's enum type).
3. `contains_pattern` and `LIKE_ESCAPE` are unchanged.
4. `SearchStatement` (the dataclass, `:51-56`) is deleted, and so are
   `SearchStatementInterface` (`interfaces/ledger_search_repository_interface.py:25-37`) and
   its export (`interfaces/__init__.py:14`, `:37`). `LedgerSearchCompilerInterface.compile`
   is declared `-> Select[Any]` (`from sqlalchemy import Select` under `TYPE_CHECKING`), and
   its docstring says every value is a bound parameter.
5. `PostgresLedgerSearchRepository.__init__(self, orm: PostgresOrmInterface, *, compiler=LEDGER_SEARCH_SQL, rows=EVENT_ROWS)`;
   `search` runs `(await conn.execute(statement)).mappings().all()` inside `self._orm.connect()`
   and keeps today's "fetch one past the limit" logic (`:141-148`) unchanged.
6. The module docstring's index table and "nothing a searcher typed" paragraph stay true;
   update only the sentence that mentions `$n` placeholders and the `B608` comment.
7. `build_app` passes `ledger_search=PostgresLedgerSearchRepository(orm)` (the field lane
   `orm-app-resources` added).

## Where to change
- `src/vibey/infrastructure/db/ledger_search_repository.py`
- `src/vibey/infrastructure/db/interfaces/ledger_search_repository_interface.py`
- `src/vibey/infrastructure/db/interfaces/__init__.py`
- `src/vibey/bootstrap.py` (the `ledger_search=` line)
- `tests/infrastructure/db/test_ledger_search_repository.py`: the compiler tests assert the
  old SQL text, so they move. Remove them with this exact script, then run
  `uv run ruff check --fix tests/infrastructure/db/test_ledger_search_repository.py` to drop
  the imports it leaves unused:
  ```python
  from pathlib import Path
  p = Path("tests/infrastructure/db/test_ledger_search_repository.py")
  s = p.read_text()
  a = s.index("# -- the compiler, without a database")
  b = s.index("# -- against Postgres")
  s = s[:a] + s[b:]
  c = s.index("def test_an_unrecognized_kind_is_bound_as_its_exact_text")
  d = s.index("async def test_a_kind_a_newer_vibey_wrote_is_found_and_read_back")
  s = s[:c] + s[d:]
  p.write_text(s)
  ```
  Then two small edits, because `SearchStatementInterface` no longer exists: remove it from
  the `from vibey.infrastructure.db.interfaces import (...)` block (`:28-32`), and in
  `test_a_substituted_compiler_and_row_mapper_are_used` change the nested `compile`'s return
  annotation `-> SearchStatementInterface:` to `-> object:`. Every other Postgres-backed test
  in that file stays and must pass unchanged.
- New `tests/infrastructure/orm/test_ledger_search_compiler.py` (no database), replacing them.

Rules every ORM lane keeps: production code reaches PostgreSQL only through
`PostgresOrmInterface`; no new `import asyncpg`, `text()`, `exec_driver_sql()` or SQL strings
in `src/`; substitute at the declared seam, never by patching an import; never edit a
protected test; the first line of every new file is the provenance comment copied
byte-for-byte from a sibling.

## Acceptance criteria
- [ ] `grep -n "asyncpg\|nosec\|conn.fetch" src/vibey/infrastructure/db/ledger_search_repository.py` prints nothing.
- [ ] Every Postgres-backed test in `test_ledger_search_repository.py` passes unchanged, including wildcards, the hostile needle, the half-open window, the unknown kind and the substituted compiler.
- [ ] `tests/cli/test_ledger_search_cli.py` passes.
- [ ] 100% branch coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
`tests/infrastructure/orm/test_ledger_search_compiler.py` (no database). Compile with
`statement.compile(dialect=sqlalchemy.dialects.postgresql.asyncpg.dialect())`; read the text
with `str(compiled)` and the bound values with `compiled.params`:
- `test_no_criteria_is_the_project_newest_first` (text has `ORDER BY event.seq DESC` and `LIMIT`; params hold `project_id` and `51`)
- `test_every_criterion_binds_its_value` (the eight-criterion query of the removed test; every value — the ids, the digest, `"codexloop"`, both datetimes, the pattern `"%50\\%%"`, and `4` — appears in `compiled.params.values()`, the kinds as the list `["FindingRaised", "FindingResolved"]`)
- `test_every_actor_scope_has_its_own_clause` (parametrize over `ActorScope`: `SELF` renders `event.engine_id IS NULL`; `ENGINE` binds `"x"` against `event.engine_id`; `PROVENANCE` against `event.provenance`)
- `test_the_needle_is_matched_literally` (the four `contains_pattern` cases, moved as they are)
- `test_nothing_a_searcher_types_reaches_the_sql_text` (the hostile needle is in the params, never in `str(compiled)`)
- `test_an_unrecognized_kind_is_bound_as_its_exact_text` (`["FindingRaised", "FutureKindX"]` is a bound value)
- `test_the_seams_are_satisfied` (`LEDGER_SEARCH_SQL` is a `LedgerSearchCompilerInterface`; the result is a `sqlalchemy.Select`; `EVENT_ROWS` is an `EventRowMapperInterface`)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    # Postgres-backed (integration tier):
    uv run pytest -q -p no:cacheprovider tests/infrastructure/db/test_ledger_search_repository.py tests/cli/test_ledger_search_cli.py
    # No-services unit tests (need no database once the in-memory-fakes work lands; today the root conftest still opens one at startup):
    uv run pytest -q -p no:cacheprovider tests/infrastructure/orm/test_ledger_search_compiler.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The criteria themselves, the CLI (`src/vibey/cli/ledger_search.py`), the indexes
  (`migrations/0012`). Docs, CHANGELOG.
Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
