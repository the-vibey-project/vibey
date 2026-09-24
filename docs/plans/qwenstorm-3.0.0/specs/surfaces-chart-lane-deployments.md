## Title
feat(chart): surfaceLanes.transport=queue renders one lane Deployment per surface, each holding only its own credentials, and the worker keeps only the bus

## Why
Draft ADR-0047 §14 (`specs/ADR-surface-lanes.md`, "The chart"):
- "**One Deployment per lane** (`templates/surface-lanes.yaml`, lane S30), named
  `<fullName>-surface-<name>`: rendered when `surfaceLanes.transport` is `queue` and
  `surfaceLanes.lanes.<name>.enabled`, which is true for all eleven; `replicas: 1`,
  `strategy: Recreate`, `args: ["surface", "serve", "<name>"]`; the `wait-for-postgres` and
  `wait-for-rabbitmq` init containers, copied from the worker; **no Service**: a lane listens on
  no port."
- "In `queue` mode each lane receives only its own surface's variables; the worker receives only
  the bus's; the worker keeps `VIBEY_BUS_AMQP_URL` (R29)."
- 8.f's "a single lane per deployment" is `replicas: 1` with `Recreate` (§1, third enforcer),
  and "the replica count is not a key" (§1).

§15: "The chart renders no lanes until `surfaceLanes.transport=queue` is set." One exception
this lane adds: the worker keeps `VIBEY_MESSAGING_ROOM_ID` in `queue` mode — a room address,
not a credential — because the worker's notifications name the room they post to
(`surfaces-consumer-notifications`). ADR-0047 lane S30 (deployments and worker).

## Required behaviour
1. **`values.yaml`** gains a top-level block after R29's `engines:` block, each key commented
   like its neighbours:
   ```yaml
   surfaceLanes:
     # direct: the worker reaches each surface itself. queue: one lane per surface, fed by
     # RabbitMQ, reaches it (sub-doctrine 8.f; ADR-0047). Stays direct until the default flips.
     transport: direct
     resources:
       requests: {cpu: 50m, memory: 128Mi}
       limits: {memory: 512Mi}
     lanes:
       tracker: {enabled: true}
       docs: {enabled: true}
       secrets: {enabled: true}
       files: {enabled: true}
       email: {enabled: true}
       sms: {enabled: true}
       messaging: {enabled: true}
       configuration: {enabled: true}
       cache: {enabled: true}
       blob: {enabled: true}
       siem: {enabled: true}
   ```
   (No `replicas` key: 8.f fixes it at one.)
2. **`templates/surface-lanes.yaml`** (new): when `eq .Values.surfaceLanes.transport "queue"`,
   for each name in the fixed list `tracker docs secrets files email sms messaging configuration cache blob siem`
   whose `lanes.<name>.enabled` is true, one Deployment `{{ $fullName }}-surface-<name>`:
   labels as the worker's with `app.kubernetes.io/component: surface-<name>`; `replicas: 1`;
   `strategy: {type: Recreate}`; the worker's image, pull policy, security contexts and service
   account; `args: ["surface", "serve", "<name>"]`; `resources` from `surfaceLanes.resources`;
   the worker's `wait-for-postgres` and R29's `wait-for-rabbitmq` init containers (copy them);
   env: `VIBEY_PG_URL` (as the worker), R29's `VIBEY_BUS_AMQP_URL`, `VIBEY_BUS_VHOST`,
   `VIBEY_BUS_PREFIX`, `VIBEY_SURFACES_TRANSPORT: queue`, then
   `{{- include "vibey.surfaceEnv" (dict "root" $ "only" "<name>") }}` (lane
   `surfaces-chart-env-helper`). No Service, no ports.
3. **`templates/worker.yaml`**: add `VIBEY_SURFACES_TRANSPORT` with
   `{{ .Values.surfaceLanes.transport | quote }}`. The surface include becomes
   `only: "bus"` when the transport is `queue` and `only: ""` otherwise; in `queue` mode, when
   `surfaces.enabled` and `surfaces.synapse.enabled`, the worker also keeps
   `VIBEY_MESSAGING_ROOM_ID` (the same value the helper renders).
