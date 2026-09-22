## Title
feat(test-harness)!: pytest runs, engine sessions and the cluster route test runs through the harness queue

## Why
Draft ADR-0045 §15: first serialize, then queue. By this lane, each piece has landed behind its
default and is green: the machine lock (harness-T07), the single gated push request (T18), CI's
always-fresh route (T19), the `rabbitmq` backend with its announced `auto` degrade (T25), the engine
route (T26) and the cluster Deployment (T27). This lane flips **only defaults**, so reverting its one
commit restores the `locked` behaviour exactly: CDD's bounded divergence (sub-doctrine 9.c).

The ADR made this lane wait for the ratification of 8.e with the reuse-window amendment. That is
done: 8.e is ratified on the integration branch with "while that result is still valid" and "a
request may always ask for a fresh run" (`src/vibey_tools/gh/docs/doctrines.md:271-292`).

Amendment A6 (`specs/ADR-test-harness-fakes-amendment.md:161-181`): `pytest` in a fresh clone with
nothing running must still pass. So this lane also waits for lane fakes-ci-no-services (the default
tier needs no service) and lane fakes-harness-degrade (a missing prerequisite — no broker, no writable
`state_dir`, no command executable — is an announced direct run, never a failure), and its acceptance
"run twice, `executed` then `reused`" must hold in a clone with nothing running.

## Required behaviour
1. **`pyproject.toml`**: `vibey_harness_route = "queue"` in `[tool.pytest.ini_options]` (harness-T07
   set it to `locked`). Its comment names 8.e, ADR-0045 and the bypasses: `VIBEY_HARNESS_ROUTE=off`
   runs directly; `VIBEY_HARNESS_ROUTE=locked` serializes only.
2. **`TestHarnessConfig.route_engines`** (`src/vibey/domain/config.py`, harness-T05a) defaults to
   `"queue"`. harness-T05a's `test_test_harness_defaults` asserts the new default: the only edit to an
   existing assertion.
3. **`deploy/helm/vibey/values.yaml`**: `testHarness.enabled: true`. Regenerate the goldens with
   `deploy/helm/golden/render.sh --update`: `default.yaml` gains the Deployment and the loop-service
   variables; the `keda-*` goldens stay byte-identical.
4. **The commit carries a `BREAKING CHANGE:` footer**: a root `pytest` run is now a test-harness
   request, answered from the record while that record is valid and otherwise executed once per
   machine; `VIBEY_HARNESS_ROUTE=off` restores a direct run; engine sessions carry the route; the
   chart runs a `test-harness` Deployment by default (`testHarness.enabled=false` opts out), and it
   needs a broker.

## Where to change
- `pyproject.toml` (the ini value and its comment), `src/vibey/domain/config.py` (one default),
  `tests/domain/test_config.py` (one assertion), `deploy/helm/vibey/values.yaml`, `deploy/helm/golden/*`
  (regenerated), `tests/cli/test_pytest_route.py` (one appended test).
  This lane stays one commit across these files on purpose: it is the single revertible flip ADR-0045 §15 asks for.

## Acceptance criteria
- [ ] In a clean clone with nothing running (no PostgreSQL, no broker), `uv run pytest -q -p no:cacheprovider tests/domain`, run twice, prints `executed` and then `reused` on its first line, with exit 0 both times.
- [ ] The whole-suite coverage run and the four per-layer reports pass; `.coverage` is restored by the harness (ADR-0045 §8).
- [ ] `VIBEY_HARNESS_ROUTE=off uv run pytest -q -p no:cacheprovider tests/cli/test_pytest_route.py` runs directly.
- [ ] `render.sh` passes, and the `keda-*` goldens are unchanged.
- [ ] `git diff --stat HEAD~1` shows no protected file.

## Tests to write first (TDD)
- Update harness-T05a's `test_test_harness_defaults` (behaviour 2).
- `tests/cli/test_pytest_route.py` (appended): `test_the_repository_ini_routes_to_the_queue`, which
  reads `pyproject.toml` with `tomllib` and asserts `vibey_harness_route == "queue"`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain
    uv run pytest -q -p no:cacheprovider tests/domain
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    uv run coverage report --include='src/vibey/application/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100
    VIBEY_HARNESS_ROUTE=off uv run pytest -q -p no:cacheprovider tests/cli/test_pytest_route.py
    deploy/helm/golden/render.sh
    git diff --stat HEAD~1 -- tests/domain/test_noloss*.py tests/domain/test_briefing.py tests/infrastructure/db/test_chaos.py tests/system/test_delivery_stage_set.py tests/live

## Out of scope
- Docs, ADRs, CHANGELOG, CONTRIBUTING.md and the agent-surface trees: the docs wave owns them, as ADR-0045's *Owes* line lists.
- The storm driver: exporting `VIBEY_HARNESS_ROUTE=queue` for tenant-directory runs, and passing qwenloop's `shell_timeout_seconds`, are operator steps (ADR-0045 "Where the drafted rule conflicts" item 6).
- The canon text of 8.e (ratified).

Do not push, open a pull request or change remotes. Commit locally as `feat(test-harness)!: …` with the `BREAKING CHANGE:` footer.

## Lane card
- **Depends on:** harness-T16-test-inspect-cli, harness-T17-pytest-queue-route, harness-T18-hooks-route, harness-T19-ci-route, harness-T25-harness-backend-selection, harness-T26-engine-route-env, harness-T27-chart-test-harness, fakes-ci-no-services, fakes-harness-degrade (amendment A6).
- **Files touched:** see *Where to change*.
- **Shares a file with:** `pyproject.toml` (after harness-T07 and fakes-ci-no-services); `domain/config.py` (after rmq-r34); the chart (after harness-T27).
- **Must keep passing unchanged:** the entire suite, now run *through* the harness, including all protected tests; the `keda-*` goldens; `tests/infrastructure/db/test_keda_scaler_query.py`.
- **Registry (amendment A4):** nothing.
- **Standing constraints (every harness lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Never `monkeypatch.setattr`, `mock.patch` or `MagicMock`; default-tier tests need nothing outside the process (ADR-0045 amendment A1; lane fakes-isolation-guard's audit hook fails a default-tier test that reaches out).
  - Never hand-edit a golden.
  - Edit existing files with `edit_file`, never rewrite a test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
