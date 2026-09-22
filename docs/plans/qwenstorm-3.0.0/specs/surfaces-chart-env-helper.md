## Title
refactor(chart): the worker's surface environment moves into a vibey.surfaceEnv helper that renders all surfaces or one — byte-for-byte the same output

## Why
Draft ADR-0047 §14 (`specs/ADR-surface-lanes.md`, "The surface's credentials move to its
lane"): "A helper, `vibey.surfaceEnv` (lane S29), renders the surface environment block that
`worker.yaml:118-273` renders today, either for all surfaces or for one. S29 changes no golden
byte." In `queue` mode each lane Deployment will receive only its own surface's variables and
the worker only the bus's (`surfaces-chart-lane-deployments`), so a compromised worker "holds
broker rights, not a Plane token, an OpenBao token or an SMTP password" ("Security impact").
Splitting the move from the behaviour keeps this lane provable by one fact: every golden is
unchanged. ADR-0047 lane S29.

## Required behaviour
1. **`deploy/helm/vibey/templates/_helpers.tpl`** gains
   `{{- define "vibey.surfaceEnv" -}} … {{- end -}}`, called as
   `include "vibey.surfaceEnv" (dict "root" $ "only" "")`.
   - The body is the worker's current surface block — from
     `{{- if and .Values.surfaces .Values.surfaces.enabled }}` through its matching
     `{{- end }}` (`templates/worker.yaml:118-273` at integration `d3b4a388`) — **copied
     verbatim, not re-indented**, with only the context changed: `.Values` → `$root.Values`,
     `.Release` → `$root.Release`, `$fullName` defined inside as
     `include "vibey.fullname" $root`, and `(dict "root" . …)` → `(dict "root" $root …)`.
   - Each surface's sub-block is additionally wrapped in
     `{{- if or (eq $only "") (eq $only "<name>") }} … {{- end }}`, using these names:
     `tracker` (plane), `docs` (bookstack), `secrets` (openbao), `files` (nextcloud),
     `email` (postfix), `sms` (kannel), `messaging` (synapse), `configuration` (infisical),
     `cache` (redis), `bus` (rabbitmq), `blob` (garage), `siem` (wazuh). The names are
     `SurfaceName` values plus `bus` (`src/vibey/domain/surface_catalogue.py`).
   - An `only` that is none of these fails the render:
     `{{- fail (printf "vibey.surfaceEnv: unknown surface %q" $only) }}`.
2. **`templates/worker.yaml`**: the block is replaced by
   `{{- include "vibey.surfaceEnv" (dict "root" . "only" "") }}` at the same place.
3. **Goldens are byte-identical.** Run `deploy/helm/golden/render.sh` **without** `--update`;
   it must pass. If it does not, fix the whitespace control in the helper until it does; never
   regenerate a golden in this lane.

## Where to change
- `deploy/helm/vibey/templates/_helpers.tpl`, `deploy/helm/vibey/templates/worker.yaml`.
- New `tests/infrastructure/test_chart_surface_env_helper.py`.

## Acceptance criteria
- [ ] `deploy/helm/golden/render.sh` passes with no golden changed (`git diff --exit-code deploy/helm/golden`).
- [ ] `helm template` with `--show-only templates/worker.yaml` renders the same worker as before for `surfaces.enabled=false` and for the defaults.
- [ ] The helper's source guards each of the twelve names and carries the `fail` line for any other (a one-surface render is exercised by `surfaces-chart-lane-deployments`' golden).
- [ ] `helm lint --strict` passes.

## Tests to write first (TDD)
`tests/infrastructure/test_chart_surface_env_helper.py` (reads files; no cluster):
- `test_the_helper_guards_all_twelve_surface_names`
- `test_the_worker_includes_the_helper_for_all_surfaces`
- `test_an_unknown_surface_fails_the_render` (source assertion on the `fail` line)

## Checks the lane must run (all must pass)
    deploy/helm/golden/render.sh
    git diff --exit-code deploy/helm/golden
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_chart_surface_env_helper.py tests/infrastructure/test_chart_valkey_golden.py tests/infrastructure/db/test_keda_scaler_query.py

## Out of scope
- Using the helper for one surface (`surfaces-chart-lane-deployments`). R29's bus variables
  (`VIBEY_BUS_AMQP_URL`, `VIBEY_BUS_VHOST`, `VIBEY_BUS_PREFIX`) stay where R29 put them, outside
  the helper. CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees
  (`surfaces-docs-wave`). Do not push, open PRs or change remotes. Commit locally with the Title
  as the subject.

## Lane card
- **Depends on:** `rmq-r29-chart-broker-core`, `surfaces-chart-valkey` (chart order).
- **Shares a file with:** `templates/worker.yaml` (R29, R30, R34, T27 edit other parts), `_helpers.tpl`.
- **Must keep passing unchanged:** every golden, `tests/infrastructure/db/test_keda_scaler_query.py`, `tests/infrastructure/test_chart_broker_golden.py`, all protected tests.
- **Standing constraints (every surfaces chart lane):**
  - `helm` must be v4.2.4, the version the `chart` job pins. If it is not on `PATH`, stop and report.
  - Read `/private/tmp/claude-501/storm/qwenstorm-3.0.0/EDITING-RULES.md` before changing a file; `worker.yaml` is long: `edit_file` or a checked replacement only.
  - Never hand-edit a golden. Line 1 of every new Python file is the provenance comment.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
