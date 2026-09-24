## Title
test(cli): the ledger search, ledger publication, deploy and forward-compatibility CLI tests run on the in-memory app

## Why
Four CLI modules still open PostgreSQL through `build_app()`:
- `tests/cli/test_ledger_search_cli.py` (19 tests, `pytestmark = integration`, `:41`; the fixture at `:48-60` drops `public`);
- `tests/cli/test_ledger_publication_cli.py`: `test_export_then_site_publishes_the_policys_projection`
  and `test_export_of_an_unknown_project_exits_1` (`:126-173`, per-test `integration`);
- `tests/cli/test_deploy_cli.py` (7 tests, `:50`);
- `tests/cli/test_forward_compatibility_columns.py` (marked by `fakes-harness-decouple`).

The seams already exist:
- `LedgerSearchCommand` and `LedgerExportCommand` take `open_app`, and resolve
  `CliComposition` at call time (`fakes-job-wakeup`);
- `AppResources.ledger_search` exists (`fakes-bootstrap-seam`);
- `InMemoryLedgerSearch` reproduces the SQL semantics case for case (`fakes-ledger-publication`).

## Required behaviour
1. **`test_ledger_search_cli.py`**:
   - drop the database fixture and `pytestmark`;
   - seed through `async with memory_app.open_app() as resources:` and `resources.ledger.append(...)`,
     using the same drafts the old seeding built;
   - invoke with `ops.invoke(memory_app, "ledger", "search", ...)` (`tests/cli/ops_support.py`).
   Every expected line of output stays.
2. **`test_ledger_publication_cli.py`**: the two `integration` tests move to the in-memory app.
   Use `InMemoryShardStore` where the command's store is injectable, or `tmp_path` with the real
   `JsonlShardStore`. The file system is not an outside service. Remove their marks.
3. **`test_deploy_cli.py`**: the same move. Deploy state is `InMemoryDeploymentStateStore`, or
   the real file repository under `tmp_path`.
4. **`test_forward_compatibility_columns.py`**: the rows "a newer vibey wrote" are written
   straight into the fakes' stores (`InMemoryQueueStore.jobs`, `InMemoryProjectRepository`'s
   records), bypassing the ports, as the old test bypassed them with SQL. Remove the mark.
5. Remove these modules from `PER_TEST_MODULES` in `tests/meta/test_integration_tier.py`
   where present, and lower the baseline entries.
6. If a case can only be answered by PostgreSQL, keep it in an `integration`-marked
   `tests/cli/test_<module>_postgres.py`, with the reason.

## Where to change
- The four test modules; `tests/cli/ops_support.py` (any new seed helper);
  `tests/meta/test_integration_tier.py`; `tests/meta/patching_baseline.json`.

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider -m "not integration" tests/cli/test_ledger_search_cli.py tests/cli/test_ledger_publication_cli.py tests/cli/test_deploy_cli.py tests/cli/test_forward_compatibility_columns.py`
      passes with PostgreSQL stopped, and collects as many tests as before.
- [ ] 100% `cli/` coverage.

## Tests to write first (TDD)
- Move one test at a time. There are no new behaviours.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/cli tests/meta
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- Production code. CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-cli-operational-1` (for `tests/cli/ops_support.py`).
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** the protected tests.
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
See STORM/SPEC-TEMPLATE.md.
