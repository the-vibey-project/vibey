## Title
feat(deploy)!: run the kopf operator by default, scoped to the release namespace

## Why
ADR-0043 (`docs/architecture/decisions/0043-sovereign-surfaces-install.md:17,65-70`) says
the kopf operator reconciles every `VibeySurface` status and that this is on by default.
The chart disagrees: `deploy/helm/vibey/values.yaml:88-92` sets `operator.enabled: false`,
and `templates/operator.yaml:1` and `templates/crd-vibeyproject.yaml:1` are gated on that
flag. A default install therefore creates 18 `VibeySurface` CRs (from `templates/surfaces.yaml`)
that nothing ever writes a status to, so each one claims health with no evidence behind it
(sub-doctrine 10.f, ADR-0040). The code already works with the CRD. `src/vibey/infrastructure/operator/handlers.py:259-284`
has `on_surface_create` and a 60s `kopf.timer` on `vibeysurfaces`. Both read each
`spec.components[].deployment` through `read_namespaced_deployment_status`
(`handlers.py:218-241`) and patch `status.surface/components/conditions`, which is exactly
the shape in `deploy/helm/vibey/crds/crd-vibeysurface.yaml:58-87` (status subresource on).
The image already ships the operator: `deploy/docker/Dockerfile:110,154` run
`uv sync --extra operator`, the entrypoint is `tini -g -- vibey` (`:213`), and the chart
passes `args: [operator, ...]`, which runs `vibey operator` (`src/vibey/cli/main.py:1394-1413`).
The original reason for "off" was that the operator is a cluster-scoped controller
(`values.yaml:89-91`). This Part keeps it on by default and removes that reason: all
write rules move to a namespaced Role, and only kopf's read-only discovery stays
cluster-scoped. kopf 1.44 runs namespaced when given `--namespace`
(`kopf.run(namespace=..., clusterwide=False)`, `handlers.py:194`). Without the kopf.dev
peering CRDs it runs standalone, because `peering.mandatory` defaults to False.

## Required behaviour
1. `values.yaml`: `operator.enabled` defaults to `true`. A new key `operator.clusterWide`
   defaults to `false`. `operator.watchNamespace` stays `""`, but it now means "the
   release namespace" when `clusterWide` is false.
2. Default render (`clusterWide: false`) produces, in this order in `templates/operator.yaml`:
   - a ServiceAccount `<fullname>-operator`
   - a ClusterRole `<fullname>-operator` with only two rules: `list, watch` on
     `apiextensions.k8s.io/customresourcedefinitions` and on `""/namespaces`
   - a ClusterRoleBinding to that ClusterRole
   - a Role `<fullname>-operator` in namespace `watchNamespace || .Release.Namespace`,
     with these rules: `kopf.dev/kopfpeerings` (list, watch, patch, get), `""/events`
     (create), `vibey.dev/vibeyprojects, vibeyprojects/status, vibeysurfaces, vibeysurfaces/status`
     (list, watch, get, patch, update), and `apps/deployments, deployments/status` (get, list, watch)
   - a RoleBinding in the same namespace, bound to the ServiceAccount in `.Release.Namespace`
   - the Deployment, with container args exactly `["operator", "--namespace", "<that namespace>"]`
3. With `operator.clusterWide=true`, the ClusterRole also carries
   `kopf.dev/clusterkopfpeerings` (list, watch, patch, get) and every rule in the Role
   above except `kopfpeerings`. No Role or RoleBinding is rendered. The args are exactly
   `["operator"]`.
4. `operator.clusterWide=true` together with a non-empty `operator.watchNamespace` fails
   rendering with: `operator.clusterWide and operator.watchNamespace are mutually exclusive: a cluster-wide operator watches every namespace`.
5. No rule anywhere grants `delete`.
6. `operator.enabled=false` still renders no operator resources and no VibeyProject CRD.
7. The rule list the Role and ClusterRole share is defined once, in `_helpers.tpl`, as
   `define "vibey.operatorRules"`. It is not copied into two places.
8. Goldens: `default`, `ollama` and `surfaces-off` gain the operator ServiceAccount,
   VibeyProject CRD, ClusterRole, ClusterRoleBinding, Role, RoleBinding and Deployment
   (+335 lines each in the prototype, 0 removed, before the chart-version label change).
   `ollama-gpu-qwenloop`, `keda-latest` and `keda-project` use `--show-only` on templates
   this Part does not touch. Their only change is the `helm.sh/chart` label from item 9.
