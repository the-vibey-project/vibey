## Title
feat(chart): one Deployment per loop service

## Why
ADR-0044 §13 and §15 run each loop engine as one long-lived service. In a cluster that
means one Deployment per engine running `vibey loop-service --engine <id>` (R27).

Sub-doctrine 8.b makes qwenloop and opencode on by default and the paid engines
declared-only. A service edits the worktree its caller tails, so it must mount the
worker's worktrees PVC (`worker.yaml:276-310`) at the same path.

That PVC is `ReadWriteOnce` today. So either every pod that mounts it co-locates on
one node, or the operator chooses `ReadWriteMany`, which becomes a value (12.c). The
qwenloop service takes the Ollama wiring the worker has today (`worker.yaml:93-114`).

## Required behaviour
1. **values.yaml:**
   - `worker.worktrees.accessMode: ReadWriteOnce`
   - `loopServices:`, a map keyed by engine id: `qwenloop`, `opencode`, `claudeloop`,
     `codexloop`, `cursorloop`, `agyloop`, `claudeloop-local`. Each entry has:
     - `enabled` (true only for `qwenloop` and `opencode`)
     - `prefetch: 1`
     - `replicas: 1`
     - `terminationGracePeriodSeconds: 7200`
     - `engineAuth` (true for the four paid engines, false otherwise)
     - `resources`, with the worker's shape
     - `extraEnv: []`
2. **`templates/loop-services.yaml`:** for each enabled entry, a Deployment
   `<fullName>-loop-<engine>`:
   - labels: `app.kubernetes.io/component: loop-<engine>` and
     `vibey.dev/worktrees: <Release.Name>`;
   - `args: ["loop-service", "--engine", <engine>, "--prefetch", <prefetch>]`;
   - env:
     - `VIBEY_BUS_AMQP_URL`, `VIBEY_BUS_VHOST` and `VIBEY_BUS_PREFIX`, the same as
       R29's worker env;
     - `VIBEY_LOOP_SERVICES_ROOT=/work`;
     - for `qwenloop` with `ollama.enabled`, the same `VIBEY_OLLAMA_URL`,
       `VIBEY_OLLAMA_MODEL`, `QWENLOOP_BASE_URL` and `QWENLOOP_MODEL` lines as
       `worker.yaml:93-114`;
     - with `engineAuth`, the `engineAuth.keys` list as `worker.yaml:84-90` renders it;
     - then `extraEnv`;
   - the worktrees volume mounted at `/work`, `workingDir: /work`;
   - `podSecurityContext` and `securityContext`, and the chart's
     `nodeSelector` / `tolerations`.
3. **Affinity.** When `worker.worktrees.accessMode` is `ReadWriteOnce`, the worker and
   every loop service carry `vibey.dev/worktrees: <Release.Name>` and a **required**
   `podAffinity` on that label with `topologyKey: kubernetes.io/hostname`. The first
   pod may schedule because it matches its own term. `ReadWriteMany` renders no
   affinity.
4. **The PVC.** `accessModes: [{{ .Values.worker.worktrees.accessMode }}]`.
5. **Environment.** The worker also gets `VIBEY_LOOP_SERVICES_ROOT=/work`. R01 reads
   it as `[loop_services] root`.
6. **Goldens.** Regenerate `default`, `ollama`, `ollama-gpu-qwenloop` and
   `surfaces-off`. The `keda-*` goldens do not change.

## Where to change
- The files on the card. Copy the worker Deployment's shape.

## Acceptance criteria
- [ ] The default render has exactly two loop-service Deployments, qwenloop and opencode.
- [ ] Paid ones appear only when their `enabled` is set.
- [ ] The affinity is present under RWO and absent under RWX.
- [ ] The qwenloop service carries the Ollama env when `ollama.enabled`.
- [ ] `render.sh` passes, and the `keda-*` goldens are unchanged.

## Tests to write first (TDD)
- `tests/infrastructure/test_chart_loop_services_golden.py`:
  - `test_default_render_runs_the_sovereign_pair`
  - `test_services_mount_worktrees_at_work`
  - `test_rwo_renders_required_co_location`
  - `test_qwenloop_service_gets_the_ollama_wiring` (reads the `ollama` golden)
  - `test_paid_services_are_declared_only`

## Checks the lane must run (all must pass)
    deploy/helm/golden/render.sh
    git diff --exit-code deploy/helm/golden/keda-latest.yaml deploy/helm/golden/keda-project.yaml
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_chart_loop_services_golden.py tests/infrastructure/test_chart_broker_golden.py tests/infrastructure/db/test_keda_scaler_query.py tests/infrastructure/test_config_loader.py

## Out of scope
- KEDA (R31).
- CI (R32).
- Flipping the defaults (R34).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

## Lane card
- **Depends on:** R27, R29.
- **Wave:** 8.
- **Files touched:**
  - `deploy/helm/vibey/templates/loop-services.yaml` (new)
  - `deploy/helm/vibey/templates/worker.yaml` (worktrees access mode, affinity label, root env)
  - `deploy/helm/vibey/values.yaml`
  - the goldens (regenerated)
  - `tests/infrastructure/test_chart_loop_services_golden.py` (new)
- **Parallel-safe with:** R28 and R33.
- **Must keep passing unchanged:**
  - the `keda-*` goldens
  - `tests/infrastructure/db/test_keda_scaler_query.py`
  - R29's tests
  - all protected tests
- **Standing constraints:** see the header list. helm v4.2.4; never hand-edit goldens.

## Standing constraints for every RabbitMQ lane
- **Protected tests are never edited:** `tests/domain/test_noloss*.py`,
  `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`,
  `tests/system/test_delivery_stage_set.py`, `tests/live/**` (`.vibey-gh.toml:78-85`,
  `.github/CODEOWNERS`). They must keep passing.
- **The first line of every new source file** is the provenance comment, copied
  byte-for-byte from line 1 of a sibling file (`vibey-gh check` compares it exactly).
- **No lane needs a running RabbitMQ.** Unit tests use
  `vibey_bootstrap.amqp.memory.InMemoryAmqpClient` (lane R04). Tests against a real
  broker are marked `integration` and skip unless `VIBEY_TEST_AMQP_URL` is set.
- **SQL runs on PostgreSQL 14:** no `MERGE`, no PostgreSQL 15+ syntax. The 14–18 matrix
  runs `tests/infrastructure/db`.
- **Defaults stay today's until R34:** `queue.backend = "postgres"` and
  `engines.invocation = "subprocess"`.

---
