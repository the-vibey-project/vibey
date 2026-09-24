## Title
feat(ledger): the ledger search port can search every project a deployment holds, in one statement

## Why
Sub-doctrine 7.a (`src/vibey_tools/gh/docs/doctrines.md:72-78`): "the ledger always has a way for
anyone … to search it: the full public ledger where a deployment holds it". The search port
searches one project only: `LedgerSearch.search(project_id, query)`
(`src/vibey/application/interfaces/ledger.py:131-145`); its compiler always adds
`project_id = $1` (`src/vibey/infrastructure/db/ledger_search_repository.py:59-97`, and after
`orm-ledger-search` `EVENT.c["project_id"] == project_id`); the CLI resolves exactly one project
(`src/vibey/cli/ledger_search.py:5`, `:207-218`). #136 plans a forge search, not this.

This lane gives the store a deployment-wide search: the same criteria, the same "newest `limit`,
returned oldest first, truncated when more matched" contract, over every project, as one bound
statement. `gap-ledger-search-all-projects-2` exposes it as `vibey ledger search --all-projects`.
Across projects `seq` is not a global order, so the deployment-wide order is `produced_at`, then
project id, then `seq`: stable and total.

## Required behaviour
1. `LedgerSearchCompiler.compile(self, project_id: UUID | None, query, *, fetch)` (after
   `orm-ledger-search`, it returns a `Select[Any]`):
   - `project_id is None`: no project clause; every other criterion exactly as today; ordered
     `EVENT.c["produced_at"].desc(), EVENT.c["project_id"].asc(), EVENT.c["seq"].desc()`; `.limit(fetch)`.
   - A project id: exactly today's statement (project clause first, `ORDER BY event.seq DESC`).
2. `LedgerSearchCompilerInterface.compile`
   (`src/vibey/infrastructure/db/interfaces/ledger_search_repository_interface.py`) takes
   `project_id: UUID | None`; its docstring says `None` is every project the deployment holds,
   ordered newest first by `produced_at`, then project, then `seq`.
3. `PostgresLedgerSearchRepository`: the body of `search` moves into
   `async def _search(self, project_id: UUID | None, query) -> LedgerSearchResult` (unchanged:
   fetch one past the limit, keep `limit`, reverse, `truncated`). `search(project_id, query)`
   returns `await self._search(project_id, query)`; new
   `async def search_all(self, query: LedgerQueryInterface) -> LedgerSearchResult` returns
   `await self._search(None, query)`.
4. The port `LedgerSearch` gains
   `async def search_all(self, query: LedgerQueryInterface) -> LedgerSearchResultInterface`, with
   the docstring "The most recent `query.limit` matches across every project this deployment
   holds, oldest first, and whether older matches were left out (7.a)." The contract
   `PostgresLedgerSearchRepositoryInterface` (`src/vibey/infrastructure/interfaces/class_contracts.py:91`)
   inherits it.
5. **The fake.** `InMemoryLedgerSearch` (`tests/fakes/ledger_publication.py`, lane
   `fakes-ledger-publication`): its constructor's `ledger` annotation becomes `InMemoryLedger`
   (it needs every project's events). The filter of `search` moves into a private
   `_matches(event, query) -> bool`, used by both. `search_all(query)` filters `self._ledger.events`,
   takes `sorted(matches, key=lambda e: (e.produced_at, -e.project_id.int, e.seq), reverse=True)`
   (newest first by time, then project ascending, then `seq` descending, as PostgreSQL orders
   `uuid`), keeps the first `query.limit`, returns them reversed, with
   `truncated = len(matches) > query.limit`, as the real `LedgerSearchResult`.

## Where to change
- `src/vibey/infrastructure/db/ledger_search_repository.py`,
  `src/vibey/infrastructure/db/interfaces/ledger_search_repository_interface.py`,
  `src/vibey/application/interfaces/ledger.py` (edit_file only).
- `tests/fakes/ledger_publication.py`.
- Append to `tests/infrastructure/orm/test_ledger_search_compiler.py` (no database),
  `tests/infrastructure/db/test_ledger_search_repository.py` (integration by its directory) and
  `tests/fakes/test_fake_ledger_search.py` (no service).

## Acceptance criteria
- [ ] `compile(None, LedgerQuery(), fetch=51)` compiled with the asyncpg dialect has no
      `event.project_id =` and renders `ORDER BY event.produced_at DESC, event.project_id ASC, event.seq DESC`;
      `compile(pid, ...)` is byte-for-byte today's text.
- [ ] Two projects with interleaved `produced_at`: `search_all(LedgerQuery(limit=3))` returns the
      three newest across both, oldest first, with `truncated` true when a fourth matched.
- [ ] `search_all` applies every criterion (`kinds`, `text`, `actor`, `since`/`until`, `digest`, `event_id`).
- [ ] `search(project_id, query)` returns exactly what it returned before for every existing test.
- [ ] The fake answers each case exactly as PostgreSQL does; `tests/fakes/test_port_parity.py` passes.
- [ ] `bandit -q -r src/vibey` is clean; 100% branch coverage of `src/vibey/application/*` and `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
- `tests/infrastructure/orm/test_ledger_search_compiler.py` (append):
  `test_a_deployment_wide_search_names_no_project_and_orders_by_time`,
  `test_a_project_search_is_unchanged_by_the_deployment_wide_form`.
- `tests/infrastructure/db/test_ledger_search_repository.py` (append; two projects, drafts with
  explicit `produced_at`):
  `test_search_all_returns_the_newest_matches_across_projects_oldest_first`,
  `test_search_all_applies_every_criterion`,
  `test_search_all_reports_that_older_matches_were_left_out`,
  `test_search_all_of_an_empty_deployment_matches_nothing`.
- `tests/fakes/test_fake_ledger_search.py` (append): the same four names and outcomes.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider tests/infrastructure/orm tests/fakes tests/cli -m "not integration and not paid"
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider tests/infrastructure/db/test_ledger_search_repository.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/application/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The CLI (`gap-ledger-search-all-projects-2`).
- A deployment-wide `produced_at` index: `event_project_produced_at`
  (`migrations/0012_event_search_indexes.sql`) serves one project; a cross-project search sorts.
  If a measured search is slow (8.g), an index is a migrator lane.
- The published site's search (the shard a repository holds; 7.a's other half).
- Docs, CHANGELOG.

Commit as `feat(ledger): the ledger search port can search every project a deployment holds`. Do not push.

## Lane card
- **Depends on:** `orm-ledger-search`, `fakes-ledger-publication`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
