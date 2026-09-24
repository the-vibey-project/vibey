## Title
ci: the root suites run through the test harness, always fresh, with nothing running

## Why
Two reasons, both in draft ADR-0045 §10 and "Where the drafted rule conflicts" item 3:
- **10.e** (`src/vibey_tools/gh/docs/doctrines.md:417`) says the family is used "in imports, in CI,
  and in operations": a project that ships a test harness it does not run in CI has not tested it.
- **8.b's sovereign forge default is self-hosted Forgejo**, whose runners *do* share a machine
  between jobs. There, the harness's machine lock is what keeps 8.e.

A verifier must produce its own evidence and never take a cached answer, so every CI request is
`--fresh` (8.e: "a request may always ask for a fresh run", `doctrines.md:283`). The four per-layer
coverage steps (`.github/workflows/ci.yml:75-85`) stay as they are: the harness restores `.coverage`
in the checkout from the run's private data (ADR-0045 §8). The tenant rows (`:195-`) are unchanged:
their venvs are built with plain pip and hold no vibey, and each row is a machine of its own.

**Amendment A5** (`specs/ADR-test-harness-fakes-amendment.md:152-159`): this lane lands after lane
fakes-ci-no-services, which makes the default tier need no service. So `gates` and `noloss` start
**no service** and keep the default selection, and `postgres-compatibility` runs the integration
tier explicitly, `-m "integration and not paid" tests`. A path list without `-m` would be
deselected by `addopts` and pass vacuously.

## Required behaviour
In `.github/workflows/ci.yml` only:
1. The jobs **`gates`**, **`noloss`** and **`postgres-compatibility`** each gain, in their job-level
   `env:`, `VIBEY_HARNESS_STATE_DIR: ${{ runner.temp }}/vibey-test-harness`. Add no `services:` to
   `gates` or `noloss` (fakes-ci-no-services removed them); keep `postgres-compatibility`'s.
2. **`gates`**: the step "Run test suite with coverage" (`:72-73`) becomes
   ```yaml
         # 10.e: CI runs the family's test harness; on self-hosted runners its machine lock keeps
         # 8.e. --fresh: a verifier produces its own evidence, never a cached answer (ADR-0045 §10).
         - name: Run test suite with coverage
           run: uv run vibey test run --backend local --fresh --full-output -- -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
   ```
3. **`noloss`** (`:138-139`): the run line becomes
   `uv run vibey test run --backend local --fresh --full-output -- -m noloss --hypothesis-profile=noloss --hypothesis-show-statistics -p no:cacheprovider`.
   `--full-output` prints the whole log, so the Hypothesis statistics this job exists to show
   (the comment at `:95-103`) are never cut to the output tail.
4. **`postgres-compatibility`** (`:188-193`): the step "Run PostgreSQL compatibility suite" becomes
   ```yaml
         - name: Run PostgreSQL compatibility suite
           run: >-
             uv run vibey test run --backend local --fresh --full-output --
             -q -p no:cacheprovider -m "integration and not paid" tests
   ```
   (fakes-ci-no-services's `tests/meta/test_ci_tiers.py` asserts this step contains
   `-m "integration and not paid"`; keep that exact text).
5. **Each of the three jobs** gains a last step:
   ```yaml
         - name: Test-harness dead letters (evidence)
           if: failure()
           run: uv run vibey test dead-letters
   ```
6. **`tests/meta/test_ci_routes_through_the_harness.py`** (new, module-level test functions, the
   reason `tests/meta/test_githooks_reach_the_framework.py:30-33` gives), loading `ci.yml` with
   `yaml.safe_load`:
   - `test_root_suites_run_through_the_harness_fresh`: in `gates`, `noloss` and
     `postgres-compatibility`, the step that runs the tests starts with
     `uv run vibey test run --backend local --fresh --full-output --`;
   - `test_each_root_job_keeps_its_state_dir_private`: each of the three jobs' `env` sets
     `VIBEY_HARNESS_STATE_DIR` under `${{ runner.temp }}`;
   - `test_each_root_job_shows_dead_letters_on_failure`: each has the dead-letters step with `if: failure()`;
   - `test_no_job_is_renamed`: the three jobs' `name` values are unchanged
     (`noloss` is a required check, `ci.yml:95-103`).

## Where to change
- `.github/workflows/ci.yml` (with `edit_file`) and the new meta test.

## Acceptance criteria
- [ ] `uv run python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` passes.
- [ ] `uv run pytest -q -p no:cacheprovider tests/meta` passes, including `test_ci_tiers.py` and `test_postgres_support_matrix.py`.
- [ ] Locally, with `VIBEY_HARNESS_STATE_DIR` pointing at a temporary directory, `uv run vibey test run --backend local --fresh -- -q -p no:cacheprovider tests/domain` exits 0 with nothing running.
- [ ] `uv run vibey test run --backend local --fresh -- -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report= tests/domain && uv run coverage report --include='src/vibey/domain/*'` shows the restored `.coverage` (ADR-0045 §8).

## Tests to write first (TDD)
- `tests/meta/test_ci_routes_through_the_harness.py` (behaviour 6).

## Checks the lane must run (all must pass)
    uv run python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"
    uv run pytest -q -p no:cacheprovider tests/meta
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- The tenant rows. A RabbitMQ service in CI (rmq-r32-ci-rabbitmq). `.vibey-gh.toml`'s required checks (fakes-ci-no-services adds the PostgreSQL 17 row).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push, open a pull request or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** harness-T15-test-run-cli, harness-T16-test-inspect-cli (the dead-letters step), fakes-ci-no-services (amendment A5).
- **Files touched:** `.github/workflows/ci.yml`, `tests/meta/test_ci_routes_through_the_harness.py` (new).
- **Shares a file with:** `ci.yml` (rmq-r32, rmq-r34 and fakes-ci-no-services; rebase on whichever landed, keeping their changes).
- **Must keep passing unchanged:** `tests/meta/test_postgres_support_matrix.py` (it pins the matrix and the image, not the command), `tests/meta/test_tools_matrix_covers_every_package.py`, `tests/meta/test_ci_tiers.py`, every job name, and the protected tests.
- **Registry (amendment A4):** nothing.
- **Standing constraints (every harness lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte for byte from line 1 of a sibling file:
    `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`
  - Never `monkeypatch.setattr`, `mock.patch` or `MagicMock`; the meta test only reads files.
  - Edit existing files with `edit_file`, never rewrite a test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
