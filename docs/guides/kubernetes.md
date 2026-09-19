# Running vibey on Kubernetes

This guide takes vibey from a laptop process to a long-lived deployment:
a containerized worker, a Helm chart, an in-cluster PostgreSQL, and
queue-depth autoscaling via KEDA. Everything below was verified on
minikube (Kubernetes v1.35.1). The chart is written so the same install
works against a managed Postgres on AKS/EKS/GKE by setting
`postgres.enabled=false` and `dsn.existingSecret` (there are no per-cloud
values presets yet), but only the local path has been exercised end to
end so far. The design decisions behind the image, chart, operator, and
autoscaler are recorded in
[ADR-0025](../architecture/decisions/0025-kubernetes-operator-crd-keda.md)
and
[ADR-0026](../architecture/decisions/0026-tini-pid1-and-the-sigterm-latch.md).

## What works today, and what does not

Be clear about this before you install anything:

- **The worker runs, applies migrations, claims jobs, and autoscales.**
- **One vendor engine binary ships in the image: `codex`.** Since
  [ADR-0037](../architecture/decisions/0037-one-distribution-one-version.md)
  the image carries every runner's console script (`claudeloop`,
  `codexloop`, `cursorloop`, `agyloop`, `qwenloop`), but three of those
  drive a vendor CLI that is still absent: `claude`, `cursor-sdk-bridge`,
  and `agy`. The fourth, `codex`, is now in the image as upstream's static
  musl build — pinned by version and sha256, copied into the runtime layer
  alone, with no Node and no npm (step 1). So codexloop is the one paid
  engine that can run in a pod today, given `OPENAI_API_KEY` or
  `CODEX_API_KEY`; nothing in CI has run a live codex session in-cluster
  yet. `qwenloop` needs no vendor binary, only a model server, which the
  chart can now run for it (step 8). Without either, in-cluster runs use
  `--provider scripted`, and the worker logs `no recorded conformance for
  agyloop, claudeloop, codexloop, cursorloop`. That warning is correct,
  not a misconfiguration. The remaining engines in-cluster are workstreams
  [05](../runbooks/expansion/05-server-mode-kubernetes.md) item 1 and
  [16](../runbooks/expansion/16-loop-runner-containers.md).
- **Engine authentication in a pod is by API key only.** Subscription
  login is an interactive TTY flow and does not exist in a cluster. When
  an image does carry engine binaries, the chart reads their keys from a
  Secret you create: set `engineAuth.existingSecret` to its name and list
  `engineAuth.keys` as `{name, key}` pairs (environment variable name,
  key inside the Secret), for example
  `{name: ANTHROPIC_API_KEY, key: anthropic}`. They are injected into the
  worker Deployment only. The variables each engine looks for are
  `ANTHROPIC_API_KEY` or `ANTHROPIC_AUTH_TOKEN` (claudeloop);
  `OPENAI_API_KEY`, `AZURE_OPENAI_API_KEY`, or `CODEX_API_KEY`
  (codexloop); `CURSOR_API_KEY` (cursorloop); and `GOOGLE_API_KEY`,
  `GEMINI_API_KEY`, or `GOOGLE_APPLICATION_CREDENTIALS` (agyloop).
  `vibey doctor --cluster` reports `engine-auth` as `FAIL` for any
  installed engine without one.
- **The operator is implemented, but off by default.** `vibey operator`
  (`pip install 'vibey[operator]'`) runs kopf handlers that create
  projects and apply `spec.answers` through the same application services
  `vibey new` / `vibey answer` use, then reconcile `VibeyProject` status
  every 15s. The chart does not install it unless you set
  `operator.enabled=true` (step 7 below); without that flag, creating
  projects and answering gates is still `vibey new` / `vibey answer`, run
  inside a pod or against the database.

## Prerequisites

- Docker (or colima) and `minikube`, `helm`, `kubectl`.
- For autoscaling, KEDA installed in the cluster (step 5).

## 1. Build the image into the cluster's daemon

The chart defaults to `image.pullPolicy: Never` and tag `vibey:dev`,
because a locally built image has never been pushed anywhere and `Always`
would send kubelet hunting a registry that has never seen it. Build
directly into minikube's Docker daemon:

