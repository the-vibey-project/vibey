## Title
feat(chart): one test-harness Deployment per cluster, off by default

## Why
Sub-doctrine 8.e (ratified, `src/vibey_tools/gh/docs/doctrines.md:271-277`) counts a cluster as one
deployment: one test run at a time, fed by a queue. Draft ADR-0045 §1 and §12 make its instance one
Deployment:
- **`replicas: 1`** is a literal, not a value: 8.e fixes the number, and a key that could only be set
  to what the law forbids is not configurability (12.c, `doctrines.md:455`);
- **`strategy: Recreate`**, so a rollout never runs two;
- it consumes `vibey.tests.cluster` (`instance: cluster`);
- it mounts the worktrees PVC at `/work`, like the loop services (rmq-r30), because a run executes in
  the requester's worktree.

It runs `vibey test-harness serve` (harness-T25) and needs a broker (rmq-r29). This lane adds the
Deployment behind `testHarness.enabled: false`, so every existing golden stays byte-identical;
harness-T27 wires the loop services, and harness-T28 turns it on.

## Required behaviour
1. **`deploy/helm/vibey/values.yaml`** gains
   ```yaml
   testHarness:
     enabled: false          # harness-T28 turns this on
     instance: cluster
     runBoundSeconds: 3600
     routeEngines: queue
     engineWaitSeconds: 110
     resources: {}
     testDatabase:           # the tests' own PostgreSQL; unset leaves VIBEY_TEST_DATABASE_URL unset
       existingSecret: ""
       key: ""
   ```
2. **New `deploy/helm/vibey/templates/test-harness.yaml`**, rendered only when
   `.Values.testHarness.enabled`: a `Deployment` named `<fullName>-test-harness` (use the chart's
   fullname helper from `_helpers.tpl`, as `worker.yaml` does) with:
   - `replicas: 1` (a literal) and `strategy: {type: Recreate}`;
   - the vibey image and pull policy, as the worker has;
   - `args: ["vibey", "test-harness", "serve"]`;
   - `terminationGracePeriodSeconds: {{ add .Values.testHarness.runBoundSeconds 60 }}`;
   - the worktrees PVC `<fullName>-worktrees` at `/work`, with rmq-r30's `vibey.dev/worktrees` label
     and, for `ReadWriteOnce`, its required pod affinity (copy both from `templates/loop-services.yaml`);
   - `resources: {{ toYaml .Values.testHarness.resources }}`;
   - environment: `VIBEY_HARNESS_BACKEND=rabbitmq`; `VIBEY_HARNESS_INSTANCE={{ .Values.testHarness.instance }}`;
     `VIBEY_HARNESS_STATE_DIR=/work/.vibey-test-harness`; `VIBEY_HARNESS_ROOT=/work`;
     `VIBEY_BUS_AMQP_URL` from a `secretKeyRef` exactly as rmq-r29 wires the worker: the broker
     Secret's `amqp-url` key when `broker.enabled`, else `broker.existingSecret` /
     `broker.existingSecretUrlKey`; and `VIBEY_TEST_DATABASE_URL` from
     `testHarness.testDatabase.existingSecret` / `.key` only when both are set.

   The render **fails** with `fail` when `testHarness.enabled` and neither `broker.enabled` nor
   `broker.existingSecret` is set: `"testHarness needs a broker: set broker.enabled=true or broker.existingSecret"`.
3. **`deploy/helm/golden/render.sh`** gains, beside the existing `profile` lines (`:77-94`),
   `profile test-harness --show-only templates/test-harness.yaml -- --set testHarness.enabled=true`
   (add `--set broker.enabled=true` too if the chart's defaults do not enable the broker).
   Run `deploy/helm/golden/render.sh --update` to generate `deploy/helm/golden/test-harness.yaml`;
   never hand-edit a golden. Use helm v4.2.4, as rmq-r30 does.
4. **New `tests/infrastructure/test_chart_test_harness_golden.py`**, module-level test functions
   (the reason `tests/infrastructure/db/test_keda_scaler_query.py:11-14` gives). The default-tier
   tests read the committed golden, as that file does, so no `helm` runs (the isolation guard of
   lane fakes-isolation-guard forbids `helm` in the default tier):
   - `test_one_recreated_replica_serving_the_cluster_queue`: `replicas: 1`, `Recreate`, the args,
     `VIBEY_HARNESS_BACKEND=rabbitmq`, `VIBEY_HARNESS_INSTANCE=cluster`;
   - `test_it_mounts_the_worktrees_like_the_loop_services`: the claim name, `/work`, the label;
   - `test_it_needs_a_broker` (`@pytest.mark.integration`, skipped when `shutil.which("helm")` is
     `None`): `helm template` with `testHarness.enabled=true,broker.enabled=false` fails with the message.

## Where to change
- `deploy/helm/vibey/values.yaml`, new `deploy/helm/vibey/templates/test-harness.yaml`,
  `deploy/helm/golden/render.sh`, the generated `deploy/helm/golden/test-harness.yaml`, and the new test.

## Acceptance criteria
- [ ] `deploy/helm/golden/render.sh` passes; the only new or changed golden is `test-harness.yaml`; `git diff --exit-code deploy/helm/golden/default.yaml deploy/helm/golden/keda-latest.yaml deploy/helm/golden/keda-project.yaml` is clean.
- [ ] The new default-tier tests pass; `test_it_needs_a_broker` passes with `-m integration` where helm is installed.
- [ ] `helm lint --strict deploy/helm/vibey --set testHarness.enabled=true --set broker.enabled=true` passes.

## Tests to write first (TDD)
- `tests/infrastructure/test_chart_test_harness_golden.py` (behaviour 4).

## Checks the lane must run (all must pass)
    deploy/helm/golden/render.sh
    git diff --exit-code deploy/helm/golden/keda-latest.yaml deploy/helm/golden/keda-project.yaml deploy/helm/golden/default.yaml
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_chart_test_harness_golden.py tests/infrastructure/db/test_keda_scaler_query.py
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- The loop services' environment (harness-T27). Turning it on (harness-T28).
- Cluster-smoke contracts ("the test-harness Deployment consumes `vibey.tests.cluster`"): a follow-up to rmq-r32's cluster job.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push, open a pull request or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** rmq-r29-chart-broker-core, rmq-r30-chart-loop-services, rmq-r31-chart-keda-rabbitmq, rmq-r34-defaults-flip (the chart's goldens land in that order), harness-T25-harness-backend-selection (`vibey test-harness serve`).
- **Files touched:** see *Where to change*.
- **Shares a file with:** the chart and its goldens (rmq-r29 → r30 → r31 → r34 → this lane → harness-T27 → T28).
- **Must keep passing unchanged:** every existing golden, the `keda-*` goldens included; `tests/infrastructure/db/test_keda_scaler_query.py`; rmq-r29's and rmq-r30's chart tests; and the protected tests.
- **Registry (amendment A4):** nothing.
- **Standing constraints (every harness lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new Python file is the provenance line, copied byte for byte from line 1 of a sibling file:
    `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`
  - Never hand-edit a golden: `render.sh --update` writes them.
  - Default-tier tests need nothing outside the process (ADR-0045 amendment A1; lane fakes-isolation-guard's audit hook fails a default-tier test that reaches out): `helm` only in an `integration` test.
  - Edit existing files with `edit_file`, never rewrite a test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
