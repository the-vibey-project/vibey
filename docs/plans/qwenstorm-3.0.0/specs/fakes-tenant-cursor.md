## Title
test(cursorloop): the API gateway, doctor and CLI take their HTTP client, SDK and bootstrap by injection, shared fakes come from runners-common, and the ratchet reaches zero

## Why
cursorloop (`src/vibey_runners/cursor`) makes 37 `patch` calls and 16 `setattr` calls, with 7 mocks:
- `tests/infrastructure/test_infra_full_coverage.py` (22) patches
  `cursorloop.infrastructure.api.gateway.httpx.Client` (`:586`) and `gateway.redact` (`:580`),
  and `cursorloop.infrastructure.doctor_env.Cursor.me` and `Cursor.models.list` (`:681-710`);
- `tests/cli/test_control_doctor_resume.py` (14) patches `cursorloop.cli.commands.doctor.run_doctor`
  and `cursorloop.cli.commands.resume.bootstrap.build_runner`;
- `tests/infrastructure/test_coverage_gaps.py` (7), `tests/cli/test_app_main_asyncio.py` (5)
  (`cursorloop.cli.app.app` ×4), and `tests/bootstrap/test_build_runner_bridge.py` (4)
  (`cursorloop.bootstrap.open_live_bridge` ×2);
- `setattr` on `os` ×4, `sys`, `runner_mod.random` and `builtins.__import__`.

cursorloop already has `tests/application/test_fakes_satisfy_ports.py`, the precedent for a
tenant parity test, and 14 fakes in `tests/application/fakes.py`.

## Required behaviour
1. **Shared fakes.** Fakes of `vibey_runners.common` ports come from
   `vibey_runners.common.testing.fakes`. Extend `test_fakes_satisfy_ports.py` into the full
   parity check: signatures, not-a-stub, and "every port registered".
2. **The HTTP client.** `infrastructure/api/gateway.py` takes
   `client_factory: Callable[..., httpx.Client]`, whose default is `httpx.Client`. Tests pass
   `lambda **kw: httpx.Client(transport=httpx.MockTransport(handler), **kw)`. `MockTransport`
   is httpx's own in-memory transport, which is a declared seam, not a patch. The handler is an
   in-memory router class, `InMemoryCursorApi` in `tests/application/fakes.py`. `redact` is
   pure, so tests call it for real.
3. **The doctor.** `doctor_env` takes a `cursor_client` factory (default: the SDK's `Cursor`),
   and tests pass a `ScriptedCursorSdk` (`me()`, `models.list()`, scripted failures).
4. **The CLI.** A `CursorloopComposition`, found through the typer context like the other
   runners', holds `run_doctor`, `build_runner` and `open_live_bridge`. The CLI and
   `resume` read them from it. The `cursorloop.cli.app.app` patches in
   `test_app_main_asyncio.py` become invocations of the real app with a composition.
5. **The stragglers.** `runner_mod.random` becomes an injected `random: Callable[[], float]`
   on the runner. The `builtins.__import__` patch, which simulates a missing optional
   dependency, becomes an injected `importer` on the one function that does the optional
   import. The `os` and `sys` sets become keyword seams where they select behaviour. Use
   `monkeypatch.setenv` where they were only environment.
6. **The ratchet.** Add `tests/test_patching_ratchet.py` and `tests/patching_baseline.json`,
   and bring them to zero, apart from entries carrying a written reason.

## Where to change
- `src/cursorloop/infrastructure/api/gateway.py`, `infrastructure/doctor_env.py`, `cli/composition.py` (new), `cli/commands/doctor.py`, `cli/commands/resume.py`, `cli/app.py`, `bootstrap.py`, the runner module, and the interfaces for new classes.
- `tests/application/fakes.py`, `tests/application/test_fakes_satisfy_ports.py`, `tests/test_patching_ratchet.py`, `tests/patching_baseline.json`, and the listed test modules.

## Acceptance criteria
- [ ] `python -c "import json; print(json.load(open('src/vibey_runners/cursor/tests/patching_baseline.json')))"` prints `{}`, or only entries with a reason.
- [ ] cursorloop's CI row passes on each supported Python.

## Tests to write first (TDD)
`tests/application/test_fakes.py`:
- `test_in_memory_cursor_api_routes_and_errors`
- `test_scripted_cursor_sdk`

`tests/cli/test_composition.py`:
- `test_defaults_are_production`

## Checks the lane must run (all must pass)
    cd src/vibey_runners/cursor && pip install -e ../common && pip install -e ".[dev]" && python -m pytest -q
    cd src/vibey_runners/cursor && mypy --strict src/cursorloop && lint-imports && bandit -q -r src/cursorloop
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- The `live` and `system` tiers. CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-tenant-common`.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** the protected root tests.
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
See STORM/SPEC-TEMPLATE.md.
