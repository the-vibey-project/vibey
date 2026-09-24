## Title
feat(surfaces): the surface_lanes package, and a caller scope that tells a lane which project an operation serves

## Why
The ledger is project-scoped: `LedgerEvent.project_id` is required
(`src/vibey/domain/ledger.py`, `LedgerEvent`), and `append_event` writes it `NOT NULL`. Sub-doctrine
7.c ("the thorough ledger") wants every surface operation recorded, and 8.g ("always measured")
wants its measurements to "join the ledger". A surface operation only knows its project if the
caller says so, and the ports cannot say it: `send_message(channel_id, message)` has no
project argument, and adding one to every port would leak orchestration into twelve protocols.

So the caller binds its project (and job, when it has one) around the calls it makes, in a
scope the surface-lane client reads when it builds each request's `caller`
(`SurfaceCaller`, lane `surfaces-protocol`). A context variable is the in-process mechanism;
this class is its declared seam (sub-doctrine 9.b). Operations made outside any binding still
run; they carry only the calling process, and the lane records them as measurements without a
ledger event (`surfaces-ledger-recorder` says why).

This lane also creates the `vibey.infrastructure.surface_lanes` package every later
surface-lane module lives in (draft ADR-0047 §12, `specs/ADR-surface-lanes.md`), its
`interfaces/` package in the import-linter contract, and the test directory with its fixtures.

## Required behaviour
1. **Packages.** New `src/vibey/infrastructure/surface_lanes/__init__.py` (provenance line and
   the docstring `"""Surface lanes: every sovereign surface runs in one lane fed by RabbitMQ (sub-doctrine 8.f; draft ADR-0047)."""`)
   and `src/vibey/infrastructure/surface_lanes/interfaces/__init__.py`.
2. **`.importlinter`**: append `    vibey.infrastructure.surface_lanes.interfaces` as the last
   line of `source_modules` in `[importlinter:contract:infrastructure-interfaces-declare-only]`
   (`.importlinter:108-133` at this writing; other lanes append their own lines the same way).
3. **`src/vibey/infrastructure/surface_lanes/caller_scope.py`**, `class ContextVarSurfaceCallerScope`:
   - `__init__(self, *, process: str)`; an empty `process` raises `ValueError`. It creates one
     `contextvars.ContextVar[SurfaceCaller | None]` for the instance, default `None`.
   - `process` property.
   - `current(self) -> SurfaceCaller`: the bound caller, or `SurfaceCaller(process=self.process)`.
   - `bind(self, *, project_id: UUID, job_id: UUID | None = None) -> AbstractContextManager[SurfaceCaller]`
     (a `contextlib.contextmanager`): sets `SurfaceCaller(process, project_id, job_id)` for the
     body and restores the previous value with the token on exit, even when the body raises.
     Bindings nest, and each asyncio task sees its own (context variables are copied per task).
   - `@staticmethod default_process() -> str`: `f"{socket.gethostname()}:{os.getpid()}"`.
4. **`src/vibey/infrastructure/surface_lanes/interfaces/caller_scope_interface.py`**:
   `@runtime_checkable class SurfaceCallerScopeInterface(Protocol)` with `process`, `current`
   and `bind`; exported from the `interfaces/__init__.py`.
5. **Tests directory.** New `tests/infrastructure/surface_lanes/__init__.py` (provenance line
   only) and `tests/infrastructure/surface_lanes/conftest.py` with:
   - `memory_amqp` → a fresh `vibey_bootstrap.amqp.InMemoryAmqpClient()`;
   - `amqp_url` → `os.environ["VIBEY_TEST_AMQP_URL"]`, skipping when unset;
   - `cache_url` → `os.environ["VIBEY_TEST_CACHE_URL"]`, skipping when unset;
   - `pytest_collection_modifyitems(config, items)` that adds `pytest.mark.integration` to
     each item **under this directory** whose `fixturenames` include `amqp_url`, `cache_url`,
     `migrated_pool` or `database_url`. Items using only `memory_amqp` stay unmarked.
6. **Registry.** Register
   `SurfaceCallerScopeInterface → functools.partial(ContextVarSurfaceCallerScope, process="test:0")`
   and add the interface to `DRIVER_SEAMS` (the production class is already in memory).

## Where to change
- The new files above; `.importlinter` (one line); `tests/fakes/registry.py` (append).
- New `tests/infrastructure/surface_lanes/test_caller_scope.py`.

## Acceptance criteria
- [ ] Outside any binding, `current()` is `SurfaceCaller(process="p")` with no project.
- [ ] Inside `bind(project_id=P, job_id=J)` it is `(p, P, J)`; nested bindings restore the outer one; an exception in the body restores it too.
- [ ] Two concurrent tasks each binding a different project each see their own.
- [ ] `default_process()` has the form `<host>:<pid>`.
- [ ] `uv run lint-imports` passes with the new contract line; a test item using `amqp_url` in this directory is collected `integration` and one using only `memory_amqp` is not.
- [ ] 100% `infrastructure/` branch coverage.

## Tests to write first (TDD)
`tests/infrastructure/surface_lanes/test_caller_scope.py` (no service):
- `test_unbound_caller_has_only_the_process`
- `test_bind_sets_and_restores_even_on_error`
- `test_bindings_nest`
- `test_each_task_sees_its_own_binding`
- `test_default_process_is_host_and_pid`
- `test_an_empty_process_is_refused`
- `test_scope_satisfies_its_interface`
- `test_conftest_marks_service_backed_items_integration` (assert on `request.node` markers of two tiny tests in the module, as R12 does)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/infrastructure/surface_lanes tests/fakes tests/meta
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Reading the scope (`surfaces-lane-client`) or binding it in production code
  (`surfaces-consumer-notifications`). CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md
  and the skill trees (`surfaces-docs-wave`). Do not push, open PRs or change remotes. Commit
  locally with the Title as the subject.

## Lane card
- **Depends on:** `surfaces-protocol` (`SurfaceCaller`), `fakes-registry`, `split-351-1-amqp-contract` (the `memory_amqp` fixture).
- **Shares a file with:** `.importlinter` (R03, R12, R21, T05, `fakes-sockets` append lines), `tests/fakes/registry.py`.
- **Must keep passing unchanged:** `tests/meta/test_import_contracts_bind.py`, the fakes parity test, all protected tests.
- **Standing constraints (every surfaces lane):**
  - Read `STORM/EDITING-RULES.md` before changing a file. Change existing files with `edit_file` or a checked replacement.
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from line 1 of a sibling file.
  - Every new class has a `@runtime_checkable` Protocol in `surface_lanes/interfaces/`; interfaces declare and never import the code that consumes them.
  - Substitute only at a declared seam; never `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`.
  - The default run needs no service.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
