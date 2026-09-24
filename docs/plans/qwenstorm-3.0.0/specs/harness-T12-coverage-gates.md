## Title
feat(test-harness): coverage gates run inside the run, and the run's data is kept for reuse

## Why
Draft ADR-0045 §8. The pre-push hook runs four `coverage report --fail-under=100` gates after the
suite (`.pre-commit-config.yaml:40-45`), and CI runs the same four as separate steps that read
`.coverage` in the checkout (`.github/workflows/ci.yml:75-85`). If the gates ran outside the
harness, a cached answer would leave them reading whatever `.coverage` the last execution in that
directory wrote. So:
- the gates are part of the request, and run under the same machine lock against the run's
  **private** data file (ADR-0023's four floors are unchanged; only where they read changes);
- the run's data file is kept with its record and restored to `<cwd>/.coverage` both after
  execution and on reuse, so a later `coverage report` reads the data of the run that answered.

## Required behaviour
Create `src/vibey/infrastructure/test_harness/coverage.py`:
1. **`CoverageGates(*, coverage_command: tuple[str, ...], output_cap: int = 16384, timeout_seconds: float = 300.0)`**.
   `async def check(self, *, cwd: Path, data_file: Path, gates: Sequence[CoverageGateInterface], env: Mapping[str, str]) -> tuple[GateReport, ...]`
   (`CoverageGateInterface` from `vibey.domain.interfaces.test_harness_interface`, `GateReport` from
   `vibey.domain.test_harness_protocol`):
   - When `data_file` does not exist, return one failing `GateReport` per gate with
     `exit_code=-1` and `output=f"no coverage data at {data_file}"`. Spawn nothing.
   - Otherwise, for each gate in order, run
     `coverage_command + ("report", f"--data-file={data_file}", f"--include={gate.include}", f"--fail-under={gate.fail_under}")`
     with `asyncio.create_subprocess_exec` in `cwd` with `env`, stdout and stderr combined
     (`stderr=asyncio.subprocess.STDOUT`), bounded by `timeout_seconds`. On timeout kill the
     process, await it, and report `exit_code=-1` with output `f"coverage report exceeded {timeout_seconds:g}s"`.
     The report is `GateReport(include, fail_under, passed=(returncode == 0), exit_code=returncode, output=<the last output_cap characters>)`.
2. **`CoverageDataKeeper`**, stateless:
   - `keep(self, *, data_file: Path, keep_dir: Path) -> Path | None` copies an existing
     `data_file` to `keep_dir / "coverage"` (mode `0o600`) and returns that path; a missing file returns `None`;
   - `restore(self, *, kept: Path | None, cwd: Path) -> bool` copies `kept` to `cwd / ".coverage"`
     atomically (a temporary file in `cwd`, then `os.replace`) and returns `True`; it returns
     `False` when `kept` is `None` or missing.
3. **Interfaces**, `src/vibey/infrastructure/test_harness/interfaces/coverage_interface.py`:
   `@runtime_checkable` `CoverageGatesInterface` (`check`) and `CoverageDataKeeperInterface`
   (`keep`, `restore`).
4. **Registry (amendment A4).** In `tests/fakes/registry.py` (lane fakes-registry), import the
   interface module, append `CoverageGatesInterface` and `CoverageDataKeeperInterface` to
   `DRIVER_SEAMS`, and add `"CoverageGatesInterface": "fakes-test-harness"` and
   `"CoverageDataKeeperInterface": "fakes-test-harness"` to `PENDING` (fakes-test-harness registers
   `ScriptedCoverageGates` and `InMemoryCoverageDataKeeper`).

## Where to change
- New `src/vibey/infrastructure/test_harness/coverage.py` and its interface module.
- `tests/fakes/registry.py` (with `edit_file`).
- New `tests/infrastructure/test_harness/test_coverage.py`.

## Acceptance criteria
- [ ] With real data (made in the test with `(sys.executable, "-m", "coverage", "run", "--data-file=<tmp>", "<tmp module>")`), a gate of 100 on a module with an uncovered line fails with exit code 2, and a gate of 0 passes. This checks the ADR-0045 *Verification owed* facts that the locked coverage accepts `--data-file` and exits 2 below `--fail-under`. The gates' `coverage_command` in the test is `(sys.executable, "-m", "coverage")`, never `uv`.
- [ ] Missing data fails every gate without spawning anything (a `coverage_command` of a nonexistent binary proves nothing was spawned).
- [ ] The keeper round-trips, and a restore of nothing returns `False`.
- [ ] 100% coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
`tests/infrastructure/test_harness/test_coverage.py` (`from vibey.infrastructure.test_harness import coverage as cg`):
- `test_gate_passes_and_fails_on_real_data`
- `test_missing_data_fails_every_gate_without_spawning`
- `test_gate_output_is_capped`
- `test_gate_timeout_fails` (`coverage_command=(sys.executable, "-c", "import time; time.sleep(5)")`, `timeout_seconds=0.3`)
- `test_keeper_round_trip`
- `test_restore_of_nothing_is_false`
- `test_classes_satisfy_their_interfaces`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_harness tests/fakes tests/meta
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- When gates run (harness-T13). The hook's gate list (harness-T18). The scripted fakes (fakes-test-harness).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push, open a pull request or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** harness-T03-test-harness-messages, harness-T05-test-harness-config, fakes-registry.
- **Files touched:** the two new source files, `tests/fakes/registry.py`, the new test file.
- **Shares a file with:** `tests/fakes/registry.py` (append only).
- **Must keep passing unchanged:** `tests/fakes/*`, and the protected tests.
- **Standing constraints (every harness lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte for byte from line 1 of a sibling file:
    `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`
  - In test files import modules, not `Test*` names.
  - Never `monkeypatch.setattr`, `mock.patch` or `MagicMock`; default-tier tests need nothing outside the process (ADR-0045 amendment A1; lane fakes-isolation-guard's audit hook fails a default-tier test that reaches out); children of `sys.executable` are inside.
  - Every data file and cwd is under `tmp_path`. No test waits longer than 5 s.
  - Edit existing files with `edit_file`, never rewrite a test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
