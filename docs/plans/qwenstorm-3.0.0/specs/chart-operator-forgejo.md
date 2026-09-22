# chart-operator-forgejo: two independently committable parts

This spec covers two issues. **Read and implement only one Part per session.** Do Part 1
first, then Part 2. Each Part leaves `bash deploy/helm/golden/render.sh` green and makes
its own local commit. Line numbers are for `develop` at `d47c196d`. If they have moved,
find the quoted text instead.

Both Parts were prototyped against a scratch copy of the chart before this spec was
written. The YAML below is what passed `helm lint --strict` and all six golden profiles
with helm v4.2.4, and the tests passed against the regenerated goldens.

---

# Part 1: the operator runs by default, scoped to the release namespace

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

# Part 2: the forge surface runs Forgejo, not Gitea

## Title
feat(deploy)!: the forge surface runs Forgejo; surfaces.gitea is now surfaces.forgejo

## Why
Ratified sub-doctrine 8.b (`src/vibey_tools/gh/docs/doctrines.md:122`) says: "**Forge**
defaults to **self-hosted Forgejo**". The chart installs Gitea instead. It sets
`image: gitea/gitea:latest@sha256:87a6…` at `deploy/helm/vibey/values.yaml:517-534`
(`surfaces.gitea`), and `templates/surfaces.yaml:818-937` renders a Gitea Secret, PVC,
Service and Deployment. The only `VibeySurface` for the forge, `<fullname>-forge`,
watches `<fullname>-gitea`. Forgejo reads the same configuration from environment
variables. Its code (`modules/setting/config_env.go`, codeberg.org/forgejo/forgejo,
checked 2026-09-22) matches `^(FORGEJO|GITEA)__`, and the official docker docs use the
`FORGEJO__` form. The rootful image keeps the Gitea layout: `GITEA_CUSTOM=/data/gitea`,
`VOLUME /data`, `EXPOSE 22 3000`, and `/etc/s6/gitea/setup` generates
`/data/gitea/conf/app.ini` and then applies the env through `environment-to-ini`. It also
ships `curl`, and `/usr/local/bin/forgejo`. So the swap only changes the image and config.

This Part also fixes a latent bug. The Service maps ssh `22 -> targetPort 2222`
(`surfaces.yaml:861-864`), but the rootful image's sshd listens on `SSH_LISTEN_PORT`,
which defaults to `SSH_PORT`, which defaults to `22`.

## Required behaviour
1. `values.yaml`: `surfaces.gitea` becomes `surfaces.forgejo`, and every knob is kept:
   `enabled`, `image.{repository,tag,digest}`, `adminUser`, `adminPassword`,
   `storage.{size,storageClass}`, `resources`. New values:
   `image.repository: codeberg.org/forgejo/forgejo`, `image.tag: "16.0.5"` (current stable
   16.x as of 2026-09-22; 15.x is the LTS line), `adminUser: forgejo_admin`,
   `adminPassword: forgejo_password`. Storage and resources are unchanged
   (10Gi; 100m/256Mi requests, 1Gi limit).
2. **The digest is pinned from the registry and never typed from memory or invented.** Run
   `docker buildx imagetools inspect codeberg.org/forgejo/forgejo:16.0.5`, or
   `crane digest codeberg.org/forgejo/forgejo:16.0.5`. Copy the top-level index digest
   (`Digest:` line), not a per-platform manifest. The listing must include `linux/amd64`
   and `linux/arm64`. If neither tool exists, this curl pair does the same:
   ```
   tok=$(curl -s "https://codeberg.org/v2/token?service=container_registry&scope=repository:forgejo/forgejo:pull" | python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])')
   curl -sI -H "Authorization: Bearer $tok" -H "Accept: application/vnd.oci.image.index.v1+json" https://codeberg.org/v2/forgejo/forgejo/manifests/16.0.5 | grep -i docker-content-digest
   ```
   For comparison only: at spec time (2026-09-22, registry HEAD) this returned
   `sha256:cf5f5ae6acf2ababca0ee3d255705b83a47f35b25e07fc931d694d60664053fe`, and the
   index listed linux/amd64, linux/arm64 and linux/arm/v6. Use the value **your** command
   prints. If you cannot reach the registry, STOP and report BLOCKED. Do not commit this
   spec's value unverified, an empty digest, or a guessed one.
