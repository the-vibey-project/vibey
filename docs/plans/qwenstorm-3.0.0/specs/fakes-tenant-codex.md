## Title
test(codexloop): the CLI commands take their readers, probes and clock from a typer-context composition, shared fakes come from runners-common, and the ratchet starts

## Why
codexloop (`src/vibey_runners/codex`) makes 84 `monkeypatch.setattr` calls. Most replace
functions imported into its command modules:
- `test/cli/test_ops_commands.py`, 24 calls (`:83-203`):
  - `codexloop.cli.commands.capacity.read_capacity_windows`;
  - `doctor.run_doctor_checks`;
  - `watch.read_run_state`, `watch.run_is_live` and `watch.time.sleep`;
  - `wind_down_cmd.enqueue_run_control`;
- `tests/test_bootstrap.py`, 13 calls: `codexloop.bootstrap.probe_app_server_transport` ×4;
- `tests/cli/test_asyncio.py`, 10 calls: `cli_asyncio.asyncio`;
- `tests/infrastructure/api/test_gateway.py`, 9 calls;
- `tests/infrastructure/test_lock.py`, 4 calls: `codexloop.infrastructure.lock.os.link` and `os.kill`.

`tests/application/fakes.py` already holds 18 fake classes, but several of them fake ports
that `vibey-runners-common` now ships fakes for (`fakes-tenant-common`: Clock, Sleeper,
StreamUi, RunControl, ControlInbox, Logger, StateBus, RunStateStore, SessionLock, ApiGateway).

## Required behaviour
1. **Shared fakes from the family (10.e).** For each class in `tests/application/fakes.py`
   that fakes a `vibey_runners.common` port, delete it and import the one from
   `vibey_runners.common.testing.fakes`. Fakes of codexloop's own ports stay. Complete them
   where a method is a stub; the parity test will name them.
2. **`codexloop/cli/composition.py` — `class CodexloopComposition`**, with an interface,
   found through `click.get_current_context(silent=True).find_object(...)`, like vibey's
   `CliComposition`. Its fields default to the functions the tests patch today:
   `read_capacity_windows`, `run_doctor_checks`, `read_run_state`, `run_is_live`,
   `enqueue_run_control`, `sleep`, and `probe_app_server_transport` for bootstrap. Each command
   module reads them from `current()`.
3. **Infrastructure seams:**
   - `infrastructure/lock.py` takes `link` and `kill` callables with the `os` defaults, or a
     small `ProcessOs` interface. Its tests inject a `FakeProcessOs` that models a PID table
     and hard links in a dict;
   - `infrastructure/api/gateway.py`: whatever `test_gateway.py` patches becomes a constructor
     keyword with the production default.
4. **`tests/cli/test_asyncio.py`'s `cli_asyncio.asyncio` patches** become an injected runner
   (`run: Callable[[Coroutine], T] = asyncio.run`) on the helper under test.
5. **The tenant registry and ratchet:** `tests/application/test_port_parity.py` (add it if
   absent, or extend it), `tests/test_patching_ratchet.py` and
   `tests/patching_baseline.json`. The converted files count zero.

## Where to change
- `src/codexloop/cli/composition.py` (new) and its interface; the command modules named above;
  `src/codexloop/bootstrap.py`; `infrastructure/lock.py`; `infrastructure/api/gateway.py`; the CLI asyncio helper.
- `tests/application/fakes.py`, `tests/application/test_port_parity.py`, `tests/test_patching_ratchet.py`,
  `tests/patching_baseline.json`, and the five test modules above.

## Acceptance criteria
- [ ] `grep -c "monkeypatch.setattr" src/vibey_runners/codex/tests/cli/test_ops_commands.py src/vibey_runners/codex/tests/test_bootstrap.py src/vibey_runners/codex/tests/infrastructure/test_lock.py` prints `0` for each.
- [ ] codexloop's CI row passes (install `../common`, then `.[dev]`, then its `test` and `static`).

## Tests to write first (TDD)
- `tests/cli/test_composition.py`:
  - `test_defaults_are_production`
  - `test_context_object_is_found`
- `tests/application/test_fakes.py` (append): `test_fake_process_os_models_links_and_pids`

## Checks the lane must run (all must pass)
    cd src/vibey_runners/codex && pip install -e ../common && pip install -e ".[dev]" && python -m pytest -q
    cd src/vibey_runners/codex && mypy --strict src/codexloop && lint-imports && bandit -q -r src/codexloop
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- The `live` and `system` tiers (`-m "not live and not system"` already deselects them;
  `tests/live/**` in codexloop is its own opt-in tier).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-tenant-common`.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** codexloop's `shim` fakes (`tests/shim/fake_codex.py`,
  `fake_appserver.py`), which are already honest process-level fakes, and the protected root tests.
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