9. `deploy/helm/vibey/Chart.yaml` `version: 0.3.0` becomes `version: 0.4.0`. The comment
   on line 5 says the chart version tracks the chart's shape, and this Part changes a
   default and the meaning of a key. This changes the `helm.sh/chart: vibey-0.4.0` label
   in every golden. That churn is expected.
10. CI `cluster-smoke` (`.github/workflows/ci.yml:871`) gains two contract steps and two
    diagnostics lines (exact text below). The steps prove that the operator Deployment
    becomes Available with 0 restarts, that every VibeySurface reaches `Ready=True`, and
    that reconciliation is live: a surface whose Deployment is scaled to 0 turns
    `Ready=False`/`Degraded` and then recovers.

## Where to change
- `deploy/helm/vibey/values.yaml:88-94`. Replace the first lines of the `operator:` block
  (through `watchNamespace: ""`) with the text below. Leave `installCRD` and `resources`
  unchanged.
  ```yaml
  operator:
    # The kopf operator (ADR-0025, ADR-0043): reconciles VibeyProject custom
    # resources and keeps the Ready condition of every VibeySurface this chart
    # installs current. On by default: without it the surfaces' health is
    # never observed and every VibeySurface carries no status at all.
    enabled: true
    # false (the default): watch one namespace -- watchNamespace, or the
    # release namespace when that is empty -- through a namespaced Role
    # there. The only cluster-scoped grant left is kopf's read-only discovery
    # (list/watch CRDs and namespaces). true: watch every namespace, with
    # every rule in a ClusterRole; watchNamespace must then be empty.
    clusterWide: false
    # The namespace a namespaced operator watches. Empty means the release
    # namespace, which is where the chart puts every VibeySurface.
    watchNamespace: ""
  ```
- `deploy/helm/vibey/templates/_helpers.tpl`. Append after line 155:
  ```
  {{/*
  The operator's rules on the resources it serves, in one place so the
  namespaced Role and the cluster-wide ClusterRole can never disagree.
  kopf's own bookkeeping first (events so parks and surface changes show up
  in `kubectl describe`), then the two custom resources and the Deployments a
  VibeySurface names. Deliberately no `delete` anywhere: the operator
  reconciles, it does not remove, and a controller that cannot delete cannot
  delete the wrong thing.
  */}}
  {{- define "vibey.operatorRules" -}}
  - apiGroups: [""]
    resources: [events]
    verbs: [create]
  - apiGroups: [vibey.dev]
    resources: [vibeyprojects, vibeyprojects/status, vibeysurfaces, vibeysurfaces/status]
    verbs: [list, watch, get, patch, update]
  - apiGroups: [apps]
    resources: [deployments, deployments/status]
    verbs: [get, list, watch]
  {{- end -}}
  ```