3. **No deprecated alias.** If a user still passes `surfaces.gitea`, rendering fails loudly
   with: `surfaces.gitea was renamed to surfaces.forgejo: the forge surface runs Forgejo (sub-doctrine 8.b). Move these overrides under surfaces.forgejo.`
   An alias would map Gitea-specific overrides, such as `image.repository: gitea/gitea`,
   onto the Forgejo template without anyone noticing. Use `hasKey .Values.surfaces "gitea"`,
   not `.Values.surfaces.gitea`, because `helm lint --strict` renders with
   `missingkey=error`.
4. Rendered resource names: Secret `<fullname>-forgejo`, PVC `<fullname>-forgejo-data`,
   Service `<fullname>-forgejo`, Deployment `<fullname>-forgejo` (container `forgejo`),
   and label `app.kubernetes.io/component: forgejo` everywhere Gitea's was. The
   VibeySurface keeps its name `<fullname>-forge` and `spec.surface: forge`, and its
   component becomes `deployment: <fullname>-forgejo`.
5. Container env names use `FORGEJO__`: `FORGEJO__security__INSTALL_LOCK=true`,
   `FORGEJO__database__DB_TYPE=sqlite3`, `FORGEJO__server__HTTP_PORT=3000`.
   `USER_UID=1000` and `USER_GID=1000` are unchanged. The mount stays `/data`, and the pod
   keeps no securityContext, because the rootful image's setup needs root to chown before
   it drops to uid 1000, the same as Gitea today.
6. Ports: container `- name: http, containerPort: 3000` and `- name: ssh, containerPort: 22`.
   Service ssh is `port: 22, targetPort: 22`, and http stays `3000 -> 3000`. The probes
   stay `tcpSocket` on 3000 with the same delays, because ADR-0043's Security Impact
   specifies TCP probes.
7. Goldens: only `default` and `ollama` change in content (+25/-23 lines each in the
   prototype, all inside the forge resources, plus any `helm.sh/chart` label change from
   item 9). Afterwards neither file contains the string `gitea` in any case.
   `surfaces-off`, `ollama-gpu-qwenloop`, `keda-latest` and `keda-project` render no forge
   resources.
8. CI `cluster-smoke`: the Available list replaces `vibey-vibey-gitea` with
   `vibey-vibey-forgejo`. One new contract step proves the pod is Forgejo, not Gitea:
   `/api/forgejo/v1/version` exists only on Forgejo, and the API is served only once
   `INSTALL_LOCK` from `FORGEJO__` has taken effect. The step also checks that the
   `FORGEJO__` config reached `/data/gitea/conf/app.ini`.
9. `Chart.yaml`: if `version` is `0.3.0`, set it to `0.4.0`. If it is already `0.4.0` or
   higher because Part 1 landed, leave it.

## Where to change
- `deploy/helm/vibey/values.yaml:517-525`. Replace the header comment, the `gitea:` key
  and the `image`/`adminUser`/`adminPassword` lines with the text below. The `storage`
  and `resources` lines under it stay as they are.
  ```yaml
    # 13. Forge: Forgejo (sub-doctrine 8.b names Forgejo as the forge default).
    # The rootful image: HTTP on 3000, OpenSSH on 22, everything under /data.
    # Formerly surfaces.gitea; that key is now rejected at render time rather
    # than silently ignored.
    forgejo:
      enabled: true
      image:
        repository: codeberg.org/forgejo/forgejo
        tag: "16.0.5"
        # The multi-arch index (amd64, arm64, arm/v6), from
        # `docker buildx imagetools inspect codeberg.org/forgejo/forgejo:16.0.5`.
        # Bump tag and digest together.
        digest: "<the sha256:... your command printed>"
      adminUser: forgejo_admin
      adminPassword: forgejo_password
  ```
