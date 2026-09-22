## Title
feat(surfaces)!: queue is the default surface transport — every sovereign surface is reached through its lane

## Why
Sub-doctrine 8.f (`src/vibey_tools/gh/docs/doctrines.md`, "8.f — every sovereign surface runs
in one lane, driven by the bus", ratified): every surface "is reached through **a single lane per
deployment** … nothing opens a second path to a surface beside its lane." Until now every lane
landed behind `transport = direct` (draft ADR-0047 §15, `specs/ADR-surface-lanes.md`). §15:
"The last lane, S33, flips the default, but only once all of these hold: the lanes are merged and
cluster-smoke is green in `queue` mode; the §10 measurement is recorded; the operator has accepted
the cache cost in writing; 8.f is ratified." Then "`tests/conftest.py` pins
`VIBEY_SURFACES_TRANSPORT=direct` for the historical suite, as R34 does for the queue backend.
Every step can be reversed with one key (CDD, 9.c)." ADR-0047 lane S33.

## Precondition (check first; stop and report if any fails)
1. `grep -n "8.f — every sovereign surface runs in one lane" src/vibey_tools/gh/docs/doctrines.md`
   prints a line marked ratified.
2. `docs/architecture/decisions/0047-*.md` exists (lane `surfaces-docs-wave`), its "Measured cache
   cost (Valkey)" section holds the macOS and Arch Linux JSON (not "owed"), and its line
   "Operator's decision on the cache cost:" no longer says "owed" and records an acceptance.
   **Never write or edit that line yourself.** If it is missing or says anything other than an
   acceptance, stop: the operator has not decided.
3. `git log --oneline -1 -- .github/workflows/ci.yml` shows `surfaces-cluster-smoke` landed; the
   reviewer confirms that CI run was green (a lane cannot see CI).

## Required behaviour
1. `src/vibey/domain/config.py`: `DEFAULT_SURFACE_TRANSPORT = "queue"`.
2. `tests/conftest.py` `pytest_configure`: beside R34's
   `os.environ.setdefault("VIBEY_QUEUE_BACKEND", "postgres")`, add
   `os.environ.setdefault("VIBEY_SURFACES_TRANSPORT", "direct")` with a comment: the historical
   suite keeps in-process surfaces; the lanes' own suites and `-m integration` choose `queue`
   explicitly.
3. `deploy/helm/vibey/values.yaml`: `surfaceLanes.transport: queue`. Regenerate the goldens
   with `render.sh --update` and review: `default`, `ollama`, `ollama-gpu-qwenloop` and
   `surfaces-off` now render the eleven lane Deployments and the queue-mode worker; `keda-latest`
   and `keda-project` do not change.
4. Update exactly the assertions that pinned the old default, and nothing else:
   `tests/domain/test_surfaces_config.py::test_defaults_match_the_adr_table`,
   `tests/infrastructure/surface_lanes/test_selection.py::test_direct_is_the_default_and_quiet`
   (it now builds its settings with `transport="direct"` explicitly),
   `tests/test_bootstrap_surfaces.py::test_direct_by_default_builds_no_amqp_client` (likewise),
   and the chart goldens' tests that assert no lane in the default profile.
5. With `direct` chosen explicitly and any surface configured, `build_app` now logs the 8.f
   warning (`surface.transport.direct`, lane `surfaces-transport-selection`); add one test
   proving it through `build_app`.

## Where to change
- `src/vibey/domain/config.py` (one constant), `tests/conftest.py` (two lines and a comment),
  `deploy/helm/vibey/values.yaml` (one value), the regenerated goldens, the four tests named in 4,
  and `tests/test_bootstrap_surfaces.py` (append the warning test).

## Acceptance criteria
- [ ] `parse_config({"project": {"name": "x"}}).surfaces.transport == "queue"`.
- [ ] The default tier passes with the conftest pin: `uv run pytest -q -p no:cacheprovider -m "not integration and not paid"`; so does the full suite with PostgreSQL.
- [ ] `VIBEY_SURFACES_TRANSPORT=direct` restores today's behaviour with the warning; `queue` with no URL fails the start naming both remedies.
- [ ] The default golden holds eleven lane Deployments; `keda-*` goldens are byte-identical.
- [ ] Manual evidence in the commit body: against a local broker and Valkey, `VIBEY_SURFACES_TRANSPORT=queue VIBEY_TEST_AMQP_URL=… VIBEY_TEST_CACHE_URL=… uv run pytest -q -p no:cacheprovider -m integration tests/infrastructure/surface_lanes tests/contracts/test_surface_contracts.py` passes — or the body says it was not run.

## Tests to write first (TDD)
Append to `tests/test_bootstrap_surfaces.py`:
- `test_direct_after_the_flip_warns_that_8f_is_not_held`
- `test_queue_is_the_default_transport`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    deploy/helm/golden/render.sh
    git diff --exit-code deploy/helm/golden/keda-latest.yaml deploy/helm/golden/keda-project.yaml
    uv run pytest -q -p no:cacheprovider -m "not integration and not paid"
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    uv run coverage report --include='src/vibey/application/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- The docs lines naming the default and the CHANGELOG entry (`surfaces-docs-flip`). The
  operator's decision. CLAUDE.md, AGENTS.md, GEMINI.md, ADRs and the skill trees. Do not push,
  open PRs or change remotes. Commit locally as `feat(surfaces)!: …` with a `BREAKING CHANGE:`
  footer: surfaces default to their lanes; a process with surfaces configured and no lanes
  running fails its first surface call with `SurfaceLaneUnavailable`, naming
  `vibey surface serve <name>`; `VIBEY_SURFACES_TRANSPORT=direct` restores in-process surfaces
  with a warning that 8.f is not held.

## Lane card
- **Depends on:** `surfaces-docs-wave` (the ADR, its measurement and the operator's decision line), `surfaces-cluster-smoke`, `surfaces-contracts-lane`, `surfaces-cli-dead-letters`, `surfaces-callers-registry`, `surfaces-consumer-notifications`.
- **Shares a file with:** `tests/conftest.py` (`fakes-harness-decouple`, R34), `domain/config.py`, the chart and goldens.
- **Must keep passing unchanged:** every test not named in behaviour 4, all protected tests.
- **Standing constraints:** the flip is reversible with one key; never write the operator's decision; never hand-edit a golden; `helm` v4.2.4.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