- `deploy/helm/vibey/templates/operator.yaml`:
  - Lines 1-2 stay. Insert right after line 2:
    ```
    {{- if and .Values.operator.clusterWide .Values.operator.watchNamespace }}
    {{- fail "operator.clusterWide and operator.watchNamespace are mutually exclusive: a cluster-wide operator watches every namespace" }}
    {{- end }}
    {{- $watchNamespace := default .Release.Namespace .Values.operator.watchNamespace }}
    ```
  - Replace lines 8-51, from the `---` before `kind: ClusterRole` through the
    ClusterRoleBinding's last line `namespace: {{ .Release.Namespace }}`, with:
    ```
    ---
    apiVersion: rbac.authorization.k8s.io/v1
    kind: ClusterRole
    metadata:
      name: {{ $fullName }}-operator
      labels: {{- include "vibey.labels" . | nindent 4 }}
    rules:
      # kopf's discovery, read-only and needed in either mode: it watches CRDs
      # to learn when the resources it serves appear, and lists namespaces to
      # resolve the one it watches.
      - apiGroups: [apiextensions.k8s.io]
        resources: [customresourcedefinitions]
        verbs: [list, watch]
      - apiGroups: [""]
        resources: [namespaces]
        verbs: [list, watch]
      {{- if .Values.operator.clusterWide }}
      - apiGroups: [kopf.dev]
        resources: [clusterkopfpeerings]
        verbs: [list, watch, patch, get]
      {{- include "vibey.operatorRules" . | nindent 2 }}
      {{- end }}
    ---
    apiVersion: rbac.authorization.k8s.io/v1
    kind: ClusterRoleBinding
    metadata:
      name: {{ $fullName }}-operator
      labels: {{- include "vibey.labels" . | nindent 4 }}
    roleRef:
      apiGroup: rbac.authorization.k8s.io
      kind: ClusterRole
      name: {{ $fullName }}-operator
    subjects:
      - kind: ServiceAccount
        name: {{ $fullName }}-operator
        namespace: {{ .Release.Namespace }}
    {{- if not .Values.operator.clusterWide }}
    ---
    apiVersion: rbac.authorization.k8s.io/v1
    kind: Role
    metadata:
      name: {{ $fullName }}-operator
      namespace: {{ $watchNamespace }}
      labels: {{- include "vibey.labels" . | nindent 4 }}
    rules:
      - apiGroups: [kopf.dev]
        resources: [kopfpeerings]
        verbs: [list, watch, patch, get]
      {{- include "vibey.operatorRules" . | nindent 2 }}
    ---
    apiVersion: rbac.authorization.k8s.io/v1
    kind: RoleBinding
    metadata:
      name: {{ $fullName }}-operator
      namespace: {{ $watchNamespace }}
      labels: {{- include "vibey.labels" . | nindent 4 }}
    roleRef:
      apiGroup: rbac.authorization.k8s.io
      kind: Role
      name: {{ $fullName }}-operator
    subjects:
      - kind: ServiceAccount
        name: {{ $fullName }}-operator
        namespace: {{ .Release.Namespace }}
    {{- end }}
    ```
    The Deployment's own `---` (old line 52) and everything after it stay.
  - Old lines 99-102, in the container args. Change
    `{{- if .Values.operator.watchNamespace }}` to `{{- if not .Values.operator.clusterWide }}`,
    and `- {{ .Values.operator.watchNamespace | quote }}` to `- {{ $watchNamespace | quote }}`.
- `deploy/helm/vibey/Chart.yaml:6`: `version: 0.4.0`.
- `.github/workflows/ci.yml`. Insert immediately **before** the comment line
  `      # A fresh install into an empty namespace has no project. The worker` (line 936),
  keeping the 6-space step indentation:
  ```yaml
        # The operator is on by default (ADR-0043): a VibeySurface whose status
        # nobody writes is a health claim with no evidence behind it. Every
        # surface Deployment is Available by the step above, so every surface
        # must now report Ready -- and the operator must have got there without
        # a restart.
        - name: Contract - the operator marks every VibeySurface Ready
          run: |
            kubectl wait --for=condition=available \
              deployment/vibey-vibey-operator -n vibey --timeout=5m
            kubectl wait --for=condition=Ready vibeysurface --all -n vibey --timeout=5m
            kubectl get vibeysurfaces -n vibey
            restarts=$(kubectl get pods -n vibey -l app.kubernetes.io/component=operator \
              -o jsonpath='{.items[0].status.containerStatuses[0].restartCount}')
            echo "restarts=$restarts"
            test "$restarts" = "0"

        # Ready once is a snapshot, not reconciliation. Take one surface's only
        # Deployment away and the operator must notice on its next pass (60s),
        # then notice it come back -- level-triggered, both directions.
        - name: Contract - a scaled-down surface is reported Degraded, then recovers
          run: |
            kubectl scale deployment/vibey-vibey-registry -n vibey --replicas=0
            kubectl wait --for=condition=Ready=false vibeysurface/vibey-vibey-registry \
              -n vibey --timeout=3m
            kubectl get vibeysurface vibey-vibey-registry -n vibey \
              -o jsonpath='{.status.conditions[?(@.type=="Ready")].reason}' | grep -qx Degraded
            kubectl scale deployment/vibey-vibey-registry -n vibey --replicas=1
            kubectl wait --for=condition=available deployment/vibey-vibey-registry \
              -n vibey --timeout=5m
            kubectl wait --for=condition=Ready vibeysurface/vibey-vibey-registry \
              -n vibey --timeout=3m

  ```
  Append two lines to the end of the `Diagnostics on failure` step, after line 1033
  (`kubectl logs -n keda deployment/keda-operator --tail=50 || true`):
  ```yaml
            kubectl get vibeysurfaces -n vibey -o wide || true
            kubectl logs -n vibey deployment/vibey-vibey-operator --tail=200 || true
  ```