- `deploy/helm/vibey/templates/surfaces.yaml`:
  - Insert these as the very first lines of the file, above `{{- if .Values.surfaces.enabled }}`:
    ```
    {{- if hasKey .Values.surfaces "gitea" }}
    {{- fail "surfaces.gitea was renamed to surfaces.forgejo: the forge surface runs Forgejo (sub-doctrine 8.b). Move these overrides under surfaces.forgejo." }}
    {{- end }}
    ```
  - Edit only the forge block, which runs from the comment `8. Gitea (Forge)` to its
    `{{- end }}`, before `9. Registry`. This script makes exactly the edits the prototype
    made. Run it once from the repo root, then read the block back:
    ```python
    import re
    p = "deploy/helm/vibey/templates/surfaces.yaml"
    s = open(p, encoding="utf-8").read()
    a = s.index("{{- /* 8. Gitea (Forge)")
    b = s.index("{{- /* 9. Registry")
    blk = s[a:b]
    blk = blk.replace("8. Gitea (Forge)                                                           ",
                      "8. Forgejo (Forge)                                                         ")
    blk = blk.replace(".Values.surfaces.gitea", ".Values.surfaces.forgejo")
    blk = blk.replace("-gitea", "-forgejo")                      # names, incl. -gitea-data
    blk = blk.replace("component: gitea", "component: forgejo")
    blk = blk.replace("- name: gitea\n", "- name: forgejo\n")    # container name
    blk = blk.replace("GITEA__", "FORGEJO__")
    blk = blk.replace("      port: 22\n      targetPort: 2222", "      port: 22\n      targetPort: 22")
    blk = blk.replace("            - containerPort: 3000\n            - containerPort: 2222",
                      "            - name: http\n              containerPort: 3000\n"
                      "            - name: ssh\n              containerPort: 22")
    assert "gitea" not in blk.lower(), "a gitea reference survived in the forge block"
    open(p, "w", encoding="utf-8").write(s[:a] + blk + s[b:])
    ```
