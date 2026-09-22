## Title
feat(chart): in queue mode each VibeySurface lists its lane as a component, so Ready means usable through vibey

## Why
Draft ADR-0047 §14 (`specs/ADR-surface-lanes.md`, "Health"): "Each surface's `VibeySurface`
resource (ADR-0043 §4) lists the lane's Deployment as a component in `queue` mode, so `Ready`
means the surface is usable through vibey, not only that its server is up." The operator
computes a surface's status from its components (`src/vibey/infrastructure/operator/handlers.py:207-256`).
The eleven laned surfaces' resources live in six templates: `plane.yaml:327-335` (tracker),
`docs.yaml:216-224` (docs), `kannel.yaml:152-160` (sms), `synapse.yaml:122-130` (messaging),
`wazuh.yaml:270-278` (siem) and `surfaces.yaml` (cache `:86-94`, secrets `:292-300`, files
`:413-421`, email `:537-545`, configuration `:635-643`, blob `:806-814`); the bus's resource
gets no lane (§11). ADR-0047 lane S30 (health).

## Required behaviour
1. In each of the eleven `VibeySurface` resources, after its existing `components` entries,
   add:
   ```yaml
       {{- if and (eq .Values.surfaceLanes.transport "queue") .Values.surfaceLanes.lanes.<name>.enabled }}
       - deployment: {{ $fullName }}-surface-<name>
       {{- end }}
   ```
   using the lane names of `surfaces-chart-lane-deployments` (`configuration` for the
   `configstore` resource, `siem` for the SIEM resource). Match each template's existing
   indentation and its `$fullName` variable.
2. **Goldens.** Regenerate with `--update`: the `surface-lanes` golden gains the eleven
   component lines; **no other golden changes** (the default transport is `direct`).

## Where to change
- `deploy/helm/vibey/templates/{plane,docs,kannel,synapse,wazuh,surfaces}.yaml` (the
  `components` lists only), `deploy/helm/golden/surface-lanes.yaml` (regenerated).
- Append to `tests/infrastructure/test_chart_surface_lanes_golden.py`.

## Acceptance criteria
- [ ] In `surface-lanes.yaml`, each of the eleven `VibeySurface` resources lists `vibey-vibey-surface-<name>` as its last component; the bus's does not.
- [ ] `git diff --stat deploy/helm/golden` shows only `surface-lanes.yaml`.
- [ ] Disabling one lane (`surfaceLanes.lanes.blob.enabled=false`) removes only that component (a test render, skipped without `helm`).
- [ ] `helm lint --strict` passes.

## Tests to write first (TDD)
Append to `tests/infrastructure/test_chart_surface_lanes_golden.py`:
- `test_each_laned_surface_lists_its_lane_as_a_component`
- `test_the_bus_surface_lists_no_lane`
- `test_a_disabled_lane_is_not_a_component`

## Checks the lane must run (all must pass)
    deploy/helm/golden/render.sh
    git diff --exit-code deploy/helm/golden/default.yaml deploy/helm/golden/ollama.yaml deploy/helm/golden/ollama-gpu-qwenloop.yaml deploy/helm/golden/surfaces-off.yaml deploy/helm/golden/keda-latest.yaml deploy/helm/golden/keda-project.yaml
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_chart_surface_lanes_golden.py tests/infrastructure/test_operator_surface_handlers.py

## Out of scope
- The operator's code (it already reads `components`). Cluster-smoke (`surfaces-cluster-smoke`).
  CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees
  (`surfaces-docs-wave`). Do not push, open PRs or change remotes. Commit locally with the Title
  as the subject.

## Lane card
- **Depends on:** `surfaces-chart-lane-deployments`.
- **Shares a file with:** six chart templates and the goldens (the chart chain). Never hand-edit a golden.
- **Must keep passing unchanged:** `tests/infrastructure/test_operator_surface_handlers.py`, `tests/infrastructure/db/test_keda_scaler_query.py`, all protected tests.
- **Standing constraints (every surfaces chart lane):**
  - `helm` must be v4.2.4, the version the `chart` job pins. If it is not on `PATH`, stop and report.
  - Read `/private/tmp/claude-501/storm/qwenstorm-3.0.0/EDITING-RULES.md` before changing a file; `surfaces.yaml` is long: `edit_file` only.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
