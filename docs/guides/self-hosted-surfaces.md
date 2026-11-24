---
description: What the vibey Helm chart deploys for its 18 self-hosted operational surfaces, which ones need a token pasted after install, and what the chart does not set up for you.
---

# Run vibey's 18 self-hosted surfaces on your own cluster

> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** A default `helm install` of `deploy/helm/vibey` deploys all 18
> sovereign operational surfaces (issue tracker, docs, secrets, files, email, SMS, messaging,
> configuration, cache, bus, object storage, SIEM, forge, registry, identity, logs, status,
> monitoring) beside the worker: 26 Deployments in all. The worker runs from the start, falling
> back to in-memory stand-ins until you paste three tokens (Plane, BookStack, Infisical). Several
> defaults are for development only. Plan an hour, and a cluster with room for 25 services.

## The lesson

The Professor had a cluster dashboard open, and it was a long column of green.

**Daniel:** Professor, I asked Helm for vibey and got twenty-six deployments. Why does a coding
tool need a mail server and a chat server?

**Professor Feynman:** Think of a workshop. The bench is where the work happens, but a workshop
also needs a filing cabinet, a noticeboard, a post box and a lock on the door. vibey's worker is
the bench. The surfaces are the rest of the workshop: a tracker for issues, a wiki for docs, a
vault for secrets, a mailbox, a chat room, and so on. The rule is that each one is free software
you host yourself, never a paid service you rent by default.

**Daniel:** And they all work the moment the install finishes?

**Professor Feynman:** Most of them start with passwords the chart made up. Three of them cannot:
the tracker, the wiki and the configuration store want you to log in through their web pages and
make a token. Until you do, the worker uses a stand-in that keeps things in memory, so it never
refuses to start.

**Daniel:** So the green column means everything is ready?

**Professor Feynman:** That is the gap in the picture. Green means the pods are serving. It does
not mean every surface is wired: the chart never registers a chat user or creates storage keys,
and it opens the chat server to anyone who can reach it. A workshop with every cupboard installed
can still have empty cupboards and an unlocked door. Read the "not set up for you" list before you
trust it.

**Daniel:** What would I turn off for a small trial?

**Professor Feynman:** All of it, with one switch, `surfaces.enabled=false`, or one surface at a
time. The worker runs without them.

## Do it

The commands below assume a release named `vibey` in namespace `vibey`, so every object is named
`vibey-vibey-...` (the chart names objects `<release>-vibey-...`). Use your own release name in
its place. The install steps are the [Kubernetes guide](kubernetes.md)'s; this page starts after
`helm install`.

1. Confirm every surface came up. This is the same check CI's `cluster-smoke` job makes.

   ```bash
   kubectl get deployments -n vibey
   ```

   You should see 26 Deployments, every one `READY 1/1`: the 25 surface Deployments and
   `vibey-vibey-worker`.

2. Set up Plane, the issue tracker. Open its web page:

   ```bash
   kubectl port-forward svc/vibey-vibey-plane-web 8090:80 -n vibey
   ```

   Browse to `http://localhost:8090`, create the workspace and project, and generate an API token
   from your profile. Then store it where the worker reads it:

   ```bash
   kubectl create secret generic vibey-vibey-plane-token \
     -n vibey \
     --from-literal=token="YOUR_PLANE_API_TOKEN" \
     --dry-run=client -o yaml | kubectl apply -f -
   ```

   The worker reads `surfaces.plane.workspaceSlug` (`vibey`) and `surfaces.plane.projectId` from
   the values, so set those to match what you created.

3. Set up BookStack, the documentation surface.

   ```bash
   kubectl port-forward svc/vibey-vibey-bookstack 8091:80 -n vibey
   ```

   Log in at `http://localhost:8091` with BookStack's own default administrator
   (`admin@admin.com`, password `password`) and change it at once. Go to **Edit Profile, API
   Tokens, Create Token**, then store the token id and secret:

   ```bash
   kubectl create secret generic vibey-vibey-bookstack-token \
     -n vibey \
     --from-literal=token-id="YOUR_TOKEN_ID" \
     --from-literal=token-secret="YOUR_TOKEN_SECRET" \
     --dry-run=client -o yaml | kubectl apply -f -
   ```

4. Set up Infisical, the configuration store.

   ```bash
   kubectl port-forward svc/vibey-vibey-infisical 8080:8080 -n vibey
   ```

   Create an organisation, a project and a Machine Identity with read access to secrets, generate
   its token, and store it:

   ```bash
   kubectl create secret generic vibey-vibey-infisical-token \
     -n vibey \
     --from-literal=machine-token="YOUR_MACHINE_TOKEN" \
     --dry-run=client -o yaml | kubectl apply -f -
   ```

5. Restart the worker so it reads the new tokens. The worker takes them as environment variables
   when its pod starts, so a changed Secret is not seen until then.

   ```bash
   kubectl rollout restart deployment/vibey-vibey-worker -n vibey
   ```

   You should see `deployment.apps/vibey-vibey-worker restarted`.