- `.github/workflows/ci.yml`:
  - Line 925: `vibey-vibey-gitea \` becomes `vibey-vibey-forgejo \`.
  - Insert immediately **after** the `Contract - all sovereign surface deployments become Available`
    step, after its `done` line (932) and one blank line. This puts it before Part 1's
    operator steps if those exist, or otherwise before the
    `# A fresh install into an empty namespace` comment:
    ```yaml
          # Sub-doctrine 8.b names Forgejo as the forge default. /api/forgejo/v1/version
          # exists only on Forgejo (Gitea answers 404), and the API is served only once
          # INSTALL_LOCK -- set through a FORGEJO__ variable -- has taken effect.
          - name: Contract - the forge surface is Forgejo, configured by FORGEJO__ variables
            run: |
              kubectl wait --for=condition=available deployment/vibey-vibey-forgejo \
                -n vibey --timeout=5m
              version=$(kubectl exec -n vibey deploy/vibey-vibey-forgejo -- \
                curl -fsS http://127.0.0.1:3000/api/forgejo/v1/version)
              echo "$version"
              echo "$version" | grep -q '"version"'
              kubectl exec -n vibey deploy/vibey-vibey-forgejo -- \
                grep -Eq '^INSTALL_LOCK *= *true' /data/gitea/conf/app.ini

    ```
    (`/data/gitea` is the image's own internal path, `GITEA_CUSTOM`. Leave it as is.)
- `deploy/helm/vibey/Chart.yaml:6`: follow Required behaviour item 9.
- Goldens: run `bash deploy/helm/golden/render.sh --update`. If Part 1 and Part 2 are on
  separate branches, whichever lands second rebases and reruns `--update`. Never
  hand-merge a golden.
- New test file `tests/meta/test_chart_forge_is_forgejo.py` (below). No `src/vibey`
  change. Copy the attribution header onto line 1, as in Part 1.

## Acceptance criteria
- [ ] `helm version --short` prints `v4.2.4`.
- [ ] Your digest lookup output is included in the commit message body: the tag, the
      index digest, and the platforms listed.
- [ ] `bash deploy/helm/golden/render.sh` prints `ok` for all six profiles.
- [ ] `helm lint deploy/helm/vibey --strict --namespace vibey` passes, and so do
      `--set surfaces.enabled=false` and `--set surfaces.forgejo.enabled=false`.
- [ ] `helm template vibey deploy/helm/vibey -n vibey --set surfaces.gitea.enabled=false`
      exits non-zero and prints `renamed to surfaces.forgejo`.
- [ ] `grep -ci gitea deploy/helm/golden/default.yaml deploy/helm/golden/ollama.yaml`
      prints `0` for both files.
- [ ] `grep -n -i gitea deploy/helm/vibey/values.yaml deploy/helm/vibey/templates/surfaces.yaml`
      shows only the rename comment in values.yaml and the `hasKey`/`fail` guard in surfaces.yaml.
- [ ] `uv run pytest -q -p no:cacheprovider tests/meta/test_chart_forge_is_forgejo.py` passes (6 tests).
- [ ] `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` succeeds.
      If `actionlint` is installed, it reports nothing new.
- [ ] One local commit:
      `feat(deploy)!: the forge surface runs Forgejo; surfaces.gitea is now surfaces.forgejo`,
      with the footer `BREAKING CHANGE: surfaces.gitea is renamed surfaces.forgejo (rendering fails if the old key is set); the forge PVC is now <release>-vibey-forgejo-data, so an upgrade does not reuse the old Gitea volume.`

## Tests to write first (TDD)
Create `tests/meta/test_chart_forge_is_forgejo.py`. All 6 tests fail on `develop` and pass
after the change plus `render.sh --update`.
```python
"""The forge surface is Forgejo, not Gitea (sub-doctrine 8.b).

Read from the committed goldens, which deploy/helm/golden/render.sh keeps equal to
what the chart renders, so this needs no helm.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[2]
GOLDEN = REPO / "deploy" / "helm" / "golden"
VALUES = REPO / "deploy" / "helm" / "vibey" / "values.yaml"
CI = REPO / ".github" / "workflows" / "ci.yml"
FORGEJO = "vibey-vibey-forgejo"
PINNED = re.compile(r"^codeberg\.org/forgejo/forgejo:[0-9][^@]*@sha256:[0-9a-f]{64}$")


def _docs(profile: str) -> list[dict[str, Any]]:
    text = (GOLDEN / f"{profile}.yaml").read_text(encoding="utf-8")
    return [doc for doc in yaml.safe_load_all(text) if doc]


def _one(docs: list[dict[str, Any]], kind: str, name: str) -> dict[str, Any]:
    found = [d for d in docs if d["kind"] == kind and d["metadata"]["name"] == name]
    assert len(found) == 1, f"expected exactly one {kind}/{name}, found {len(found)}"
    return found[0]


def test_values_name_the_forge_forgejo() -> None:
    surfaces = yaml.safe_load(VALUES.read_text(encoding="utf-8"))["surfaces"]
    assert "gitea" not in surfaces
    assert surfaces["forgejo"]["image"]["repository"] == "codeberg.org/forgejo/forgejo"


def test_the_forge_deployment_runs_a_pinned_forgejo_image() -> None:
    for profile in ("default", "ollama"):
        deployment = _one(_docs(profile), "Deployment", FORGEJO)
        container = deployment["spec"]["template"]["spec"]["containers"][0]
        assert PINNED.match(container["image"]), container["image"]
        config = [e["name"] for e in container["env"] if "__" in e["name"]]
        assert config and all(name.startswith("FORGEJO__") for name in config)


def test_the_forge_service_reaches_the_rootful_sshd() -> None:
    service = _one(_docs("default"), "Service", FORGEJO)
    ssh = [p for p in service["spec"]["ports"] if p["name"] == "ssh"]
    assert ssh == [{"name": "ssh", "port": 22, "targetPort": 22, "protocol": "TCP"}]


def test_the_forge_surface_watches_the_forgejo_deployment() -> None:
    surface = _one(_docs("default"), "VibeySurface", "vibey-vibey-forge")
    assert surface["spec"] == {"surface": "forge", "components": [{"deployment": FORGEJO}]}


def test_no_default_render_mentions_gitea() -> None:
    for profile in ("default", "ollama"):
        assert "gitea" not in (GOLDEN / f"{profile}.yaml").read_text(encoding="utf-8").lower()


def test_cluster_smoke_waits_for_forgejo_and_proves_it() -> None:
    workflow = CI.read_text(encoding="utf-8")
    assert "vibey-vibey-gitea" not in workflow
    assert "Contract - the forge surface is Forgejo, configured by FORGEJO__ variables" in workflow
```

## Checks the lane must run (all must pass)
```
helm version --short                                   # must be v4.2.4
bash deploy/helm/golden/render.sh --update && bash deploy/helm/golden/render.sh
helm lint deploy/helm/vibey --strict --namespace vibey
helm lint deploy/helm/vibey --strict --namespace vibey --set surfaces.forgejo.enabled=false
uv run ruff check . && uv run ruff format --check .
uv run pytest -q -p no:cacheprovider tests/meta/test_chart_forge_is_forgejo.py tests/meta/test_crd_engine_enum.py
uv run mypy --strict src/vibey && uv run lint-imports   # sanity only: src/vibey is untouched
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"
```
Without a reachable Postgres, use the `--noconftest -n 0` form described in Part 1's
checks. The per-layer 100% coverage gates are unaffected because no `src/vibey` file
changes. `cluster-smoke` runs only in CI, and the reviewer verifies it there.

## Out of scope
- **Admin user creation (a follow-up issue, not this lane).** Forgejo, like Gitea, has no
  environment variable that creates an admin. Today the chart writes
  `adminUser/adminPassword` into a Secret that nothing reads, and no admin exists. This
  Part keeps that parity: the Secret is renamed but still unused.
  Sketch for the follow-up: an initContainer using the same image that runs
  `/etc/s6/gitea/setup`, then `su-exec git forgejo migrate`, then
  `su-exec git forgejo admin user create --admin --username "$U" --password "$P" --email "$E" --must-change-password=false`,
  guarded by `forgejo admin user list --admin`. Forgejo refuses to run these as root. It
  needs a minikube run to prove it.
- Switching to the rootless image (`16.0.5-rootless`: uid 1000, ports 3000/2222, data in
  `/var/lib/gitea`, config through `GITEA_APP_INI`). That would satisfy ADR-0043's
  "drop: [ALL]" claim, but its config path needs proving in a cluster first.
- Wiring the worker to the forge. Nothing consumes the forge Service today, and this
  change does not add a consumer.
- The operator default (Part 1). Do not edit CHANGELOG.md, docs/, ADRs, CLAUDE.md,
  AGENTS.md, GEMINI.md or skill trees. Do not push, open PRs, or change git remotes.

## Hard repository rules (always)
- domain/ stays pure (no I/O, async, clock, network); enforced by tests/domain/test_domain_purity.py.
- Dependencies point inward: domain -> application -> infrastructure -> cli (import-linter).
- CreditsExhausted never has resets_at. A capacity rejection outranks a completion claim.
- Code lives in classes with an interface beside each (ADR-0016); module functions need a written reason.
- Every job idempotent under replay; the ledger is append-only.

---

# For the docs wave (not implemented by either Part)

Every doc that states the operator is off by default or cluster-wide, or that names Gitea
as the forge:

Operator default and scope:
- `docs/guides/kubernetes.md:56-63`: "The operator is implemented, but off by default ...
  unless you set `operator.enabled=true`".
- `docs/guides/kubernetes.md:299-323`: section "7. The kopf operator (optional)". It
  describes a cluster-scoped operator, says `--set operator.enabled=true`, describes a
  single ClusterRole holding all rules, and says "Set `operator.watchNamespace` to scope it
  to one namespace instead of the cluster". It needs the Role/ClusterRole split, the
  `clusterWide` key, and a note that a second release needs `operator.installCRD=false`.
- `docs/guides/kubernetes.md:456-457`: values-table rows `operator.enabled | false` and
  `operator.watchNamespace | "" | empty watches cluster-wide`. Add an
  `operator.clusterWide | false` row.
- `docs/project.mmd:218`: "kopf operator (off by default)".
- `docs/plans/architecture-and-roadmap.md:231`: "plus an optional Kubernetes operator".
  Review this.
- `docs/reference/cli.md:352-358`: `vibey operator --namespace` defaults to cluster-wide.
  The CLI default is unchanged, but note that the chart now passes `--namespace`.
- `CHANGELOG.md:73-74`: the released 2.1.0 entry says "The operator that reconciles their
  health is off by default (`operator.enabled`)". Leave released text alone and add an
  Unreleased entry with both BREAKING changes, the new `clusterWide` key, the new
  `watchNamespace` meaning, and chart 0.4.0.
- The skill trees, which must be updated together: `.claude/skills/vibey-quality-gates/SKILL.md:151`,
  `.agents/skills/vibey-quality-gates/SKILL.md:151`, `.cursor/rules/vibey-quality-gates.mdc:152`,
  `.agent/rules/vibey-quality-gates.md:147`. Each says the `cluster-smoke` job has "four
  cluster contracts". The job will have eight: all surfaces Available (already missing
  from that list), forge-is-Forgejo, operator-marks-Ready, Degraded-then-recovers, and
  the existing four.