4. **Goldens.** `deploy/helm/golden/render.sh` gains, after `surfaces-off`,
   `profile surface-lanes -- --set surfaceLanes.transport=queue` (the whole chart, so later
   lanes' changes to other templates show) with a comment saying it is the queue-mode install.
   Regenerate with `--update` and review: `default`, `ollama`, `ollama-gpu-qwenloop` and
   `surfaces-off` gain only the `VIBEY_SURFACES_TRANSPORT: "direct"` line in the worker;
   `surface-lanes.yaml` is new; `keda-latest` and `keda-project` do not change.

## Where to change
- `deploy/helm/vibey/values.yaml`, new `deploy/helm/vibey/templates/surface-lanes.yaml`,
  `deploy/helm/vibey/templates/worker.yaml`, `deploy/helm/golden/render.sh` (one profile), the
  regenerated goldens and the new `deploy/helm/golden/surface-lanes.yaml`.
- New `tests/infrastructure/test_chart_surface_lanes_golden.py`.

## Acceptance criteria
- [ ] In `surface-lanes.yaml`, exactly eleven Deployments named `vibey-vibey-surface-<name>`, each `replicas: 1`, `Recreate`, `args: [surface, serve, <name>]`, with both init containers and no Service.
- [ ] Each lane's env holds its own surface's variables and no other surface's (for example the tracker lane has `VIBEY_TRACKER_TOKEN` and no `VIBEY_SECRETS_TOKEN`), plus `VIBEY_PG_URL`, the three bus variables and `VIBEY_SURFACES_TRANSPORT=queue`.
- [ ] In `surface-lanes.yaml` the worker holds no surface credential (no `VIBEY_TRACKER_TOKEN`, `VIBEY_SECRETS_TOKEN`, `VIBEY_EMAIL_PASSWORD`, …), keeps the bus variables and `VIBEY_MESSAGING_ROOM_ID`, and has `VIBEY_SURFACES_TRANSPORT=queue`.
- [ ] `--set surfaceLanes.lanes.sms.enabled=false` drops only the SMS lane (a test render).
- [ ] The default goldens change by the one worker line only; `keda-*` are unchanged; `helm lint --strict` passes for both profiles.

## Tests to write first (TDD)
`tests/infrastructure/test_chart_surface_lanes_golden.py` (goldens read with `yaml.safe_load_all`; one `helm template` subprocess call for the disabled-lane case, skipped when `helm` is absent):
- `test_queue_mode_renders_eleven_single_replica_lanes`
- `test_each_lane_holds_only_its_own_credentials`
- `test_the_queue_mode_worker_holds_no_surface_credential`
- `test_a_disabled_lane_is_not_rendered`
- `test_direct_mode_renders_no_lane`

## Checks the lane must run (all must pass)
    deploy/helm/golden/render.sh
    git diff --exit-code deploy/helm/golden/keda-latest.yaml deploy/helm/golden/keda-project.yaml
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_chart_surface_lanes_golden.py tests/infrastructure/test_chart_surface_env_helper.py tests/infrastructure/test_chart_broker_golden.py tests/infrastructure/db/test_keda_scaler_query.py

## Out of scope
- `VibeySurface` health components (`surfaces-chart-surface-health`); cluster-smoke
  (`surfaces-cluster-smoke`); flipping the default (`surfaces-default-flip`); per-caller broker
  users (a follow-up in "Security impact"). `docs/guides/kubernetes.md` (`surfaces-docs-wave`).
  CHANGELOG.md, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees. Do not push, open PRs
  or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `surfaces-chart-env-helper`, `surfaces-cli-serve-ping` (the command the Deployments run).
- **Shares a file with:** `values.yaml`, `worker.yaml`, `render.sh`, the goldens (the chart chain). Never hand-edit a golden.
- **Must keep passing unchanged:** `tests/infrastructure/db/test_keda_scaler_query.py`, `tests/infrastructure/test_chart_broker_golden.py`, all protected tests.
- **Standing constraints (every surfaces chart lane):**
  - `helm` must be v4.2.4, the version the `chart` job pins. If it is not on `PATH`, stop and report.
  - Read `STORM/EDITING-RULES.md` before changing a file; `values.yaml` and `worker.yaml` are long: `edit_file` only.
  - Line 1 of every new Python file is the provenance comment, copied byte-for-byte from a sibling.
  - `surfaceLanes.transport` stays `direct` by default until `surfaces-default-flip`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