The secret names and keys are the ones the worker template reads
(`deploy/helm/vibey/templates/worker.yaml`); every one is marked optional, which is why the worker
starts without them. These steps were read from the chart, not run against a live cluster for this
page.

## Daniel's teach-back

**Daniel:** The chart puts a whole self-hosted workshop beside the worker: 18 surfaces, each free
software, all on by default. Most start with chart-made passwords; Plane, BookStack and Infisical
need me to log in, make a token, store it in a named Secret and restart the worker. Until then the
worker uses in-memory stand-ins. Green pods only mean the surfaces are serving, not that every one
is wired or safe.

**Professor Feynman:** Right. And remember the unlocked door: Synapse accepts anyone's
registration as shipped, so close it before the cluster is reachable by anyone else.

## What the chart deploys

With `surfaces.enabled: true` (the default), the chart provisions this topology. Each surface has a
`VibeySurface` resource naming the Deployments that serve it.

```text
                      +-------------------+
                      |   vibey worker    |
                      +---------+---------+
                                |
       +------------------------+------------------------+
       |                        |                        |
[Port-backed: 12]       [Chart-managed: 6]       [Shared backing: 3]
- Plane (tracker)       - Gitea (forge)          - PostgreSQL 17 (vibey,
- BookStack (docs)      - Distribution (registry)  plane, infisical DBs)
- OpenBao (secrets)     - Keycloak (identity)    - Redis (db 0 worker,
- Nextcloud (files)     - Loki (logs)              1 Plane, 2 Infisical)
- Postfix (email)       - Uptime Kuma (status)   - MariaDB (BookStack)
- Kannel (sms)          - Prometheus & Grafana
- Synapse (messaging)     (monitoring)
- Infisical (configstore)
- Redis (cache)
- RabbitMQ (bus)
- Garage (blob)
- Wazuh (siem)
```

**Port-backed** surfaces are wired into the worker through environment variables
(`VIBEY_TRACKER_*`, `VIBEY_DOCS_*`, `VIBEY_SECRETS_*` and so on). When a surface's settings are
incomplete, the worker uses an in-memory stand-in for it rather than failing to start
(`src/vibey/bootstrap.py`). **Chart-managed** surfaces are deployed and watched, but the worker does
not call them.

Every surface has its own switch, `surfaces.<name>.enabled`, and `surfaces.enabled: false` turns
all 18 off. The [Kubernetes guide](kubernetes.md) covers the install itself.

## Watching their health

Each surface's `VibeySurface` resource gets a `Ready` condition from vibey's kopf operator, which
re-checks every 60 seconds. When every listed Deployment has at least one available replica, it
reports `Ready=True` with reason `Available`; when any drops below one, `Ready=False` with reason
`Degraded`, naming the Deployments with no serving pods.

**The operator is off by default** (`operator.enabled: false`), because it is a cluster-scoped
controller. The 18 `VibeySurface` resources are created either way, but they have no status until
you install with `--set operator.enabled=true`.

## What the chart does not set up for you

These were read from the chart templates at develop `d91a3791e` and were not exercised against
live services for this page.

- **Synapse accepts open registration.** The init container writes `enable_registration: true` and
  `enable_registration_without_verification: true` into `homeserver.yaml`
  (`templates/synapse.yaml`). Anyone who can reach Synapse can create an account. There is no
  registration Job. The worker is handed `surfaces.synapse.adminToken` as its Matrix access token
  and `surfaces.synapse.roomId` as its room, but the chart registers no user, issues no token and
  creates no room; give those values real ones from your own Synapse. To register a user by hand,
  Synapse's own tool reads the shared secret from the config:

  ```bash
  kubectl exec -it deploy/vibey-vibey-synapse -n vibey -- \
    register_new_matrix_user -c /data/homeserver.yaml -u vibey -p "CHOOSE_A_PASSWORD" --admin http://localhost:8008
  ```

- **Garage has no layout, key or bucket.** The chart runs `/garage server` with a single-node
  `garage.toml` (`replication_factor = 1`, `db_engine = "sqlite"`). It does not assign a cluster
  layout, it does not import the `surfaces.garage.accessKey` and `secretKey` it hands to the
  worker, and it creates no bucket. The worker's blob adapter creates its bucket through the S3 API
  on first write, which Garage refuses for a key it does not know. Use Garage's own command-line
  tool inside the pod (`kubectl exec -it deploy/vibey-vibey-garage -n vibey -- /garage ...`) to
  apply a layout, import the key and create buckets, following Garage's documentation. For
  example, a further bucket:

  ```bash
  kubectl exec -it deploy/vibey-vibey-garage -n vibey -- \
    /garage bucket create custom-bucket
  ```

- **The forge is Gitea, not Forgejo.** The chart deploys `gitea/gitea:latest`
  (`surfaces.gitea`). Ratified sub-doctrine 8.b names **self-hosted Forgejo** as the sovereign
  default forge, and ADR-0096 and ADR-0097 are about Forgejo. The chart and the canon disagree;
  this page reports the chart.
- **The model server is off.** See the next section.

## Optional pieces in the chart