- `docs/guides/self-hosted-surfaces.md:11,40-43` and ADR-0043 `:17,65-70` already describe
  the operator reconciling surfaces. After Part 1 these are true on a default install.
  They only need re-checking.

Gitea as the forge:
- `docs/architecture/decisions/0043-sovereign-surfaces-install.md:24`: "Forge: Gitea. Gitea
  provides verifiable, digest-pinned multi-arch OCI distribution images (`gitea/gitea`).
  Forgejo is supported as a 100% API-compatible, configuration-only image swap."
- `docs/architecture/decisions/0043-sovereign-surfaces-install.md:46`: "Forge: Gitea (`gitea/gitea`)".
- `docs/architecture/decisions/0043-sovereign-surfaces-install.md:74`: Security Impact says
  all images drop ALL capabilities. The rootful forge pod has no securityContext, and
  neither did the Gitea pod before it.
- `docs/guides/self-hosted-surfaces.md:26`: the diagram's "Gitea (forge)".
- `CHANGELOG.md`: a new Unreleased entry covering the rename, the fail-on-old-key guard,
  the new PVC name (see the upgrade warning below), and the ssh targetPort fix.
- Upgrade warning for the CHANGELOG and the kubernetes guide: the PVC is renamed to
  `<release>-vibey-forgejo-data`, so `helm upgrade` deletes `<release>-vibey-gitea-data`
  because it is no longer rendered. Back that PVC up first. Forgejo can migrate data only
  from Gitea 1.22 or earlier, so a newer Gitea volume could not be reused anyway.
