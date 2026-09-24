## Title
feat(chart): the RabbitMQ broker is core infrastructure

## Why
ADR-0044 §15. RabbitMQ is only rendered inside the surfaces block
(`deploy/helm/vibey/templates/surfaces.yaml:99-215`, gated by `surfaces.enabled` at
`:1`). A queue and loop services that depend on it must work even with
`surfaces.enabled=false`.

Sub-doctrine 12.c forbids making anything less configurable. So:

- the broker's settings stay at `surfaces.rabbitmq.*` (`values.yaml:434-450`) and no
  key moves;
- a new `broker.enabled` switch gates the broker itself;
- resource names are unchanged, so Plane's default broker (`plane.yaml:3-8`),
  `VIBEY_BUS_URL` (`worker.yaml:236-248`) and cluster-smoke keep working.

The worker also needs the AMQP URL and the backend and invocation switches. The
defaults stay `postgres` and `subprocess` until R34.

## Required behaviour
1. **values.yaml** gains these blocks:
   ```yaml
   broker:
     enabled: true
     existingSecret: ""
     existingSecretUrlKey: amqp-url
     existingSecretKedaHostKey: keda-host
     vhost: "/"
     prefix: vibey
   queue:
     backend: postgres
     rabbitmq:
       deliveryLimit: 20
       consumerTimeoutSeconds: 21600
       waitTiersSeconds: [1, 5, 30, 120, 600, 3600]
       reconcileIntervalSeconds: 30
       redispatchAfterSeconds: 900
   engines:
     invocation: subprocess
   ```
   Each key has a comment saying what it does, like its neighbours.
2. **`templates/broker.yaml`** renders the Secret, PVC, Service and Deployment now at
   `surfaces.yaml:101-199`. It is gated by `broker.enabled`, not by `surfaces.*`. It
   reads `surfaces.rabbitmq.*` for image, credentials, storage and resources, and keeps
   the same names and labels.
   - The Secret gains `amqp-url`:
     `amqp://<user>:<pass>@<fullName>-rabbitmq.<ns>.svc.<clusterDomain>:5672/<urlquery vhost>`.
   - It also gains `keda-host`:
     `http://<user>:<pass>@<fullName>-rabbitmq.<ns>.svc.<clusterDomain>:15672/`.
     Both use the qualified DNS, which is ADR-0025's lesson.
   - A ConfigMap `<fullName>-rabbitmq-conf` holds `20-vibey.conf` with
     `consumer_timeout = <consumerTimeoutSeconds * 1000>`. It is mounted at
     `/etc/rabbitmq/conf.d/20-vibey.conf`. This is the fallback ADR-0044 names for a
     broker that refuses the per-queue argument.
3. **`surfaces.yaml`** keeps only the bus `VibeySurface` CR from section 2, gated as
   today by `surfaces.enabled` and `surfaces.rabbitmq.enabled`.
4. **`plane.yaml:5-6`**: the fail condition becomes `not .Values.broker.enabled`, with
   the message naming `broker.enabled`.
5. **The worker** (`worker.yaml`) gains:
   - `VIBEY_QUEUE_BACKEND={{ .Values.queue.backend }}`
   - `VIBEY_ENGINE_INVOCATION={{ .Values.engines.invocation }}`
   - `VIBEY_BUS_VHOST` and `VIBEY_BUS_PREFIX`
   - `VIBEY_BUS_AMQP_URL` from `secretKeyRef`: the broker Secret's `amqp-url` when
     `broker.enabled`, else `broker.existingSecret` / `existingSecretUrlKey`, with
     `optional: true` only when neither is set
   - when `queue.backend=rabbitmq` or `engines.invocation=service`, an init container
     `wait-for-rabbitmq` that uses the vibey image, running
     `python -c` with a TCP-connect retry loop to `<fullName>-rabbitmq:5672` or the
     external host. It follows the `wait-for-postgres` pattern at `worker.yaml:40-58`.
6. **Goldens.** Regenerate with `deploy/helm/golden/render.sh --update`, then review.
   `default`, `ollama`, `ollama-gpu-qwenloop` and `surfaces-off` change. `keda-latest`
   and `keda-project` **must not change**. `surfaces-off` now contains the broker.

## Where to change
- The files on the card. Copy `templates/postgres.yaml`'s core-infrastructure shape.

## Acceptance criteria
- [ ] `render.sh` passes after `--update`, and `git diff deploy/helm/golden/keda-*.yaml` is empty.
- [ ] The `surfaces-off` golden contains `kind: Deployment` named `vibey-vibey-rabbitmq`.
- [ ] The worker env holds `VIBEY_BUS_AMQP_URL` from the broker Secret.
- [ ] `helm lint --strict` passes with `--set broker.enabled=false --set broker.existingSecret=x --set surfaces.plane.enabled=false`.
- [ ] `test_keda_scaler_query.py` passes unchanged.

## Tests to write first (TDD)
- `tests/infrastructure/test_chart_broker_golden.py`, module-level functions reading
  the goldens with `yaml.safe_load_all`, as `test_keda_scaler_query.py:34-39` does:
  - `test_broker_renders_with_surfaces_off`
  - `test_broker_secret_carries_qualified_urls`
  - `test_worker_reads_the_amqp_url_from_the_broker_secret`
  - `test_consumer_timeout_conf_is_mounted`
  - `test_bus_surface_cr_still_follows_surfaces`

## Checks the lane must run (all must pass)
    deploy/helm/golden/render.sh
    git diff --exit-code deploy/helm/golden/keda-latest.yaml deploy/helm/golden/keda-project.yaml
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_chart_broker_golden.py tests/infrastructure/db/test_keda_scaler_query.py

## Out of scope
- Loop-service Deployments (R30).
- KEDA (R31).
- CI (R32).
- Flipping the defaults (R34).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

## Lane card
- **Depends on:** R01, for the environment variable names.
- **Wave:** 2.
- **Files touched:**
  - `deploy/helm/vibey/templates/broker.yaml` (new)
  - `deploy/helm/vibey/templates/surfaces.yaml` (remove the moved objects; keep the bus `VibeySurface`)
  - `deploy/helm/vibey/templates/plane.yaml` (one condition)
  - `deploy/helm/vibey/templates/worker.yaml`
  - `deploy/helm/vibey/values.yaml`
  - `deploy/helm/golden/{default,ollama,ollama-gpu-qwenloop,surfaces-off}.yaml` (regenerated)
  - `tests/infrastructure/test_chart_broker_golden.py` (new)
- **Parallel-safe with:** every non-chart lane. It starts the chart chain (R29 → R30 → R31 → R34).
- **Must keep passing unchanged:**
  - `tests/infrastructure/db/test_keda_scaler_query.py` (the `keda-*` goldens must not change)
  - the chart job's golden check for `keda-latest` and `keda-project`
  - cluster-smoke's deployment list (`ci.yml:904-935`); the name `vibey-vibey-rabbitmq` is unchanged
  - all protected tests
- **Standing constraints:** see the header list. `helm` must be v4.2.4, the version the `chart` job pins (`ci.yml:862-866`). If it is not on `PATH`, stop and report. Never hand-edit a golden.

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
