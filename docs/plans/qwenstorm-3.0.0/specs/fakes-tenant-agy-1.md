## Title
test(agyloop): the CLI and bootstrap take their runner, bus, tail and savepoint collaborators from a typer-context composition, and the CLI tests patch nothing

## Why
agyloop (`src/vibey_runners/agy`) has 165 `patch` calls, 96 mocks and 17 `setattr`s. The
operator's list names agyloop as a single lane, but at that size one lane would fail, so it is
split in two ("small, concrete lanes succeed"). This first half covers the CLI and
`bootstrap`:
- `tests/cli/test_cli_coverage.py` (36), `tests/test_cli.py` (15),
  `tests/cli/test_wind_down_exit.py` (7) and `tests/test_ops_cli.py`;
- they patch `agyloop.bootstrap.build_runner` ×6, `watch_bus` ×3, `tail_events` ×2,
  `list_savepoints` ×2 and `emit_snapshot` ×2, plus
  `agyloop.cli.commands.resume.resolve_last_run` ×2 and `sys.stdout.isatty` ×2.

## Required behaviour
1. **`agyloop/cli/composition.py` — `class AgyloopComposition`**, with an interface, found
   through `click.get_current_context(silent=True).find_object(...)`. Its fields default to
   production:
   - `build_runner`, `watch_bus`, `tail_events`, `list_savepoints`, `emit_snapshot`;
   - `resolve_last_run`;
   - `is_tty`, defaulting to `sys.stdout.isatty`.
   The CLI command modules read them through `current()`. `bootstrap.py` keeps the production
   functions, which are the defaults.
2. **`tests/application/fakes.py`**:
   - delete fakes of `vibey_runners.common` ports and import them from
     `vibey_runners.common.testing.fakes`;
   - add `ScriptedRunnerGraph`, which `build_runner` returns over the in-memory fakes;
   - add `InMemoryEventBus`: `watch_bus` yields recorded events, and `tail_events` yields a
     scripted tail;
   - add `InMemorySavepoints`: a list, and `emit_snapshot` appends to it;
   - add `ScriptedRunResolver`.
3. **Switch the four CLI test modules** to `obj=AgyloopComposition(...)`. Every
   `patch("agyloop.bootstrap...` and `patch("agyloop.cli...` goes, and so does
   `patch("sys.stdout.isatty")`.
4. **The tenant registry and ratchet:** `tests/application/test_port_parity.py`,
   `tests/test_patching_ratchet.py`, `tests/patching_baseline.json`.

## Where to change
- New `src/agyloop/cli/composition.py` and its interface; the command modules that call the listed names.
- `tests/application/fakes.py`, `tests/application/test_port_parity.py`, `tests/test_patching_ratchet.py`, `tests/patching_baseline.json`,
  `tests/cli/test_cli_coverage.py`, `tests/test_cli.py`, `tests/cli/test_wind_down_exit.py`, `tests/test_ops_cli.py`.

## Acceptance criteria
- [ ] `grep -cE "patch\(\"agyloop\.(bootstrap|cli)|isatty" src/vibey_runners/agy/tests/cli/*.py src/vibey_runners/agy/tests/test_cli.py src/vibey_runners/agy/tests/test_ops_cli.py` prints `0` for each.
- [ ] agyloop's CI row passes.

## Tests to write first (TDD)
- `tests/cli/test_composition.py`:
  - `test_defaults_are_production`
  - `test_context_object_is_found`
- `tests/application/test_fakes.py` (append):
  - `test_event_bus_fake_watches_and_tails`
  - `test_savepoints_fake`

## Checks the lane must run (all must pass)
    cd src/vibey_runners/agy && pip install -e ../common && pip install -e ".[dev]" && python -m pytest -q
    cd src/vibey_runners/agy && mypy --strict src/agyloop && lint-imports && bandit -q -r src/agyloop
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- `agyloop/infrastructure/*` (`fakes-tenant-agy-2`). CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-tenant-common`.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** agyloop's `system` and `live` tiers (deselected by `addopts`), and the protected root tests.
- **Standing constraints (every tenant lane):**
  - The tenant's own gates and floor pass on its Python floor (ADR-0022).
  - A fake is a plain class with real in-memory behaviour, and never `unittest.mock`.
  - Substitution happens at a declared seam: a constructor or keyword argument, a typer
    `ctx.obj`, or a parameter with a production default. It never happens by patching an
    import. `monkeypatch.setenv` and `delenv` stay allowed.
  - The tenant keeps its own registry and parity test and its own patching ratchet
    (`test_patching_ratchet.py` plus `patching_baseline.json`) in its test directory. Lower
    the ratchet for every file you convert, and never raise it.
  - Line 1 of every new file is the provenance line, copied byte-for-byte from a sibling file.
  - Protected root tests are never edited. Change existing files with `edit_file`, and never
    rewrite an existing test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
