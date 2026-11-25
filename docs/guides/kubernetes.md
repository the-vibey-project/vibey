---
description: Install vibey's worker on Kubernetes with the Helm chart, decide whether to bring the eighteen sovereign surfaces along, create a project, and autoscale on claimable work with KEDA.
---

# Run vibey on Kubernetes

> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** `helm install vibey deploy/helm/vibey` runs vibey's worker and
> a development PostgreSQL in a cluster, **plus all 18 sovereign surfaces by default** (Plane,
> BookStack, Gitea, Synapse and more: 26 Deployments). On a laptop, add
> `--set surfaces.enabled=false` for the worker alone. You build the image yourself; none is
> published. Engine-driven BUILD jobs need engine keys or an Ollama you enable.

## The lesson

Daniel had minikube open and a list of pods that would not stop growing.

**Daniel:** Professor, I asked for vibey's worker. Why is my laptop running Plane, Gitea, a
mail server and a SIEM?

**Professor Feynman:** Because you hired a removal van and ticked "the whole house". The chart
carries the worker and its database, and it also carries every service vibey prefers to run on
its own ground: a tracker, a wiki, a forge, chat, secrets, storage, monitoring. Eighteen of
them. The project's rule is that the self-hosted choice is the default, so the van comes full.

**Daniel:** And if I only want the bed?

**Professor Feynman:** Untick the house: `surfaces.enabled=false`. Then the install is the
worker, its worktree volume, PostgreSQL and the handful of objects that wire them together.

**Daniel:** Does the worker need the surfaces to run jobs?

**Professor Feynman:** To claim and run jobs it needs PostgreSQL, a project, and for BUILD an
engine it can use: a paid engine's API key, or a local model server you switch on. Here the van
picture stops working. A van just drops the furniture off. The chart also tells the worker where
each surface lives, through variables such as `VIBEY_TRACKER_URL`, so the two are wired
together when both are there. Leave the surfaces out and those variables are simply not set.

## Do it

CI's `cluster-smoke` job installs the full default (with the surfaces) on minikube with 4 CPUs
and 10 GiB of memory, and runs steps 4 and 5 as contracts. The worker-only install
(`surfaces.enabled=false`) is the install this guide was first verified with on minikube; today
CI checks it by a golden render, not by installing it.

1. Start a cluster and point Docker at it.

   ```bash
   minikube start -p vibey --cpus 4 --memory 10240
   eval $(minikube -p vibey docker-env)
   ```

2. Build the image into the cluster's Docker daemon, from the top of a vibey checkout.

   ```bash
   docker build -f deploy/docker/Dockerfile -t vibey:dev .
   ```

3. Install the chart. For the worker alone:

   ```bash
   helm install vibey deploy/helm/vibey -n vibey --create-namespace --set surfaces.enabled=false
   ```

   Leave out `--set surfaces.enabled=false` to install all 18 surfaces as well.

4. Watch the worker wait for a project.

   ```bash
   kubectl logs -n vibey deploy/vibey-vibey-worker -f
   ```

   You should see:

   ```text
   no project yet; polling every 15s
   ```

