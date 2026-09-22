## Title
ci!: the default test run needs no service, and the gates and no-loss jobs prove the four 100% floors with nothing running

## Why
This is the lane where the operator's standard becomes the default:
- "no outside thing is ever needed in order to run tests";
- ADR-0023's four per-layer 100% floors are met **in code**. No floor is lowered and no path
  is excluded.

Every earlier fakes lane moved a suite onto in-memory fakes at declared seams. Today:
- `addopts` still selects the `integration` tier (`pyproject.toml:262`: `-m 'not paid'`);
- the `gates` job (`.github/workflows/ci.yml:30-102`) and the `noloss` job (`:104-140`) both
  start a PostgreSQL service, because until `fakes-harness-decouple` the root conftest
  connected in every session;
- the pre-push hooks (`.pre-commit-config.yaml:11-45`) run the default selection, so they
  need PostgreSQL too.

After the flip, the default selection excludes `integration`. Two jobs keep the real-service
tier honest:
- `postgres-compatibility` already runs PostgreSQL 14–18 (`:141-193`). Its command passes
  paths **without** `-m`. After the flip, `addopts` would deselect every integration test in
  those paths and the job would pass vacuously. It must say `-m integration`;
- the RabbitMQ tier (R32) keeps its own broker job.

## Required behaviour
1. **`pyproject.toml`**: `addopts = "-m 'not paid and not integration' -n auto --maxprocesses=8 --dist=loadgroup"`.
   Update the comment above it to say that the default tier needs no outside service, that
   `-m integration` selects the opt-in tier, and that its services are named by
   `VIBEY_TEST_*` variables.
2. **`.github/workflows/ci.yml`**:
   - `gates`: delete `services:` and the `VIBEY_TEST_DATABASE_URL` env. The test step and the
     four coverage gates are unchanged. They now measure the default tier.
   - `noloss`: delete `services:` and its database env. The command is unchanged: its own
     `-m noloss` overrides `addopts`.
   - `postgres-compatibility`: the test step becomes
     `uv run pytest -q -p no:cacheprovider -m "integration and not paid" tests`. That is the
     whole integration tier on each major. `not paid` stays, because an explicit `-m` replaces
     `addopts`' selection, and a test marked both must never spend money in CI. A RabbitMQ test
     in it skips without `VIBEY_TEST_AMQP_URL`.
     Keep the job name, matrix and image (`tests/meta/test_postgres_support_matrix.py`).
   - Put a comment on each changed job naming the operator's standard and this lane.
3. **`.vibey-gh.toml`**: add `"PostgreSQL 17 compatibility"` to `required_checks` (`:138`, and
   the list at `:158` if it names the same checks). The integration tier then gates merges
   exactly as `gates` does. PostgreSQL 17 is ADR-0002's version.
4. **`.pre-commit-config.yaml`**: unchanged. Its `uv run pytest` inherits the new default.
   Add a comment on `test-suite` and `coverage-gates` saying that they need no service. If
   T18 has already replaced these hooks with one harness request, leave T18's hook as it is.
   It inherits the default too.
5. **`tests/meta/test_ci_tiers.py`** (new) holds the tiers in place:
   - `test_gates_and_noloss_start_no_service`: YAML-load `ci.yml`, and assert that neither job
     has `services`;
   - `test_postgres_compatibility_selects_the_integration_tier`: its test step contains
     `-m "integration and not paid"`;
   - `test_default_addopts_exclude_integration_and_paid`;
   - `test_pending_fakes_are_only_in_flight_harness_seams`: every value in `PENDING`
     (`tests/fakes/registry.py`) matches `^(harness-T\d\d-|fakes-test-harness$)`.
6. **Prove it.** Run the default tier with coverage in a shell where PostgreSQL is stopped
   (or `VIBEY_TEST_DATABASE_URL` points at port 1). All four floors must pass. If a layer
   falls short, **do not change the floor, the include globs, or `[tool.coverage]`**. Stop,
   and list the uncovered lines and the lane that should have covered them.

## Where to change
- `pyproject.toml` (`addopts` and its comment), `.github/workflows/ci.yml` (three jobs),
  `.vibey-gh.toml` (`required_checks`), `.pre-commit-config.yaml` (comments only),
  `tests/meta/test_ci_tiers.py` (new).

## Acceptance criteria
- [ ] With PostgreSQL stopped:
      `uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=`,
      then the four `coverage report --include='src/vibey/<layer>/*' --fail-under=100`
      commands, all pass.
- [ ] With PostgreSQL: `uv run pytest -q -p no:cacheprovider -m "integration and not paid" tests` passes.
- [ ] `uv run python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` passes, and so do the meta tests.
- [ ] `git diff --stat HEAD~1` shows no change to `[tool.coverage]` or to any `--fail-under` value.

## Tests to write first (TDD)
`tests/meta/test_ci_tiers.py` (behaviour 5).

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/meta
    VIBEY_TEST_DATABASE_URL=postgresql://nobody@127.0.0.1:1/none env -u VIBEY_PG_URL uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    uv run coverage report --include='src/vibey/application/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100
    uv run pytest -q -p no:cacheprovider -m "integration and not paid" tests
    uv run bandit -q -r src/vibey

## Out of scope
- Tenant CI rows (the tenant lanes).
- Routing CI through the test harness (T19; see amendment A5).
- CLAUDE.md's commands block and CONTRIBUTING.md (the docs wave).
- CHANGELOG.md, docs/, ADRs, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally as `ci!: …`, with a `BREAKING CHANGE:` footer: "a bare `pytest`
no longer runs the integration tier; pass `-m integration` with `VIBEY_TEST_DATABASE_URL` set".

## Lane card
- **Depends on:** `fakes-isolation-guard`, `fakes-db-sql-transcripts`, `fakes-cli-ledger-deploy`,
  `fakes-cli-main-providers`, `fakes-cluster-preflight`, `fakes-contracts-repositories`,
  `fakes-contracts-surfaces`, `fakes-deploy-review`, `fakes-root-stragglers`. The rest arrive
  transitively. Through `fakes-db-sql-transcripts`, it waits for `orm-unit-of-work`, because
  `infrastructure/db` cannot meet its floor without PostgreSQL until the unit of work exists.
- **Must land before:** `harness-T28-route-flip` (amendment A6).
- **Files touched:** see *Where to change*.
- **Shares a file with:** `.github/workflows/ci.yml` (R32, R34, T19; if T19 has landed, keep
  its `vibey test run --backend local --fresh` wrapping, and change only the selection and
  services); `pyproject.toml` (R03, T07, T28); `.vibey-gh.toml`.
- **Must keep passing unchanged:** `tests/meta/test_postgres_support_matrix.py`,
  `tests/meta/test_tools_matrix_covers_every_package.py`, every job name, and the protected tests.
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
