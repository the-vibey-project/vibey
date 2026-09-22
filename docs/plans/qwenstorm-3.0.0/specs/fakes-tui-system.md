## Title
test(system): the full-worker system tests, the dashboard's fetch and the operator handlers run on the in-memory app

## Why
Three suites prove the most with the least mocking, and still need PostgreSQL:
- **`tests/system/test_full_worker_faked.py`** (3 tests; marked `system` and, since
  `fakes-harness-decouple`, `integration`). `build_full_worker` drives a project to DONE, to
  DONE-deployed, and through a forced wind-down rotation. It uses `ScriptedEngine` adapters
  and scripted providers. Only its persistence is real: `build_app()` at `:139`, `:295`, `:463`.
  Its assertions read the database with raw SQL (`asyncpg.connect` at `:45`, `:104`, `:220`,
  `:246`, `:369`).
- **`tests/tui/test_dashboard.py::test_fetch_dashboard_state_from_db`** (`:151-245`). It seeds
  through `build_app()` and asyncpg, then calls `fetch_dashboard_state(...)`.
- **`tests/infrastructure/test_operator_handlers.py`** (14 tests, `pytestmark = integration`).
  The kopf handlers over `build_app()`. Since `fakes-operator-k8s`, they take their
  composition from kopf's `memo`.

With `InMemoryApp` (`fakes-bootstrap-seam`), all three run in the default tier. The system
tests then prove the whole conductor (worker loop, handlers, rotation, handoff gate, ledger)
with no service at all.

## Required behaviour
1. **`test_full_worker_faked.py`**:
   - replace `build_app()` with `memory_app.open_app()`. The `memory_app` fixture comes from
     `tests/cli/ops_support.py`, or a local copy of the same three lines; the system tests may
     not import from `tests/cli`, so put the fixture in `tests/system/conftest.py`;
   - replace every raw-SQL assertion with a read through the ports or the fakes' stores, with
     the same assertion meaning. `SELECT … FROM job` becomes
     `persistence.jobs.list_for_cycle(...)` or `store.jobs`. `SELECT … FROM event` becomes
     `persistence.ledger.all_for_project(...)`. `SELECT … FROM handoff` becomes
     `InMemoryHandoffStore.get(...)` or `list_for_pair(...)`;
   - the cost assertion (`:265`, "$0.01 on its TurnCompleted") reads the ledger's
     cost events, or `engine_health_repo`'s `cost_usd_cycle`, as it does today;
   - remove the `integration` mark and keep `system`.
2. **`test_dashboard.py`**: the fetch test seeds through `open_app()` and calls
   `fetch_dashboard_state` with the same arguments. Remove its mark.
3. **`test_operator_handlers.py`**: call the handlers with
   `memo=kopf.Memo(composition=OperatorComposition(open_app=memory_app.open_app, apps_client=lambda: InMemoryAppsApi()))`.
   Remove the database fixture and `pytestmark`.
4. Lower the baseline where anything counted. Remove the keys from `PER_TEST_MODULES`.

## Where to change
- `tests/system/test_full_worker_faked.py`, a new `tests/system/conftest.py` (fixture only),
  `tests/tui/test_dashboard.py`, `tests/infrastructure/test_operator_handlers.py`,
  `tests/meta/test_integration_tier.py`, `tests/meta/patching_baseline.json`.

## Acceptance criteria
- [ ] With PostgreSQL stopped,
      `uv run pytest -q -p no:cacheprovider -m "not integration" tests/system tests/tui tests/infrastructure/test_operator_handlers.py`
      passes, and collects as many tests as before.
- [ ] `tests/system/test_delivery_stage_set.py` (protected) is unchanged and passes.
- [ ] `grep -n "asyncpg" tests/system/test_full_worker_faked.py` prints nothing.

## Tests to write first (TDD)
- Convert one system test at a time, starting with `test_full_worker_drives_a_project_to_done_local`.
  If an assertion cannot be expressed through a port, stop and name the missing read in the
  commit body. Do not reach into private attributes of production classes.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/system tests/tui tests/infrastructure/test_operator_handlers.py tests/meta
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    git diff --stat HEAD~1 -- tests/system/test_delivery_stage_set.py

## Out of scope
- Production code. CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-bootstrap-seam`, `fakes-operator-k8s`.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** `tests/system/test_delivery_stage_set.py` and `tests/live/**` (protected).
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