- Goldens: run `bash deploy/helm/golden/render.sh --update`. Never hand-edit a golden.
- New test file `tests/meta/test_chart_operator_default.py` (below). No `src/vibey` code
  changes, so ADR-0016 (class plus interface) does not apply. Tests follow the
  module-function pattern of `tests/meta/test_crd_engine_enum.py`, and line 1 copies
  that file's attribution header.

## Acceptance criteria
- [ ] `helm version --short` prints `v4.2.4`, the version CI's `chart` job pins
      (`ci.yml` job `chart`). With a different helm, STOP: goldens rendered by another
      helm fail CI.
- [ ] `bash deploy/helm/golden/render.sh` prints `ok` for all six profiles: default,
      ollama, ollama-gpu-qwenloop, keda-latest, keda-project, surfaces-off.
- [ ] `helm lint deploy/helm/vibey --strict --namespace vibey` passes, and so do these
      variants: `--set operator.clusterWide=true`, `--set operator.enabled=false`, and
      `--set operator.watchNamespace=team-a`.
- [ ] `helm template vibey deploy/helm/vibey -n vibey --set operator.clusterWide=true --set operator.watchNamespace=x`
      exits non-zero and prints `mutually exclusive`.
- [ ] `helm template vibey deploy/helm/vibey -n vibey --show-only templates/operator.yaml --set operator.clusterWide=true | grep -c "kind: Role$"`
      prints `0`.
- [ ] `helm template vibey deploy/helm/vibey -n vibey --show-only templates/operator.yaml --set operator.watchNamespace=team-a | grep -A1 -- "- --namespace"`
      shows `- "team-a"`.
- [ ] `helm template vibey deploy/helm/vibey -n vibey | grep -c delete` prints `0`.
- [ ] `uv run pytest -q -p no:cacheprovider tests/meta/test_chart_operator_default.py` passes (5 tests).
- [ ] `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` succeeds.
- [ ] If `actionlint` is installed, `actionlint .github/workflows/ci.yml` reports nothing
      new. The only finding allowed is the existing SC2046 on the
      `Build the image into minikube's daemon` step.
- [ ] One local commit: `feat(deploy)!: run the kopf operator by default, scoped to the release namespace`,
      with the footer `BREAKING CHANGE: operator.enabled defaults to true; an empty operator.watchNamespace now means the release namespace unless operator.clusterWide=true.`

## Tests to write first (TDD)
Create `tests/meta/test_chart_operator_default.py`. It must fail against the current
goldens (all 5 fail on `develop`), then pass after `render.sh --update`.
```python
"""The chart runs the kopf operator by default, scoped to the release namespace.

ADR-0043 makes every VibeySurface's health kopf-reconciled and on by default, so a
default install must carry the operator. The goldens are what `helm template`
renders (deploy/helm/golden/render.sh keeps them honest in CI), so they are read
here rather than rendered: this needs no helm.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[2]
GOLDEN = REPO / "deploy" / "helm" / "golden"
CI = REPO / ".github" / "workflows" / "ci.yml"
OPERATOR = "vibey-vibey-operator"


def _docs(profile: str) -> list[dict[str, Any]]:
    text = (GOLDEN / f"{profile}.yaml").read_text(encoding="utf-8")
    return [doc for doc in yaml.safe_load_all(text) if doc]


def _one(docs: list[dict[str, Any]], kind: str, name: str) -> dict[str, Any]:
    found = [d for d in docs if d["kind"] == kind and d["metadata"]["name"] == name]
    assert len(found) == 1, f"expected exactly one {kind}/{name}, found {len(found)}"
    return found[0]


def test_every_full_render_carries_the_operator_deployment() -> None:
    for profile in ("default", "ollama", "surfaces-off"):
        docs = _docs(profile)
        _one(docs, "Deployment", OPERATOR)
        _one(docs, "CustomResourceDefinition", "vibeyprojects.vibey.dev")


def test_the_default_operator_watches_only_the_release_namespace() -> None:
    deployment = _one(_docs("default"), "Deployment", OPERATOR)
    args = deployment["spec"]["template"]["spec"]["containers"][0]["args"]
    assert args == ["operator", "--namespace", "vibey"]


def test_the_cluster_role_is_read_only_discovery() -> None:
    role = _one(_docs("default"), "ClusterRole", OPERATOR)
    groups = sorted(group for rule in role["rules"] for group in rule["apiGroups"])
    assert groups == ["", "apiextensions.k8s.io"]
    verbs = {verb for rule in role["rules"] for verb in rule["verbs"]}
    assert verbs == {"list", "watch"}


def test_the_namespaced_role_grants_the_surfaces_and_deployments() -> None:
    role = _one(_docs("default"), "Role", OPERATOR)
    assert role["metadata"]["namespace"] == "vibey"
    resources = {res for rule in role["rules"] for res in rule["resources"]}
    assert {"vibeysurfaces", "vibeysurfaces/status", "deployments", "events"} <= resources
    assert all("delete" not in rule["verbs"] for rule in role["rules"])


def test_cluster_smoke_proves_the_operator_reconciles_surfaces() -> None:
    workflow = CI.read_text(encoding="utf-8")
    assert "Contract - the operator marks every VibeySurface Ready" in workflow
    assert "Contract - a scaled-down surface is reported Degraded, then recovers" in workflow
```

