## Title
test(agyloop): the agent launcher, harness retarget, doctor and run directory take their OS and process collaborators by injection, and the agyloop ratchet reaches zero

## Why
The second half of agyloop's patching is in its infrastructure tests:
- `tests/infrastructure/test_infrastructure_coverage.py` (43), `tests/infrastructure/agent/test_gateway_coverage.py` (28),
  `test_harness_retarget_more.py` (16), `tests/infrastructure/test_doctor_env.py` (14),
  `tests/application/test_application_coverage.py` (14), `test_stream_ui.py` (10),
  `test_gemini_rewrite.py` (7) and `test_cli_argv.py` (6);
- they patch:
  - `agyloop.infrastructure.agent.cli_argv.os.geteuid` ×7 and `validate_unsafe_skip_permissions`;
  - `agyloop.infrastructure.agent.harness_retarget._active` ×4 and `_maybe_start_proxy` ×3;
  - `agyloop.infrastructure.doctor_env.stock_harness_path` ×4, `cache_dir` ×3 and `smoke_check_harness` ×2;
  - `agyloop.infrastructure.rundir.os.kill`, `os.fsync` and `list_run_directories`;
  - `subprocess.Popen` ×2, `subprocess.run` ×2, `shutil.which` ×2, and `os.killpg` set to `None`;
  - the SDK `Agent` class ×11.

## Required behaviour
1. **One small OS seam for the tenant:** `agyloop/infrastructure/interfaces/os_interface.py`
   declares `ProcessOs` with `geteuid`, `kill`, `killpg`, `fsync`, `popen`, `run` and `which`.
   The production `SYSTEM_OS` class wraps `os`, `subprocess` and `shutil`. `cli_argv`,
   `rundir`, `harness_retarget` and `doctor_env` take it by keyword.
2. **Module-level state becomes owned state.**
   - `harness_retarget._active`, a module global, becomes an attribute of a
     `HarnessRetarget` instance, and `_maybe_start_proxy` becomes a method taking an injected
     proxy starter;
   - `doctor_env`'s `stock_harness_path`, `cache_dir` and `smoke_check_harness` become
     constructor keywords of a `DoctorEnv` class, with the production defaults.
   Each new class gets an interface (ADR-0016).
3. **The SDK agent.** The gateway takes `agent_factory` (default: the SDK's `Agent`).
   `tests/application/fakes.py` gains `ScriptedAgent`, which scripts turns, tool calls,
   failures and cancellation, and records prompts, alongside `FakeProcessOs`, which models a
   PID table, euid, fsync calls, and scripted `Popen` and `run` results.
4. **Switch the listed modules.** Every patch goes. The agyloop ratchet reaches zero, apart
   from entries carrying a written reason.

## Where to change
- `src/agyloop/infrastructure/agent/cli_argv.py`, `agent/harness_retarget.py`, `agent/gateway*.py`,
  `doctor_env.py`, `rundir.py`, and `infrastructure/interfaces/` (the new interface files).
- `tests/application/fakes.py`, `tests/application/test_port_parity.py`, `tests/patching_baseline.json`, and the listed test modules.

## Acceptance criteria
- [ ] `python -c "import json; print(json.load(open('src/vibey_runners/agy/tests/patching_baseline.json')))"` prints `{}`, or only entries with a reason.
- [ ] agyloop's CI row passes on each supported Python.

## Tests to write first (TDD)
`tests/application/test_fakes.py` (append):
- `test_fake_process_os_models_pids_and_euid`
- `test_scripted_agent_turns_and_cancellation`

## Checks the lane must run (all must pass)
    cd src/vibey_runners/agy && python -m pytest -q
    cd src/vibey_runners/agy && mypy --strict src/agyloop && lint-imports && bandit -q -r src/agyloop
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- The `system` and `live` tiers. CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-tenant-agy-1`.
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
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