```bash
minikube start -p vibey
eval $(minikube -p vibey docker-env)
docker build -f deploy/docker/Dockerfile -t vibey:dev .
```

No prebuilt image is published — not to ghcr.io, not to Docker Hub. CI's
`image` job builds amd64 and arm64 on every push and pull request and
contract-tests the amd64 build, but it never pushes either. The only
ghcr.io artifact the project publishes is the Python distribution
(`ghcr.io/the-vibey-project/vibey/python`), which is a wheel and an sdist
pushed with `oras`, not a runnable image. For any cluster other than
minikube, build and push to a registry you control, then point the chart
at it:

```bash
docker buildx build -f deploy/docker/Dockerfile \
  --platform linux/amd64,linux/arm64 \
  -t <registry>/vibey:<tag> --push .
helm install vibey deploy/helm/vibey -n vibey --create-namespace \
  --set image.repository=<registry>/vibey --set image.tag=<tag> \
  --set image.pullPolicy=IfNotPresent
```

The image is two-stage on purpose: the runtime layer carries no compiler,
no `uv`, and no `pip` (the base image's pip is deleted), so a compromised
engine session inside a worker finds nothing it can install with.
`apt-get` remains, because the runtime stage uses it to install git and
`tini`, but it needs root and the pod runs as uid 10001 with
`allowPrivilegeEscalation: false`. The entrypoint is
`tini -g -- vibey` (see step 6). Migrations ship inside the image, so an
install never depends on someone running SQL by hand first.

`codex` reaches the image the same way: the build stage downloads
upstream's static musl release for the architecture it is building
(`dpkg --print-architecture`, because cluster-smoke's classic builder
never sets `TARGETARCH`), checks it against the sha256 pinned in the
Dockerfile, and the runtime stage copies the one executable to
`/usr/local/bin/codex`, with its `LICENSE` and `NOTICE` under
`/usr/share/doc/codex/`. The npm package would have brought Node and npm
with it; the static build brings neither. To move to another codex
release, change `CODEX_VERSION` and every `CODEX_*_SHA256` build argument
together — a stale digest fails the build at `sha256sum -c`.

CI asserts each of these against the amd64 build: the entrypoint runs,
`id -u` is 10001, none of `uv pip pip3 gcc cc node npm npx` is on `PATH`,
`/app/migrations/*.sql` is non-empty, `codex --version` prints the
version the Dockerfile pins, and every console script is on `PATH`.

## 2. Install the chart

```bash
helm install vibey deploy/helm/vibey -n vibey --create-namespace
```

This creates a ServiceAccount, a worker Deployment, a worktree PVC
(mounted at `/work`, the worker's working directory), a `vibey-vibey-dsn`
Secret, and a single-replica PostgreSQL StatefulSet behind a headless
Service. An init container waits for Postgres so the failure mode is
"pod pending" rather than "CrashLoopBackOff with a stack trace", and the
worker applies migrations itself at startup.

The built-in Postgres is **development only** — `postgres.password`
defaults to `vibey` in plain values. For anything real, set
`postgres.enabled: false` and point `dsn.existingSecret` at a Secret
whose `dsn` key (or the key named by `dsn.existingSecretKey`) holds the
managed instance's DSN. The chart injects it as `VIBEY_PG_URL` into the
worker and, when enabled, the operator. Use a fully qualified host or an
IP address: KEDA reads the same DSN from another namespace.

The `wait-for-postgres` init container is rendered only for the built-in
Postgres. Against a managed instance the worker connects directly at
startup, so an unreachable DSN shows up as `CrashLoopBackOff` rather than
a pending pod. Check `vibey doctor --cluster` (`database` and `dsn-host`)
first.

## 3. Create a project

A worker with nothing to do would normally exit, which in a Deployment is
a restart loop that ends only when a human creates a project — and the
crash counter makes a healthy worker look broken. The chart therefore
sets `--wait-for-project 15`, so the worker parks and polls:

```
no project yet; polling every 15s
```

Create one from inside the cluster:

```bash
kubectl exec -n vibey deploy/vibey-vibey-worker -- \
  vibey new demo --repo /work/demo --max-cycles 1
```

> **Set `worker.project` explicitly.** Left empty, the worker binds to
> whichever project was created most recently — convenient on a laptop, a
> footgun in a cluster the moment a second project exists. The value is
> the project **UUID**, not its name. `vibey new` prints it on creation;
> there is no list-projects command yet, so otherwise read it from the
> database (`SELECT id, name FROM project;`). The chart does not enforce
> this — with the value empty it omits `--project` and installs anyway —
> so it is on you. A value that is set but is not a UUID fails at
> `helm install`/`helm template` time rather than in the pod, because
> the autoscaler's query uses it too (step 5):
>
> ```bash
> helm upgrade vibey deploy/helm/vibey -n vibey \
>   --set worker.project=<uuid>
> ```

## 4. Watch it work

```bash
kubectl logs -n vibey deploy/vibey-vibey-worker -f
```

```
sigterm handler registered
worker started: project=demo engines=all parallelism=2 provider=scripted
processed one job
```

`kubectl logs` interleaves stdout and stderr. A current worker also
writes per-iteration diagnostics to stderr —
`drive[N] iter=M calling run_once`,
`drive[N] iter=M run_once returned worked=…`, and
`drive[N] iter=M reap done, waiting for notify` — so the real log is
noisier than the sample above. Those lines are expected.

## Preflight from inside a pod

A worker can start, log `worker started`, report Ready, and still do no
work: its worktree volume is not writable, an engine has no credentials,
or its DSN is one the autoscaler cannot resolve. `vibey doctor --cluster`
checks that wiring from inside the pod:

```bash
kubectl exec -n vibey deploy/vibey-vibey-worker -- vibey doctor --cluster
```

It prints one `PASS` or `FAIL` line per check and exits non-zero if any
check fails:

| Check | Passes when |
|---|---|
| `dsn-host` | the DSN host is fully qualified, an IP address, or `localhost`, so KEDA's operator in another namespace can resolve it |
| `non-root` | the process uid is not 0 |
| `workspace-writable` | the working directory (`/work` in the chart) accepts a write |
| `engine-auth` | every engine binary on `PATH` has one of its API-key variables set; an image with no engine binaries passes as the scripted-provider image |
| `database` | the DSN connects |
| `migrations` | every file in `/app/migrations` is recorded in `schema_migration`; runs only when `database` connected |

Run it whenever a worker reports Ready but does no work.

## 5. Autoscaling with KEDA

KEDA is a cluster-wide operator and is not assumed, so the ScaledObject is
off by default and inert without it.

```bash
helm repo add kedacore https://kedacore.github.io/charts
helm install keda kedacore/keda -n keda --create-namespace --wait
helm upgrade vibey deploy/helm/vibey -n vibey --set keda.enabled=true
```

The trigger is the **claimable-work** query — ready, due now, in the
project this worker serves, and not blocked behind an unsatisfied
dependency — deliberately mirroring `JobRepository.claim`'s SELECT arm.
Scaling on raw queue depth would start workers for jobs nothing can claim
yet.

The project scoping matters as soon as a database holds two projects. A
worker claims only its own project's jobs, so a count across every
project would scale up workers for work they will never claim, and let
another project's backlog hold this pool above zero. With
`worker.project` set, the query counts that project only. Left empty, it
counts the project a worker starting now would bind to — the newest, by
the same `ORDER BY created_at DESC` the worker uses — which is right for
a single-project install and approximate once a second project is
created while workers are running: a running worker stays bound to the
project it started with. Set `worker.project` whenever KEDA is on.

Measured behavior on minikube with `maxReplicas: 4`:

| Event | Observed |
|---|---|
| 20 claimable jobs enqueued | 0 → 4 replicas in ~8s |
| queue drained | 4 → 0 after the 300s `cooldownPeriod` |
| pod receives SIGTERM | exits in 4-5s |

Note that the N→0 transition happens in **one step**. KEDA's deactivation
path sets the replica count directly and bypasses the HPA `scaleDown`
behavior policy entirely. That policy only smooths HPA-driven scaling
between `minReplicas` and max — do not read it as protection against
losing several in-flight sessions at once.

## 6. Scale-in and long sessions

Engine sessions run for minutes to hours, so `terminationGracePeriodSeconds`
defaults to **7200**. That is a ceiling for one long in-flight turn, not
an expected shutdown time.

On SIGTERM the worker drains: it finishes the job in hand and claims no
more, then exits.

```
draining on SIGTERM: finishing in-flight job, claiming no more
```

An idle worker therefore exits in seconds. Only a worker genuinely
mid-turn uses any meaningful part of the grace period.

Two details make this hold in the window before the worker is fully up
([ADR-0026](../architecture/decisions/0026-tini-pid1-and-the-sigterm-latch.md)):

- **`tini` is PID 1.** The image's entrypoint is
  `/usr/bin/tini -g -- vibey`. Linux discards a signal sent to PID 1
  while its disposition is still the default, and a Python interpreter
  needs hundreds of milliseconds to start and install a handler. On
  minikube, a pod deleted a fraction of a second after its container
  started was observed sitting out the entire 7200s grace period, still
  claiming jobs. `tini` is ready in microseconds and forwards the signal;
  `-g` sends it to the whole process group, so an engine subprocess the
  worker started is signalled too. Gate commands, an engine's `--version`
  and `doctor` probes, and the `vibey-skills` CLI are the exception: each
  leads a process group of its own so vibey can kill everything it started,
  and the worker kills that group itself on a timeout or when the task
  running it is cancelled. Anything still running when the container stops
  ends with the pod's PID namespace.
- **A SIGTERM latch catches the startup window.** `vibey` arms a small
  handler before its other imports whose only job is to remember that
  SIGTERM arrived. Once the event loop is running and the real drain
  handler is installed, the worker checks the latch; if it fired, the
  worker logs `SIGTERM arrived during startup; draining immediately` and
  claims nothing.

CI's drain contract deletes a worker pod and requires it to terminate in
under 60s. It records the container's start time, because a delete that
lands during boot tests the startup race and a delete after boot tests
the steady-state drain; both must pass.

## 7. The kopf operator (optional)

The chart can also install a cluster-scoped operator that reconciles
`VibeyProject` custom resources, so a project is a CR instead of a
`kubectl exec` command:

```bash
helm upgrade vibey deploy/helm/vibey -n vibey --set operator.enabled=true
```

This installs, in addition to the worker:

- the `VibeyProject` CRD (`vibeyprojects.vibey.dev`, short name `vp`),
  annotated `helm.sh/resource-policy: keep` so `helm uninstall` never
  deletes a project mid-`BUILD` along with it. Set
  `operator.installCRD=false` if another release already owns the CRD.
- a `ClusterRole` scoped to `vibeyprojects`/`vibeyprojects/status`
  (`list, watch, get, patch, update` — deliberately no `delete`) plus
  `create` on `events`, `list, watch` on `customresourcedefinitions` and
  `namespaces` (kopf's discovery), and `list, watch, patch, get` on
  `kopfpeerings`/`clusterkopfpeerings` for kopf peering.
- a single-replica operator Deployment (`strategy.type: Recreate`; two
  operators patching the same CR is a race with no upside at this scale).
  Set `operator.watchNamespace` to scope it to one namespace instead of
  the cluster.

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

Keys under `spec.answers` are gate UUIDs — read them from
`status.openGates[].gateId` — and each value is the same object
`vibey answer` sends: `{choice: …}` for deployment and triage gates,
`{verdict: …}` for review gates, and `{<question_id>: <answer>, …}` for
interview gates.

The CR also accepts `maxCycleTurns` and
`skillsContext: {mode, budget, timeout_seconds, kill_grace_seconds}` (`mode`
is `off`, `shadow`, or `inject`; `budget` is 1,000–32,000, default 6,000).
`spec.engines` is restricted by the CRD schema to the four paid engines,
so `qwenloop` cannot be named in a CR today. The worker accepts
`--provider qwenloop` (chart value `worker.provider`) for the sovereign
DESIGN provider, but the stock image carries no `qwenloop` binary, so
that path needs an image that ships it.

The operator creates the project on first reconcile, then re-reconciles
every 15s. It applies any new `spec.answers` through the same gate-answer
service `vibey answer` calls. A key naming an already-answered gate, a
key that is not a UUID, or a value that is not an object is recorded in
`status.ignoredAnswers` as `{key, reason}`, not treated as an error.

Each reconcile writes:

- `status.projectId` — the guard that stops a re-applied CR from creating
  a second project;
- `status.phase`, `status.cycle`, and `status.maxCycles`;
- `status.openGates` — `{gateId, kind, prompt}` per open gate;
- three conditions: `Ready` (`True`/`Progressing`, or `False` with
  `AwaitingHuman`, `Complete`, or `Abandoned`; `Unknown`/`ProjectMissing`
  if the project row is gone), `Parked` (`True` with the gate kind
  CamelCased as the reason, for example `BudgetExhausted`), and
  `Complete`.

`kubectl get vp` shows Phase, Cycle, Ready, Parked, Reason (the Parked
reason), and Age as columns; `kubectl describe` shows the full status.
The operator never deletes a project, so removing the CR does not remove
the underlying project or its data.

## 8. Sovereign inference: an in-cluster Ollama (optional)

Sub-doctrine 8.a makes the sovereign path the preference rather than the
fallback, and until now a cluster could not take it: qwenloop and
vibey's sovereign DESIGN provider both need a model server, and the
chart had none. It can run one:

```bash
helm upgrade vibey deploy/helm/vibey -n vibey --set ollama.enabled=true
```

This adds, all named `<release>-vibey-ollama`:

- a PersistentVolumeClaim for the weights (`ollama.storage.size`,
  default `30Gi`), mounted at `/ollama` as both `HOME` and
  `OLLAMA_MODELS`, so a restarted pod serves at once instead of
  downloading again;
- a ClusterIP Service on port `11434` (`ollama.service.port`);
- a single-replica Deployment on `ollama/ollama:0.34.2`, pinned by the
  digest of its multi-arch index (`ollama.image.digest`), with
  `strategy: Recreate` because the weights volume is ReadWriteOnce, and
  readiness and liveness probes on `/api/version`, which answers without
  loading a model;
- a Job, `<release>-vibey-ollama-pull-<hash>`, that waits for the server
  and then runs `ollama pull <ollama.model>`: the image has no curl, and
  its own CLI POSTs `/api/pull` to the server named by `OLLAMA_HOST`. The
  suffix is a hash of the Job's pod template, so an upgrade that changes
  the model, image, or endpoint starts a new pull, and one that changes
  none of them pulls nothing. Set `ollama.pull.enabled=false` to manage
  models yourself.

It also points the worker at the server. The URL is fully qualified for
the same reason the DSN is:

| Variable | Value (release `vibey`, namespace `vibey`) | Read by |
|---|---|---|
| `VIBEY_OLLAMA_URL` | `http://vibey-vibey-ollama.vibey.svc.cluster.local:11434` | vibey's sovereign DESIGN and decompose providers (`worker.provider: qwenloop`) |
| `VIBEY_OLLAMA_MODEL` | `ollama.model` | the same |
| `QWENLOOP_BASE_URL` | the same URL plus `/v1` | qwenloop's `openai-compat` backend, which `auto` selects whenever a base URL is set |
| `QWENLOOP_MODEL` | `ollama.model` | the same |
| `VIBEY_FEATURE_QWENLOOP` | `1`, unless `ollama.qwenloopFeature=false` | the worker's qwenloop switch — the only one that reaches a worker ([ADR-0015](../architecture/decisions/0015-qwenloop-standby.md)) |

The first two are read by vibey's configurable Ollama client (#255) and
the next two by qwenloop's `openai-compat` backend (#243); an image built
before those landed ignores them.

With only `ollama.enabled`, qwenloop joins the worker as the BUILD
standby: it is selected only when no paid engine is eligible. To route
work to it on purpose:

```bash
helm upgrade vibey deploy/helm/vibey -n vibey --set ollama.enabled=true \
  --set worker.provider=qwenloop --set worker.engines=qwenloop
```

`worker.provider=qwenloop` runs DESIGN and decomposition on the local
model; `worker.engines=qwenloop` narrows BUILD to qwenloop alone. Either
works without the other.

**Sizing.** The default model is `qwen2.5-coder:14b` (about 9 GB), the
one vibey and qwenloop already default to. The server requests 2 CPUs and
`16Gi` with a `24Gi` limit, sized for CPU inference of that model at a
32K context: `ollama.contextLength` (default `32768`) becomes
`OLLAMA_CONTEXT_LENGTH`, because qwenloop runs a 32K context and Ollama's
own default window is far smaller and truncates longer prompts silently.
Lower the resources only together with a smaller model or context.

**GPU.** `--set ollama.gpu.enabled=true` adds `nvidia.com/gpu: 1`
(`ollama.gpu.resourceName`, `ollama.gpu.count`) to the container's
limits. Pair it with `ollama.nodeSelector` and `ollama.tolerations` for
the GPU pool, and `ollama.runtimeClassName` where the cluster needs one
(for example `nvidia`). These are separate from the worker's own
`nodeSelector`/`tolerations`, so the worker never lands on a GPU node by
accident.

**Security context.** The ollama image runs as root by default. The
chart runs it as uid 10001 instead, with its own
`ollama.podSecurityContext` and `ollama.securityContext` rather than the
chart-wide ones, and points `HOME` and `OLLAMA_MODELS` at the volume so
that uid can write its key pair and weights. If a storage class does not
honour `fsGroup`, restore the image default for this pod alone with
`ollama.podSecurityContext.runAsUser=0` and `runAsNonRoot=false`; the
worker is unaffected.

**The first install downloads gigabytes.** Depending on your Helm
version's wait strategy, `helm install --wait` may wait for the pull Job
as well as the Deployments, so give a first install a generous
`--timeout`, or install without `--wait` and follow the pull:

```bash
kubectl logs -n vibey -f job/$(kubectl get jobs -n vibey \
  -l app.kubernetes.io/component=ollama-pull -o name | head -n 1 | cut -d/ -f2)
kubectl exec -n vibey deploy/vibey-vibey-worker -- qwenloop doctor
```

Everything this section describes is rendered, linted and compared
against a committed golden in CI (the `chart` job,
`deploy/helm/golden/render.sh`); none of it is installed on a cluster by
CI, because cluster-smoke has neither the memory nor a GPU for a 14B
model.

## Troubleshooting

**`helm upgrade` fails with `lookup <release>-postgres ... no such host`.**
You are on a chart older than the DSN fix. KEDA's operator runs in its own
namespace and dials Postgres itself, so the DSN must be fully qualified —
a bare Service name resolves only from inside the release namespace, which
is why the worker was fine and the autoscaler was not. Set
`clusterDomain` if your cluster does not use `cluster.local`.

**Deployment shows `0/0` but pods are still `Terminating` and working.**
Either the worker is ignoring SIGTERM (an image built before the drain
landed) or the signal was discarded before the worker could catch it (an
image whose PID 1 is Python rather than `tini`, built before `tini`
became the entrypoint). Both look the same: `kubectl` reports capacity
released while the pods still hold CPU, memory, and Postgres connections
and keep claiming jobs. Rebuild from the current
`deploy/docker/Dockerfile`. On a current image the pod's log shows
`sigterm handler registered` at boot and, on delete, either
`draining on SIGTERM: finishing in-flight job, claiming no more` or
`SIGTERM arrived during startup; draining immediately`. If neither
appears after a delete, the image is old.

**`kubectl delete pod --force --grace-period=0` leaves workers running.**
Force delete removes the pod object without waiting for the container to
die, exactly as its warning says. The container keeps running, keeps its
database connections, and **keeps claiming jobs** — invisible to
`kubectl`, since the pod is gone from the API server. Check with:

```bash
kubectl exec -n vibey vibey-vibey-postgres-0 -- \
  psql -U vibey -d vibey -c \
  "SELECT client_addr, count(*) FROM pg_stat_activity
   WHERE datname='vibey' AND client_addr IS NOT NULL GROUP BY client_addr;"
```

Connections from addresses with no corresponding pod are orphans; kill
them at the container runtime (`docker kill` inside `minikube docker-env`).
Prefer a normal delete — the drain makes it fast.

**Workers scale up but claim nothing.** On a chart older than 0.2.0 the
scaler counted claimable jobs across *all* projects while the worker
binds to one, so work in another project scaled up workers that could
not claim it. From 0.2.0 the query is scoped to the worker's project
(step 5). If it still happens, `worker.project` is probably empty and a
newer project was created after the running workers bound to an older
one — set `worker.project`.

**A worker is Ready but does no work.** Run `vibey doctor --cluster`
inside the pod (see [Preflight from inside a pod](#preflight-from-inside-a-pod)).

## Values worth knowing

| Value | Default | Why |
|---|---|---|
| `image.repository` / `image.tag` | `vibey` / `dev` | local build; override for any registry |
| `image.pullPolicy` | `Never` | change to `IfNotPresent` once the image is in a registry |
| `worker.terminationGracePeriodSeconds` | `7200` | ceiling for one long in-flight turn |
| `worker.waitForProjectSeconds` | `15` | park instead of restart-looping |
| `worker.parallelism` | `2` | concurrent job loops per pod |
| `worker.project` | `""` | **set this**; empty binds to the newest project |
| `worker.provider` | `scripted` | DESIGN/decompose provider; `claudeloop` or `qwenloop` need an image that ships the binary |
| `worker.engines` | `""` | comma-separated engine allow-list (`--engines`); empty means all |
| `worker.extraEnv` | `[]` | extra EnvVar objects for the worker, appended after the chart's own |
| `worker.replicas` | `1` | ignored once KEDA owns the Deployment |
| `worker.worktrees.size` / `storageClass` | `5Gi` / `""` | the `/work` PVC where BUILD worktrees live |
| `engineAuth.existingSecret` | `""` | Secret holding engine API keys |
| `engineAuth.keys` | `[]` | `{name, key}` pairs mapped to env vars on the worker |
| `keda.minReplicas` / `maxReplicas` | `0` / `4` | scale to zero when idle |
| `keda.pollingInterval` | `15` | seconds between scaler queries |
| `keda.cooldownPeriod` | `300` | delay before deactivating to zero |
| `clusterDomain` | `cluster.local` | only change on a custom `--service-dns-domain` |
| `postgres.enabled` | `true` | dev only; use `dsn.existingSecret` for managed |
| `postgres.storage` | `8Gi` | dev Postgres PVC |
| `dsn.existingSecret` | `""` | Secret holding a managed instance's DSN |
| `dsn.existingSecretKey` | `dsn` | key inside `dsn.existingSecret` |
| `operator.enabled` | `false` | install the kopf `VibeyProject` operator |
| `operator.watchNamespace` | `""` | empty watches cluster-wide |
| `operator.installCRD` | `true` | disable if another release already owns the CRD |
| `ollama.enabled` | `false` | run an in-cluster Ollama and point the worker at it (step 8) |
| `ollama.image.tag` / `digest` | `0.34.2` / its index digest | pinned; bump both together, an empty digest falls back to the tag |
| `ollama.model` | `qwen2.5-coder:14b` | pulled by the Job; exported to the worker as `VIBEY_OLLAMA_MODEL` and `QWENLOOP_MODEL` |
| `ollama.contextLength` | `32768` | `OLLAMA_CONTEXT_LENGTH`; qwenloop runs a 32K context |
| `ollama.storage.size` / `storageClass` | `30Gi` / `""` | the weights PVC |
| `ollama.resources` | 2 CPU, `16Gi` request / `24Gi` limit | CPU inference of the default model |
| `ollama.gpu.enabled` | `false` | add `ollama.gpu.resourceName` (`nvidia.com/gpu`) × `ollama.gpu.count` (`1`) to limits |
| `ollama.podSecurityContext` / `securityContext` | uid 10001, non-root, no capabilities | the Ollama pod's own; the image's default is root |
| `ollama.pull.enabled` | `true` | the pull Job; `activeDeadlineSeconds` `3600`, `backoffLimit` `6` |
| `ollama.qwenloopFeature` | `true` | also set `VIBEY_FEATURE_QWENLOOP=1` on the worker |
