## Title
feat(chart): loop services route their engines' pytest to the cluster's test harness

## Why
Draft ADR-0045 §10 and §12. With the cluster's test-harness Deployment in place (harness-T27a),
the loop services' engines (rmq-r30) must carry the route, so a model's `uv run pytest` inside a
loop service is queued to the one cluster instance instead of starting a second run beside it
(8.e, ratified, `src/vibey_tools/gh/docs/doctrines.md:274-277`). A loop service's runners inherit
the service's environment (rmq-r20's launcher), so the variables go on the loop-service containers.
They appear only when `testHarness.enabled`, so every existing golden stays byte-identical until
harness-T28 turns it on.

## Required behaviour
1. **`deploy/helm/vibey/templates/loop-services.yaml`** (rmq-r30's): when `.Values.testHarness.enabled`,
   each loop-service container also gets
   `VIBEY_HARNESS_ROUTE={{ .Values.testHarness.routeEngines }}`,
   `VIBEY_HARNESS_WAIT_SECONDS={{ .Values.testHarness.engineWaitSeconds | quote }}`,
   `VIBEY_HARNESS_BACKEND=rabbitmq`, `VIBEY_HARNESS_INSTANCE={{ .Values.testHarness.instance }}` and
   `VIBEY_HARNESS_STATE_DIR=/work/.vibey-test-harness` (the same path as the Deployment's).
2. **`deploy/helm/golden/render.sh`** gains
   `profile test-harness-loop-services --show-only templates/loop-services.yaml -- --set testHarness.enabled=true`
   (plus `--set broker.enabled=true`, and whatever flags rmq-r30's own loop-services profile passes
   to render at least one loop service). Run `render.sh --update`; never hand-edit a golden.
3. **`tests/infrastructure/test_chart_test_harness_golden.py`** (harness-T27a's) gains
   `test_loop_services_route_their_engines_when_enabled`, reading the new golden: every
   loop-service container carries the five variables with the values above.

## Where to change
- `deploy/helm/vibey/templates/loop-services.yaml`, `deploy/helm/golden/render.sh`, the generated
  `deploy/helm/golden/test-harness-loop-services.yaml`, and the test file (append).

## Acceptance criteria
- [ ] `render.sh` passes; the only new golden is `test-harness-loop-services.yaml`; `default.yaml` and the `keda-*` goldens are unchanged.
- [ ] The new test passes.
- [ ] `helm lint --strict deploy/helm/vibey --set testHarness.enabled=true --set broker.enabled=true` passes.

## Tests to write first (TDD)
- `test_loop_services_route_their_engines_when_enabled` (appended to `tests/infrastructure/test_chart_test_harness_golden.py`).

## Checks the lane must run (all must pass)
    deploy/helm/golden/render.sh
    git diff --exit-code deploy/helm/golden/keda-latest.yaml deploy/helm/golden/keda-project.yaml deploy/helm/golden/default.yaml
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_chart_test_harness_golden.py tests/infrastructure/db/test_keda_scaler_query.py
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- Turning it on (harness-T28). The engine route inside vibey-launched subprocesses (harness-T26).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push, open a pull request or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** harness-T27a-chart-test-harness-deployment, harness-T26-engine-route-env.
- **Files touched:** see *Where to change*.
- **Shares a file with:** the chart and its goldens (after harness-T27a, before harness-T28).
- **Must keep passing unchanged:** every existing golden, `tests/infrastructure/db/test_keda_scaler_query.py`, rmq-r29's and rmq-r30's chart tests, harness-T27a's tests, and the protected tests.
- **Registry (amendment A4):** nothing.
- **Standing constraints (every harness lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Never hand-edit a golden. Use helm v4.2.4, as rmq-r30 does.
  - Default-tier tests read committed goldens and never run `helm` (ADR-0045 amendment A1; lane fakes-isolation-guard's audit hook fails a default-tier test that reaches out).
  - Edit existing files with `edit_file`, never rewrite a test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