| Values key | Default | What it adds |
|---|---|---|
| `ollama.enabled` | `false` | An in-cluster Ollama server with a volume for its weights, a Job that pulls `ollama.model` onto it, and the worker pointed at it (`VIBEY_OLLAMA_URL`, `VIBEY_OLLAMA_MODEL`, `GPTOSSLOOP_*`). It asks for 16 GiB of memory. `ollama.model` is the stock `gpt-oss:20b`, not the heretic v2 build the CLI defaults to (ADR-0099); set it to `hf.co/mradermacher/gpt-oss-20b-heretic-v2-GGUF:MXFP4_MOE` to match. `ollama.qwenloopFeature: true` also pulls `qwen3:14b` and switches qwenloop on. |
| `keda.enabled` | `false` | A KEDA `ScaledObject` that scales the worker from 0 to 4 replicas on the count of claimable jobs in PostgreSQL. Needs KEDA installed in the cluster. |
| `backup.enabled` | `false` | A Velero `BackupStorageLocation` on the in-cluster Garage (bucket `vibey-backups`, which the chart does not create) and a daily `Schedule` at 02:00. Needs Velero installed. |
| `edge.enabled` | `false` | Ingress and cert-manager `Certificate` resources for the surfaces with a web interface. |
| `operator.enabled` | `false` | The kopf operator that reconciles `VibeyProject` and `VibeySurface` resources. |

## Defaults that are for development only

Many surface passwords and keys in `values.yaml` are fixed, published strings: the PostgreSQL
passwords, `surfaces.plane.secretKey`, `surfaces.bookstack.appKey`, the MariaDB passwords,
`surfaces.openbao.rootToken` (`root`), the Nextcloud, Postfix, Kannel, RabbitMQ, Keycloak and
Grafana passwords, the Synapse shared secret and token, the Infisical keys, and the Garage keys and
RPC secret. Override every one for any install another person can reach. Most surface images are
pinned by digest, but tagged `latest`.

## Hardening for production

Customise `values.yaml` as follows:

1. **External PostgreSQL.** Set `postgres.enabled: false` and point `dsn.existingSecret` at a
   managed PostgreSQL (CloudNativePG, AWS RDS, GCP Cloud SQL, Azure Flexible Server).
2. **Secrets.** Use `existingSecret` fields instead of inline values, and replace every default
   listed above.
3. **OpenBao.** Move it from dev mode (`-dev`, in-memory, root token `root`) to a multi-node
   cluster with Raft storage or a Consul backend.
4. **Keycloak.** Move it from `start-dev` and its built-in storage to PostgreSQL by configuring
   `KC_DB=postgres` and the database connection variables.
5. **Synapse.** Turn off open registration in `homeserver.yaml`.
6. **TLS ingress.** Set `edge.enabled: true` and `edge.issuer` to a production cert-manager
   `ClusterIssuer` for Let's Encrypt certificates.

## Architecture caveats: ARM64 and AMD64

- **Kannel** (`cyrenity/kannel:1.4.5-alpine`) and **Wazuh** (`wazuh/wazuh-manager`, `indexer`
  and `dashboard`, 4.14.2) publish **AMD64-only** images.
- On ARM64 nodes (Apple Silicon minikube, AWS Graviton), make sure Rosetta or QEMU emulation is
  active, or schedule those surfaces on an AMD64 node pool, or set
  `surfaces.kannel.enabled=false` and `surfaces.wazuh.enabled=false`.

## When it goes wrong

| What you see | What it means | What to do |
|---|---|---|
| A surface Deployment stays `0/1` on an ARM64 node | Kannel and Wazuh have AMD64-only images. | Enable emulation, use an AMD64 node pool, or disable those two surfaces. |
| Pods stay `Pending` | The cluster cannot fit 25 surfaces. CI gives minikube 4 CPUs and 10 GiB. | Add capacity, or disable surfaces you do not need with `surfaces.<name>.enabled=false`. |
| The worker still uses its in-memory tracker after you pasted a token | The worker read its environment before the Secret existed. | `kubectl rollout restart deployment/vibey-vibey-worker -n vibey`. |
| `kubectl create secret` worked but the worker ignores it | The Secret name does not match the release. | Name it `<release>-vibey-plane-token` (or `-bookstack-token`, `-infisical-token`). |
| `kubectl get vibeysurfaces -n vibey` shows no status | The operator is off by default. | Upgrade with `--set operator.enabled=true`. |
| Blob writes fail with an HTTP error from Garage | Garage has no layout, or does not know the worker's key. | Apply a layout and import the key with Garage's own tool, as above. |

## Where next

- [Run vibey on Kubernetes](kubernetes.md), for the install itself and the worker's settings.
- [ADR-0042](../architecture/decisions/0042-sovereign-self-hosted-defaults-and-declared-paid-relays.md)
  and [ADR-0043](../architecture/decisions/0043-sovereign-surfaces-install.md), for why every
  surface defaults to free software you host yourself.
- [The configuration reference](../reference/configuration.md), for the `[surfaces]` settings on
  the vibey side.

## Say it in one line

vibey's Helm chart self-hosts 18 free operational surfaces beside the worker; paste three tokens,
restart the worker, and replace the development defaults before anyone else can reach it.