5. Create a project from inside the cluster. `VIBEY_SABBATH_ENABLED=false` is only needed from
   Friday sundown to Saturday sundown, when `vibey new` otherwise exits 75 (see
   [The Sabbath in a cluster](#the-sabbath-in-a-cluster)).

   ```bash
   kubectl exec -n vibey deploy/vibey-vibey-worker -- \
     env VIBEY_SABBATH_ENABLED=false vibey new demo --repo /work/demo --max-cycles 1
   ```

   `vibey new` prints the project's id.

6. See the project and its id at any time.

   ```bash
   kubectl exec -n vibey deploy/vibey-vibey-worker -- vibey projects
   ```

   You should see one line per project, newest first: its id, phase, cycle and open gates.

7. Bind the worker to that project (the value is the id, not the name).

   ```bash
   helm upgrade vibey deploy/helm/vibey -n vibey --reuse-values \
     --set worker.project=PROJECT_ID
   ```

   Replace `PROJECT_ID` with the id from step 5 or 6. The worker log then shows a line like
   `worker started: project=demo engines=all parallelism=2 provider=scripted`.

## Daniel's teach-back

**Daniel:** I build the image myself and install the chart. By default the chart brings the
worker, a development PostgreSQL and all eighteen sovereign surfaces; `surfaces.enabled=false`
leaves just the worker and its database. The worker waits for a project instead of
crash-looping; I create one with `vibey new` in the pod, find its id with `vibey projects`, and
pin the worker to it with `worker.project`. BUILD needs an engine: an API key in a Secret, or
the in-cluster Ollama.

**Professor Feynman:** Correct. One addition: the default `worker.provider` is `scripted`, a
stand-in for tests, so set it to `gptossloop` with Ollama on, or to `claudeloop` with its key,
before you expect a real design.

## The details

The decisions behind the image, chart, operator and autoscaler are
[ADR-0025](../architecture/decisions/0025-kubernetes-operator-crd-keda.md) and
[ADR-0026](../architecture/decisions/0026-tini-pid1-and-the-sigterm-latch.md); the surfaces are
[ADR-0042](../architecture/decisions/0042-sovereign-self-hosted-defaults-and-declared-paid-relays.md)
and [ADR-0043](../architecture/decisions/0043-sovereign-surfaces-install.md).

### What works today, and what does not

- **The worker runs, applies migrations, claims jobs, and autoscales.** CI installs the chart on
  minikube on every relevant push (`cluster-smoke`) and asserts each behaviour.
- **Every engine ships in the image; none is configured by default.** Since
  [ADR-0037](../architecture/decisions/0037-one-distribution-one-version.md) the one
  `vibey-engine` distribution carries all three runner packages, so the image puts
  `claudeloop`, `codexloop`, `gptossloop` and `qwenloop` on `PATH` beside `vibey` (CI's `image`
  job asserts every console script resolves). The chart still defaults to
  `worker.provider: scripted` with no `worker.engines` and no keys, and that is the install CI
  deploys. Its worker logs `no recorded conformance for ...`, naming the engines that have none:
  correct, because an engine without a key can never pass conformance and is never selected.
  Engine-driven (BUILD) jobs therefore do not run on a default install.
- **A binary on `PATH` is not yet a working engine.** codexloop drives an external `codex`
  binary, which the image does not carry. claudeloop runs through the Claude CLI bundled inside
  `claude-agent-sdk`, but `claudeloop doctor` looks for `claude` on `PATH` only, so it reports
  the CLI missing in the image. That per-runner verification is runbook
  [16](../runbooks/expansion/16-loop-runner-containers.md)'s Phase 0 and runbook
  [05](../runbooks/expansion/05-server-mode-kubernetes.md) item 1.
- **Engine authentication in a pod is by API key only.** Subscription login is an interactive
  TTY flow and does not exist in a cluster. Set `engineAuth.existingSecret` to a Secret you
  create and list `engineAuth.keys` as `{name, key}` pairs (environment variable name, key
  inside the Secret), for example `{name: ANTHROPIC_API_KEY, key: anthropic}`. They are
  injected into the worker Deployment only. claudeloop reads `ANTHROPIC_API_KEY` or
  `ANTHROPIC_AUTH_TOKEN`; codexloop reads `OPENAI_API_KEY`, `AZURE_OPENAI_API_KEY` or
  `CODEX_API_KEY`. Declare the engines you mean to use in `worker.engines`:
  `vibey doctor --cluster --engines <the same list>` then reports `engine-auth` as `FAIL` for any
  of them without a key (see [Preflight from inside a pod](#preflight-from-inside-a-pod)).
- **No hub in the chart.** There is no `vibey serve` Deployment, so the krypton apps cannot
  reach an in-cluster install. Create projects and answer gates with `vibey new` and
  `vibey answer` in a pod, or with the operator (below).
- **The operator is implemented, but off by default.** See
  [The kopf operator](#7-the-kopf-operator-optional).
- **Verified where.** The steps were first verified on minikube (Kubernetes v1.35.1) before the
  surfaces became the default; since then CI's `cluster-smoke` job is the standing check. The
  chart is written so the same install works against a managed PostgreSQL on AKS, EKS or GKE
  (`postgres.enabled=false` and `dsn.existingSecret`), but only the minikube path has been run
  end to end, and there are no per-cloud presets.

### The sovereign surfaces

`surfaces.enabled: true` is the master switch (`deploy/helm/vibey/values.yaml`), and each
surface also has its own `enabled: true`. A default install deploys all of them:

| # | Role | Surface (values key) | # | Role | Surface (values key) |
|---|---|---|---|---|---|
| 1 | Tracker | Plane (`plane`) | 10 | Bus | RabbitMQ (`rabbitmq`) |
| 2 | Docs | BookStack and MariaDB (`bookstack`) | 11 | Blob (S3) | Garage (`garage`) |
| 3 | Secrets | OpenBao (`openbao`) | 12 | SIEM | Wazuh, amd64 only (`wazuh`) |
| 4 | Files | Nextcloud (`nextcloud`) | 13 | Forge | Gitea (`gitea`) |
| 5 | Email | Postfix (`postfix`) | 14 | Registry | Distribution (`registry`) |
| 6 | SMS | Kannel, amd64 only (`kannel`) | 15 | Identity | Keycloak (`keycloak`) |
| 7 | Messaging | Synapse (`synapse`) | 16 | Logs | Loki (`loki`) |
| 8 | Config store | Infisical (`infisical`) | 17 | Status | Uptime Kuma (`uptimeKuma`) |
| 9 | Cache | Redis (`redis`) | 18 | Monitoring | Prometheus and Grafana (`monitoring`) |

What that costs, from the chart's own values and its golden render:

- **Objects.** The default render (`deploy/helm/golden/default.yaml`) has 26 Deployments, 18
  PersistentVolumeClaims and 18 `VibeySurface` objects (a CRD in `deploy/helm/vibey/crds/`).
  With `surfaces.enabled=false` (`golden/surfaces-off.yaml`) it is one Deployment, one
  StatefulSet, one PVC, one Secret, one Service, one ServiceAccount and two ConfigMaps.
- **Requests.** The surfaces' declared requests add up to about 1.7 CPU and 4 GiB of memory, and
  their volume claims to about 82 GiB. CI gives minikube 4 CPUs and 10 GiB and waits up to 20
  minutes for the install, then for each of 25 surface Deployments to become Available.
- **Credentials.** Several surfaces ship development passwords and keys in plain values (for
  example `surfaces.plane.secretKey`, `surfaces.gitea.adminPassword`,
  `surfaces.bookstack.appKey`). Override every one for anything real.
- **Images.** Each surface image is pinned by digest; Kannel and Wazuh are amd64 only, so on an
  Apple-silicon minikube turn those two off.

To turn them off:

```bash
# all of them
helm install vibey deploy/helm/vibey -n vibey --create-namespace --set surfaces.enabled=false
# or one at a time, for example the two amd64-only ones
helm install vibey deploy/helm/vibey -n vibey --create-namespace \
  --set surfaces.kannel.enabled=false --set surfaces.wazuh.enabled=false
```

### 1. Build the image into the cluster's daemon

The chart defaults to `image.pullPolicy: Never` and tag `vibey:dev`, because a locally built
image has never been pushed anywhere and `Always` would send kubelet hunting a registry that has
never seen it.

No prebuilt image is published, not to ghcr.io and not to Docker Hub. CI's `image` job builds
amd64 and arm64 on every push and pull request and contract-tests the amd64 build, but never
pushes either. The only ghcr.io artifact the project publishes is the Python distribution
(`ghcr.io/the-vibey-project/vibey/python`), a wheel and an sdist pushed with `oras`, not a
runnable image. For any cluster other than minikube, build and push to a registry you control,
then point the chart at it (`REGISTRY` and `TAG` are yours):

```bash
docker buildx build -f deploy/docker/Dockerfile \
  --platform linux/amd64,linux/arm64 \
  -t REGISTRY/vibey:TAG --push .
helm install vibey deploy/helm/vibey -n vibey --create-namespace \
  --set image.repository=REGISTRY/vibey --set image.tag=TAG \
  --set image.pullPolicy=IfNotPresent
```

The image is two-stage on purpose: the runtime layer carries no compiler, no `uv`, and no `pip`
(the base image's pip is deleted), so a compromised engine session inside a worker finds nothing
it can install with. `apt-get` remains, because the runtime stage uses it to install git and
`tini`, but it needs root and the pod runs as uid 10001 with `allowPrivilegeEscalation: false`.
The entrypoint is `tini -g -- vibey` (see step 6). Migrations ship inside the image. CI asserts
each of these against the amd64 build: the entrypoint runs, `id -u` is 10001, none of
`uv pip pip3 gcc cc` is on `PATH`, and `/app/migrations/*.sql` is non-empty.

### 2. What the chart installs for the worker

With or without surfaces, the chart creates a ServiceAccount, a worker Deployment, a worktree
PVC (mounted at `/work`, the worker's working directory), a `vibey-vibey-dsn` Secret, and a
single-replica PostgreSQL 17 StatefulSet behind a headless Service, with ConfigMaps for its
init script and `pg_hba.conf`. An init container waits for PostgreSQL, so the failure mode is
"pod pending" rather than "CrashLoopBackOff with a stack trace", and a `migrate` init container
applies migrations before the worker starts.

The built-in PostgreSQL is **development only**: `postgres.password` defaults to `vibey` in
plain values. For anything real, set `postgres.enabled: false` and point `dsn.existingSecret`
at a Secret with two keys
([ADR-0055](../architecture/decisions/0055-the-ledger-is-append-only-by-the-database.md)):

- `dsn` (or the key named by `dsn.existingSecretKey`) is the application role's DSN. The chart
  injects it as `VIBEY_PG_URL` into the worker and, when enabled, the operator.
- The owner's DSN, under the key `dsn.existingSecretMigrateKey` names. It is mounted only into
  the `migrate` init container, which runs `vibey migrate`: it applies migrations, creates the
  application role if it is missing, grants it exactly the declared privileges, and fails the
  pod if that role could still rewrite the ledger.

`dsn.existingSecretMigrateKey` is empty by default, which makes a single-DSN install, so an
existing Secret keeps working after an upgrade until you name an owner key. The worker then
migrates as the one role, and `vibey doctor --cluster` fails `ledger-guard` until the roles are
split ([database roles](../reference/configuration.md#database-roles)). Use a fully qualified
host or an IP address: KEDA reads the application's DSN from another namespace.

The built-in PostgreSQL does this for you: `postgres.user` is the owner and `postgres.appRole`
(default `vibey_app`) the application role. Each surface database
(`postgres.additionalDatabases`, default `plane` and `infisical`) is owned by a login role of the
same name whose password is `postgres.additionalDatabasePasswords.<name>`; the postgres
container creates it and hands it its database on every start, so an existing install is
converted on upgrade and no surface pod holds the owner's credentials.

Every connection to the built-in PostgreSQL authenticates with scram-sha-256, local and remote
alike (sub-doctrine 10.j,
[ADR-0061](../architecture/decisions/0061-every-postgresql-connection-authenticates-with-scram-sha-256.md)).
The chart ships the server's `pg_hba.conf` as the `<release>-postgres-hba` ConfigMap and points
`hba_file` at it on every start, so an install created before this rule follows it after an
upgrade. It also sets `password_encryption=scram-sha-256`. The method is not a value you can
change. A managed instance must meet the same rule: require scram-sha-256 for every role vibey
and the surfaces connect as, with no `trust`, `md5` or clear-text `password` rule that could
match them. See `SECURITY.md` §7 for the lines; `vibey doctor --cluster`'s `local-auth` does not
pass until they are set.

The `wait-for-postgres` init container is rendered only for the built-in PostgreSQL. Against a
managed instance the worker connects directly at startup, so an unreachable DSN shows up as
`CrashLoopBackOff` rather than a pending pod. Check `vibey doctor --cluster` (`database` and
`dsn-host`) first.

### 3. Projects in a cluster

A worker with nothing to do would normally exit, which in a Deployment is a restart loop that
ends only when a person creates a project, and the crash counter makes a healthy worker look
broken. The chart therefore sets `--wait-for-project 15`, so the worker parks and polls
(`no project yet; polling every 15s`).

**Set `worker.project` explicitly.** Left empty, the worker binds to whichever project was
created most recently: convenient on a laptop, a trap in a cluster the moment a second project
exists. The value is the project id, not its name. `vibey new` prints it, and `vibey projects`
lists every project's id, phase, cycle and open gates
([`vibey projects`](../reference/cli.md#vibey-projects)). The chart does not enforce this: with
the value empty it omits `--project` and installs anyway.

### 4. Watch it work

```bash
kubectl logs -n vibey deploy/vibey-vibey-worker -f
```

```text
sigterm handler registered
worker started: project=demo engines=all parallelism=2 provider=scripted
processed one job
```

`kubectl logs` interleaves stdout and stderr. A current worker also writes per-iteration
diagnostics to stderr (`drive[N] iter=M calling run_once`,
`drive[N] iter=M run_once returned worked=…`, and
`drive[N] iter=M reap done, waiting for notify`), so the real log is noisier than the sample
above. Those lines are expected.

### Preflight from inside a pod

A worker can start, log `worker started`, report Ready, and still do no work: its worktree
volume is not writable, an engine has no credentials, or its DSN is one the autoscaler cannot
resolve. `vibey doctor --cluster` checks that wiring from inside the pod:

```bash
kubectl exec -n vibey deploy/vibey-vibey-worker -- vibey doctor --cluster
```

`doctor` runs as a separate process, so it cannot see the worker's own command line. Pass it the
worker's `--engines` and `--provider` (the chart's `worker.engines` and `worker.provider`) so the
`engine-auth` check judges the engines the worker will actually use:

```bash
kubectl exec -n vibey deploy/vibey-vibey-worker -- \
  vibey doctor --cluster --engines claudeloop,codexloop --provider claudeloop
```

Every runner is on `PATH` in the image, so a binary being present says nothing about intent,
and the check does not treat it as intent. It prints one `PASS` or `FAIL` line per check and
exits non-zero if any check fails:

| Check | Passes when |
|---|---|
| `dsn-host` | the DSN host is fully qualified, an IP address, or `localhost`, so KEDA's operator in another namespace can resolve it |
| `non-root` | the process uid is not 0 |
| `workspace-writable` | the working directory (`/work` in the chart) accepts a write |
| `engine-auth` | every engine named by `--engines`, plus claudeloop under `--provider claudeloop`, is on `PATH` and has one of its API-key variables set (gptossloop and qwenloop take none). With neither flag nothing is required: it passes and reports which engines in the worker's default pool have a key, so a default install says plainly that no engine-driven job can run |
| `database` | the DSN connects |
| `migrations` | every file in `/app/migrations` is recorded in `schema_migration`; runs only when `database` connected |

Run it whenever a worker reports Ready but does no work.

### The local model in the cluster

`ollama.enabled=true` runs an Ollama server in the release, pulls `ollama.model` onto a 30 GiB
volume with a Job, and points the worker at it (`VIBEY_OLLAMA_URL` and `VIBEY_OLLAMA_MODEL` for
vibey's sovereign DESIGN and DECOMPOSE providers, `GPTOSSLOOP_BASE_URL` and `GPTOSSLOOP_MODEL`
for the gptossloop engine). It is off by default, because a 20B model wants a node with 16 GiB
requested and a 24 GiB limit, and ideally a GPU (`ollama.gpu.enabled`).

**The chart's model is stock `gpt-oss:20b`**, not the Heretic v2 build the rest of vibey
defaults to since
[ADR-0099](../architecture/decisions/0099-heretic-v2-of-gpt-oss-20b-is-the-sovereign-default-model.md).
The chart passes its value to the worker as `VIBEY_OLLAMA_MODEL`, which wins over vibey's own
default, so an in-cluster worker runs stock. To match a laptop install, set:

```bash
helm upgrade vibey deploy/helm/vibey -n vibey --reuse-values --set ollama.enabled=true \
  --set ollama.model=hf.co/mradermacher/gpt-oss-20b-heretic-v2-GGUF:MXFP4_MOE \
  --set worker.provider=gptossloop
```

That combination is not covered by a golden render or CI. `ollama.qwenloopFeature: true` also
switches qwenloop on, hands it `QWENLOOP_BASE_URL` and `QWENLOOP_MODEL` (`ollama.qwenModel`,
default `qwen3:14b`) and pulls that model too; it is off by default. The worker accepts
`--provider gptossloop` (`worker.provider`; `qwenloop` is still read as gptossloop,
ADR-0064). That provider talks to Ollama over HTTP rather than running the `gptossloop` binary,
so it needs a model server the pod can reach.

### 5. Autoscaling with KEDA

KEDA is a cluster-wide operator and is not assumed, so the ScaledObject is off by default and
inert without it.

```bash
helm repo add kedacore https://kedacore.github.io/charts
helm install keda kedacore/keda -n keda --create-namespace --wait
helm upgrade vibey deploy/helm/vibey -n vibey --reuse-values --set keda.enabled=true
```

The trigger is the **claimable-work** query: ready, due now, not of an abandoned project, and
not blocked behind an unsatisfied dependency, deliberately mirroring `JobRepository.claim`'s
SELECT arm (`tests/infrastructure/db/test_keda_scaler_query.py` pins each exclusion to the
claim's own). Scaling on raw queue depth would start workers for jobs nothing can claim yet.

Measured on minikube with `maxReplicas: 4`:

| Event | Observed |
|---|---|
| 20 claimable jobs enqueued | 0 → 4 replicas in about 8 s |
| queue drained | 4 → 0 after the 300 s `cooldownPeriod` |
| pod receives SIGTERM | exits in 4-5 s |

The N→0 transition happens in **one step**. KEDA's deactivation path sets the replica count
directly and bypasses the HPA `scaleDown` behaviour policy entirely. That policy only smooths
HPA-driven scaling between `minReplicas` and max, so do not read it as protection against losing
several in-flight sessions at once.

### 6. Scale-in and long sessions

Engine sessions run for minutes to hours, so `terminationGracePeriodSeconds` defaults to
**7200**. That is a ceiling for one long in-flight turn, not an expected shutdown time.

On SIGTERM the worker drains: it finishes the job in hand and claims no more, then exits
(`draining on SIGTERM: finishing in-flight job, claiming no more`). An idle worker therefore
exits in seconds. Two details make this hold in the window before the worker is fully up
([ADR-0026](../architecture/decisions/0026-tini-pid1-and-the-sigterm-latch.md)):

- **`tini` is PID 1.** The image's entrypoint is `/usr/bin/tini -g -- vibey`. Linux discards a
  signal sent to PID 1 while its disposition is still the default, and a Python interpreter
  needs hundreds of milliseconds to start and install a handler. On minikube, a pod deleted a
  fraction of a second after its container started was observed sitting out the entire 7200 s
  grace period, still claiming jobs. `tini` is ready in microseconds and forwards the signal;
  `-g` sends it to the whole process group, so an engine subprocess the worker started is
  signalled too.
- **A SIGTERM latch catches the startup window.** `vibey` arms a small handler before its other
  imports whose only job is to remember that SIGTERM arrived. Once the event loop is running and
  the real drain handler is installed, the worker checks the latch; if it fired, the worker logs
  `SIGTERM arrived during startup; draining immediately` and claims nothing.

CI's drain contract deletes a worker pod and requires it to terminate in under 60 s. It records
the container's start time, because a delete that lands during boot tests the startup race and a
delete after boot tests the steady-state drain; both must pass.

### 7. The kopf operator (optional)

`vibey operator` (`pip install 'vibey-engine[operator]'`) runs kopf handlers that create projects
and apply `spec.answers` through the same application services `vibey new` and `vibey answer`
use, then reconcile `VibeyProject` status every 15 s. The chart installs it only with
`operator.enabled=true`:

```bash
helm upgrade vibey deploy/helm/vibey -n vibey --reuse-values --set operator.enabled=true
```

This installs, in addition to the worker:

- the `VibeyProject` CRD (`vibeyprojects.vibey.dev`, short name `vp`), annotated
  `helm.sh/resource-policy: keep` so `helm uninstall` never deletes a project mid-BUILD along
  with it. Set `operator.installCRD=false` if another release already owns the CRD.
- a `ClusterRole` scoped to `vibeyprojects`/`vibeyprojects/status` (`list, watch, get, patch,
  update`, deliberately no `delete`) plus `create` on `events`, `list, watch` on
  `customresourcedefinitions` and `namespaces` (kopf's discovery), and `list, watch, patch, get`
  on `kopfpeerings`/`clusterkopfpeerings` for kopf peering.
- a single-replica operator Deployment (`strategy.type: Recreate`; two operators patching the
  same CR is a race with no upside at this scale). Set `operator.watchNamespace` to scope it to
  one namespace instead of the cluster.

Create a project by applying a CR instead of `vibey new`:

```yaml
apiVersion: vibey.dev/v1alpha1
kind: VibeyProject
metadata:
  name: demo
spec:
  repo: /work/demo
  maxCycles: 10
  maxCycleDollars: 25
  engines: [claudeloop]
  answers:
    6f1c2a4e-0000-4000-8000-000000000000: { choice: "yes" }
```

```bash
kubectl apply -n vibey -f vibeyproject.yaml
kubectl get vibeyprojects -n vibey
```

Keys under `spec.answers` are gate UUIDs (read them from `status.openGates[].gateId`), and each
value is the same object `vibey answer` sends: `{choice: …}` for deployment and triage gates,
`{verdict: …}` for review gates, and `{<question_id>: <answer>, …}` for interview gates.

The CR also accepts `maxCycleTurns` and `skillsContext: {mode, budget, timeout_seconds}` (`mode`
is `off`, `shadow`, or `inject`; `budget` is 1,000-32,000, default 6,000). `gates`
(`{timeout_seconds, kill_grace_seconds, isolate_python_env, env_allow}`) and `engineEnvironment`
(`{allow, engines: {<engine id>: [...]}}`) declare what a gate command and an engine session may
see of the worker's environment, the same objects as `vibey.toml`'s
[`[gates]`](../reference/configuration.md#gates) and
[`[engine_environment]`](../reference/configuration.md#engine_environment); a forbidden entry
(`VIBEY_*`, `PG*`, a DSN) is refused before the project is created. `spec.engines` is restricted
by the CRD schema to the known engine ids (`claudeloop`, `codexloop`, `gptossloop`, `qwenloop`,
`claudeloop-local`).

The operator creates the project on first reconcile, then re-reconciles every 15 s. It applies
any new `spec.answers` through the same gate-answer service `vibey answer` calls. A key naming an
already-answered gate, a key that is not a UUID, or a value that is not an object is recorded in
`status.ignoredAnswers` as `{key, reason}`, not treated as an error. Each reconcile writes:

- `status.projectId`, the guard that stops a re-applied CR from creating a second project;
- `status.phase`, `status.cycle`, and `status.maxCycles`;
- `status.openGates`, `{gateId, kind, prompt}` per open gate;
- three conditions: `Ready` (`True`/`Progressing`, or `False` with `AwaitingHuman`, `Complete`,
  or `Abandoned`; `Unknown`/`ProjectMissing` if the project row is gone), `Parked` (`True` with
  the gate kind CamelCased as the reason, for example `BudgetExhausted`), and `Complete`.

`kubectl get vp` shows Phase, Cycle, Ready, Parked, Reason (the Parked reason), and Age as
columns; `kubectl describe` shows the full status. The operator never deletes a project, so
removing the CR does not remove the underlying project or its data.

### The Sabbath in a cluster

Sub-doctrine 8.i is on by default
([ADR-0072](../architecture/decisions/0072-the-sabbath-kept-where-the-machine-stands.md)): from
sundown Friday to sundown Saturday, `vibey new` exits 75 and the worker keeps running but claims
nothing until the window closes. Where a pod stands is resolved as on any host (an override, the
operating system's location service, then the time zone's reference city); when none gives a
sundown, `[sabbath] fallback_opens` and `fallback_closes` apply. To declare it off for a
worker, add `{name: VIBEY_SABBATH_ENABLED, value: "false"}` to `worker.extraEnv`; for one
command, prefix it with `env VIBEY_SABBATH_ENABLED=false` as in step 5. See
[`[sabbath]`](../reference/configuration.md#sabbath).

### The tested configurations

CI's `chart` job lints and renders the chart under each profile in
`deploy/helm/golden/render.sh` and compares the result with a committed golden file:
`default`, `ollama`, `ollama-gpu-gptossloop`, `keda-latest`, `keda-project`, `surfaces-off` and
`existing-secret`. `cluster-smoke` installs only the defaults (plus `keda.enabled` for the
autoscaling contracts). Anything else is untested.

### Values worth knowing

| Value | Default | Why |
|---|---|---|
| `image.repository` / `image.tag` | `vibey` / `dev` | local build; override for any registry |
| `image.pullPolicy` | `Never` | change to `IfNotPresent` once the image is in a registry |
| `worker.terminationGracePeriodSeconds` | `7200` | ceiling for one long in-flight turn |
| `worker.waitForProjectSeconds` | `15` | park instead of restart-looping |
| `worker.parallelism` | `2` | concurrent job loops per pod |
| `worker.project` | `""` | **set this**; empty binds to the newest project |
| `worker.provider` | `scripted` | DESIGN/decompose provider; `claudeloop` needs its API key, `gptossloop` a reachable Ollama (`qwenloop` is read as gptossloop) |
| `worker.engines` | `""` | comma-separated engine allow-list (`--engines`); empty means all; pass the same list to `doctor --cluster --engines` |
| `worker.replicas` | `1` | ignored once KEDA owns the Deployment |
| `worker.resources` | requests 250m CPU, 512Mi; limit 2Gi | the worker container |
| `worker.worktrees.size` / `storageClass` | `5Gi` / `""` | the `/work` PVC where BUILD worktrees live |
| `worker.queueReap.*` | `enabled: true`, every 60 s | the queue reaper (ADR-0056); rendered into `VIBEY_QUEUE_REAP_*` |
| `worker.extraEnv` | `[]` | extra EnvVar objects, appended after the chart's own |
| `engineAuth.existingSecret` | `""` | Secret holding engine API keys |
| `engineAuth.keys` | `[]` | `{name, key}` pairs mapped to env vars on the worker |
| `keda.enabled` | `false` | install the ScaledObject |
| `keda.minReplicas` / `maxReplicas` | `0` / `4` | scale to zero when idle |
| `keda.pollingInterval` | `15` | seconds between scaler queries |
| `keda.cooldownPeriod` | `300` | delay before deactivating to zero |
| `clusterDomain` | `cluster.local` | only change on a custom `--service-dns-domain` |
| `postgres.enabled` | `true` | dev only; use `dsn.existingSecret` for managed |
| `postgres.image` | `postgres:17-alpine` | the built-in server |
| `postgres.storage` | `8Gi` | dev PostgreSQL PVC |
| `postgres.appRole.name` | `vibey_app` | the application role the worker connects as |
| `postgres.additionalDatabases` | `[plane, infisical]` | surface databases, each owned by its own role |
| `dsn.existingSecret` | `""` | Secret holding a managed instance's DSN |
| `dsn.existingSecretKey` | `dsn` | key inside `dsn.existingSecret` |
| `dsn.existingSecretMigrateKey` | `""` | the owner DSN's key; empty means a single-DSN install |
| `operator.enabled` | `false` | install the kopf `VibeyProject` operator |
| `operator.watchNamespace` | `""` | empty watches cluster-wide |
| `operator.installCRD` | `true` | disable if another release already owns the CRD |
| `ollama.enabled` | `false` | run an in-cluster Ollama and point the worker at it |
| `ollama.model` | `gpt-oss:20b` | the model pulled and handed to the worker (stock, not the ADR-0099 default) |
| `ollama.qwenModel` / `qwenloopFeature` | `qwen3:14b` / `false` | pull and switch on qwenloop too |
| `ollama.contextLength` | `32768` | `OLLAMA_CONTEXT_LENGTH` |
| `ollama.storage.size` | `30Gi` | the weights volume |
| `ollama.gpu.enabled` | `false` | add a GPU limit (`nvidia.com/gpu: 1` by default) |
| `ollama.pull.enabled` | `true` | the Job that pulls the model |
| `surfaces.enabled` | `true` | master switch for all 18 sovereign surfaces |
| `surfaces.<name>.enabled` | `true` | each surface's own switch |
| `edge.enabled` | `false` | render Ingress and cert-manager Certificates for the UI surfaces |
| `backup.enabled` | `false` | Velero backup to the in-cluster Garage, at `backup.schedule` (`0 2 * * *`) |

## When it goes wrong { #troubleshooting }

**The install times out, or pods stay Pending.** The default install brings all 18 surfaces.
Give minikube at least 4 CPUs and 10 GiB, or install with `--set surfaces.enabled=false`.

**Kannel or Wazuh pods fail with an exec format error on an Apple-silicon Mac.** Both are amd64
only. Set `surfaces.kannel.enabled=false` and `surfaces.wazuh.enabled=false`.

**`vibey new` in the pod exits 75 and says `resting for the Sabbath`.** That is sub-doctrine
8.i, not a fault. Run it again after the window, or declare it off for that command with
`env VIBEY_SABBATH_ENABLED=false`.

**`helm upgrade` fails with `lookup <release>-postgres ... no such host`.** You are on a chart
older than the DSN fix. KEDA's operator runs in its own namespace and dials PostgreSQL itself,
so the DSN must be fully qualified; a bare Service name resolves only from inside the release
namespace, which is why the worker was fine and the autoscaler was not. Set `clusterDomain` if
your cluster does not use `cluster.local`.

**The Deployment shows `0/0` but pods are still `Terminating` and working.** Either the worker
is ignoring SIGTERM (an image built before the drain landed) or the signal was discarded before
the worker could catch it (an image whose PID 1 is Python rather than `tini`). Both look the
same: `kubectl` reports capacity released while the pods still hold CPU, memory and PostgreSQL
connections and keep claiming jobs. Rebuild from the current `deploy/docker/Dockerfile`. On a
current image the pod's log shows `sigterm handler registered` at boot and, on delete, either
`draining on SIGTERM: finishing in-flight job, claiming no more` or
`SIGTERM arrived during startup; draining immediately`. If neither appears after a delete, the
image is old.

**`kubectl delete pod --force --grace-period=0` leaves workers running.** Force delete removes
the pod object without waiting for the container to die. The container keeps running, keeps its
database connections, and **keeps claiming jobs**, invisible to `kubectl`. Check with:

```bash
kubectl exec -n vibey vibey-vibey-postgres-0 -- \
  psql -U vibey -d vibey -c \
  "SELECT client_addr, count(*) FROM pg_stat_activity
   WHERE datname='vibey' AND client_addr IS NOT NULL GROUP BY client_addr;"
```

Connections from addresses with no corresponding pod are orphans; kill them at the container
runtime (`docker kill` inside `minikube docker-env`). Prefer a normal delete: the drain makes it
fast.

**Workers scale up but claim nothing.** The scaler counts claimable jobs across *all* projects,
while the worker Deployment binds to one. Work in another project will scale workers that cannot
claim it.

**A worker is Ready but does no work.** Run `vibey doctor --cluster` inside the pod, with the
worker's `--engines` and `--provider` (see
[Preflight from inside a pod](#preflight-from-inside-a-pod)). With the default
`worker.provider: scripted` and no keys, no engine-driven job can run.

**The in-cluster worker runs a different model from your laptop.** The chart's `ollama.model` is
stock `gpt-oss:20b`; set it to the Heretic tag (see
[The local model in the cluster](#the-local-model-in-the-cluster)).

## Where next

- [Local models on Ollama](local-models-ollama.md): what the in-cluster model server needs,
  measured on one machine.
- [Self-hosted surfaces](self-hosted-surfaces.md): what each sovereign surface is for.
- [Configuration reference](../reference/configuration.md): every key the worker reads.

## Say it in one line

vibey's Helm chart runs the worker, a dev PostgreSQL and, by default, 18 self-hosted surfaces; `surfaces.enabled=false` gives you the worker alone.
