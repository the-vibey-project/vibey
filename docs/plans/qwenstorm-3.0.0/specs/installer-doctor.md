## Title
feat(cli): `vibey doctor` reports one line per local-stack dependency, with the command that fixes it

## Why
`vibey doctor` checks the engines and PostgreSQL only (src/vibey/cli/main.py:1185-1391; the
PostgreSQL line is printed at :1341). The operator's standard (2026-09-22) requires the
installer to install everything on the default OSes. The companion check is that doctor says,
per dependency, what is missing and how to fix it. #391 asked for this for Ollama and the
model; the catalogue makes it uniform for every default dependency.

The stack check reuses the same port and presenter as `vibey install --check` (lane
installer-cli), so the two can never disagree (sub-doctrine 10.e). It is substituted in tests
through the typer context's `obj`, never by patching (9.b).

## Required behaviour
1. `InstallCommand` (`src/vibey/cli/local_install.py`) gains
   `doctor_lines(*, model: str = DEFAULT_LOCAL_MODEL) -> list[str]`, and
   `InstallCommandInterface` gains the same method.
   - With a None host it returns one line:
     f"local stack: {factory.host_label()} is not a default OS (Arch Linux, macOS); only PostgreSQL is checked".
     It runs no command.
   - Otherwise it resolves `catalogue.resolve(host, exclude=("postgres",))`. PostgreSQL keeps
     its existing line. It builds with `model`, calls `check()` only, and returns
     `presenter.lines(report)`.
2. `doctor` in `src/vibey/cli/main.py` takes `ctx: typer.Context` as its first parameter.
   - When it is not `--cluster`, it computes the stack lines before `asyncio.run(run_doctor())`,
     beside the postgres status at :1245-1251. It uses
     `factory = ctx.obj if isinstance(ctx.obj, LocalStackFactory) else LocalStackComposition()`
     and `model = os.environ.get(OLLAMA_MODEL_ENV) or DEFAULT_LOCAL_MODEL`.
   - It prints the lines immediately after the postgresql line (:1341).
   - `--cluster` output is unchanged and computes no stack lines.
3. Doctor's exit code is unchanged: the stack lines are informational. Existing doctor output
   lines and their order are unchanged, and the new lines only follow the postgresql line.
4. On a non-default host, such as CI's Ubuntu, the stack check is one line and runs no command.
   Existing doctor tests that pass no `obj` therefore stay hermetic in CI.

## Where to change
- `src/vibey/cli/local_install.py` and `src/vibey/cli/interfaces/local_install_interface.py`:
  add the method.
- `src/vibey/cli/main.py` `doctor`: use edit_file only; the file is 1761 lines.
- `tests/cli/test_local_install.py`: append tests, reusing its `FakeFactory`.
- Test `doctor_lines` directly for the stack logic. The `CliRunner` doctor tests (ordering,
  model env, exit code, `--cluster`) must also get past the engine preflight, which is
  existing code outside this lane. Pass `--engine claudeloop`, and stub the preflight exactly
  as the existing doctor tests do (tests/cli/test_operational_commands.py:939-947). The stack
  itself comes only from `obj=FakeFactory(...)`.

## Acceptance criteria
- [ ] On a fake Arch factory, doctor prints, after the postgresql line, one line per default
      dependency except postgres. A MISSING docker line is followed by
      `fix: vibey install --only docker`.
- [ ] `doctor_lines` calls `check()` only, never `install()`.
- [ ] A fake non-default host gives the single "not a default OS" line.
- [ ] `vibey doctor --cluster` output is unchanged. The existing `--cluster` tests pass
      untouched.
- [ ] `VIBEY_OLLAMA_MODEL`, set through `CliRunner(env=...)`, reaches `factory.build(model=...)`.
- [ ] Doctor's exit code is 0 when only stack dependencies are missing.
- [ ] Every existing test in `tests/cli/test_operational_commands.py` passes unchanged. 100%
      branch coverage of `src/vibey/cli/*`.

## Tests to write first (TDD)
Append to `tests/cli/test_local_install.py`:
- `test_doctor_lists_each_stack_dependency_after_postgres`
- `test_doctor_stack_check_never_installs`
- `test_doctor_on_a_non_default_host_says_so_once`
- `test_doctor_uses_the_configured_model`
- `test_doctor_exit_code_ignores_missing_stack_dependencies`
- `test_cluster_doctor_prints_no_stack_lines`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/cli
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- R33's broker and loop-service checks (#380).
- Making missing dependencies fail doctor. Doctor stays informational; `vibey install --check`
  exits non-zero.
- `--install-postgres`.
- Docs.

Commit as `feat(cli): ...`. Do not push.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