## Checks the lane must run (all must pass)
```
helm version --short                                   # must be v4.2.4
bash deploy/helm/golden/render.sh --update && bash deploy/helm/golden/render.sh
helm lint deploy/helm/vibey --strict --namespace vibey
helm lint deploy/helm/vibey --strict --namespace vibey --set operator.clusterWide=true
helm lint deploy/helm/vibey --strict --namespace vibey --set operator.enabled=false
uv run ruff check . && uv run ruff format --check .
uv run pytest -q -p no:cacheprovider tests/meta/test_chart_operator_default.py tests/meta/test_crd_engine_enum.py
uv run mypy --strict src/vibey && uv run lint-imports   # sanity only: src/vibey is untouched
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"
```
The root `tests/conftest.py:146-155` connects to Postgres at session start, even for
file-only tests. If no Postgres is reachable (`VIBEY_TEST_DATABASE_URL`), run the new
tests with `uv run pytest -q -p no:cacheprovider --noconftest -n 0 tests/meta/test_chart_operator_default.py`
instead. They need nothing from conftest. The per-layer 100% coverage gates are
unaffected because no `src/vibey` file changes. `cluster-smoke` itself runs only in CI
on minikube, and the reviewer verifies it there.

## Out of scope
- Do not change `src/vibey/infrastructure/operator/handlers.py`. **Follow-up finding, not
  this lane:** `reconcile_surface` (`handlers.py:256`) calls `surface_status(name, ...)`
  with the CR name, so `status.surface` and the `Surface` printer column show
  `vibey-vibey-forge` instead of `spec.surface` (`forge`). This is harmless to the
  Ready-condition contracts above.
- Moving the VibeyProject CRD from `templates/` into `crds/`. Now that it installs by
  default, a second release in the same cluster needs `operator.installCRD=false`.
  Record this for the docs wave. Do not change it here.
- The Forgejo swap (Part 2). Do not edit CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md,
  GEMINI.md or skill trees; the docs wave owns them (list at the end of this file). Do not
  push, open PRs, or change git remotes.

## Hard repository rules (always)
- domain/ stays pure (no I/O, async, clock, network); enforced by tests/domain/test_domain_purity.py.
- Dependencies point inward: domain -> application -> infrastructure -> cli (import-linter).
- CreditsExhausted never has resets_at. A capacity rejection outranks a completion claim.
- Code lives in classes with an interface beside each (ADR-0016); module functions need a written reason.
- Every job idempotent under replay; the ledger is append-only.

---

## Context shared by every part of this work
# chart-operator-forgejo: two independently committable parts

This spec covers two issues. **Read and implement only one Part per session.** Do Part 1
first, then Part 2. Each Part leaves `bash deploy/helm/golden/render.sh` green and makes
its own local commit. Line numbers are for `develop` at `d47c196d`. If they have moved,
find the quoted text instead.

Both Parts were prototyped against a scratch copy of the chart before this spec was
written. The YAML below is what passed `helm lint --strict` and all six golden profiles
with helm v4.2.4, and the tests passed against the regenerated goldens.

---
