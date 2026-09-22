# Sovereign operational surfaces: self-hosted cluster install

`vibey` orchestrates software delivery end-to-end on sovereign defaults:
every operational dependency — issue tracking, documentation, secrets, files,
email, SMS, messaging, configuration store, caching, message bus, object
storage, and SIEM — is self-hosted and free-software-first ([ADR-0042](../architecture/decisions/0042-sovereign-self-hosted-defaults-and-declared-paid-relays.md),
[ADR-0043](../architecture/decisions/0043-sovereign-surfaces-install.md)).

The Helm chart (`deploy/helm/vibey`) packages and deploys all 18 sovereign
surfaces directly into your Kubernetes cluster, with health continuously
observed by the vibey kopf operator via `VibeySurface` custom resources.

## Architecture

In an all-defaults deployment (`surfaces.enabled: true`), the chart provisions
the following in-cluster topology:

```
                      +-------------------+
                      |   vibey worker    |
                      +---------+---------+
                                |
       +------------------------+------------------------+
       |                        |                        |
[Port-backed: 12]       [Chart-managed: 6]       [Shared Backing: 3]
- Plane (tracker)       - Gitea (forge)          - PostgreSQL (+ plane,
- BookStack (docs)      - Distribution (registry)  infisical DBs)
- OpenBao (secrets)     - Keycloak (identity)    - Redis (db 0, 1, 2)
- Nextcloud (files)     - Loki (logs)            - MariaDB (BookStack)
- Postfix (email)       - Uptime Kuma (status)
- Kannel (sms)          - Prometheus & Grafana
- Synapse (messaging)     (monitoring)
- Infisical (configstore)
- Redis (cache)
- RabbitMQ (bus)
- Garage (blob)
- Wazuh (siem)
```

The operator periodically checks every surface's backing Deployments. When all
pods are serving, the surface's `VibeySurface` status condition reports
`Ready=True` with reason `Available`. If any component drops below 1 available
replica, the condition reports `Ready=False` with reason `Degraded`.

## Initial Setup & Pasted Token Workflow

Most services are fully automated with chart-managed static credentials
generated or provided at install time (Nextcloud, Postfix, Kannel, Synapse,
OpenBao, Redis, RabbitMQ, Garage, Wazuh).

Three services operate on human/operator UI authentication tokens. To allow
unattended initial deployment, the worker starts cleanly with in-memory fallbacks
until the operator pastes the tokens into the cluster Secret:

### 1. Issue Tracker: Plane
- **Deployments:** `plane-api`, `plane-worker`, `plane-beat`, `plane-web`.
- **Database:** PostgreSQL database `plane` (initialized via `plane-migrator` Job).
- **Activation:**
  1. Port-forward or access the Plane web UI:
     ```bash
     kubectl port-forward svc/vibey-plane-web 8090:80 -n vibey
     ```
  2. Complete initial workspace and project setup.
  3. Generate an API token from your user profile.
  4. Patch the secret:
     ```bash
     kubectl create secret generic vibey-plane-token \
       -n vibey \
       --from-literal=token="YOUR_PLANE_API_TOKEN" \
       --dry-run=client -o yaml | kubectl apply -f -
     ```

### 2. Documentation: BookStack
- **Deployments:** `bookstack` and `bookstack-mariadb`.
- **Activation:**
  1. Access BookStack web UI (default admin user: `admin@admin.com`, password: `password`).
  2. Navigate to **Edit Profile -> API Tokens -> Create Token**.
  3. Store the Token ID and Token Secret:
     ```bash
     kubectl create secret generic vibey-bookstack-token \
       -n vibey \
       --from-literal=token-id="YOUR_TOKEN_ID" \
       --from-literal=token-secret="YOUR_TOKEN_SECRET" \
       --dry-run=client -o yaml | kubectl apply -f -
     ```

### 3. ConfigStore: Infisical
- **Deployments:** `infisical` (reuses chart PostgreSQL database `infisical` and Redis db 2).
- **Activation:**
  1. Access the Infisical web UI:
     ```bash
     kubectl port-forward svc/vibey-infisical 8080:8080 -n vibey
     ```
  2. Create an organization, project, and Machine Identity with Secret Read permissions.
  3. Generate a Client Secret / Machine Token:
     ```bash
     kubectl create secret generic vibey-infisical-token \
       -n vibey \
       --from-literal=machine-token="YOUR_MACHINE_TOKEN" \
       --dry-run=client -o yaml | kubectl apply -f -
     ```

## Bootstrap Jobs & Manual Fallbacks

### Synapse Messaging User Registration
The chart runs an initial registration job to generate credentials. If manual
registration is needed:
```bash
kubectl exec -it deploy/vibey-synapse -n vibey -- \
  register_new_matrix_user -c /data/homeserver.yaml -u vibey -p "secret" --admin http://localhost:8008
```

### Garage S3 Object Storage Layout
Garage runs with `--single-node --default-access-key --default-bucket`. If
manually creating additional buckets:
```bash
kubectl exec -it deploy/vibey-garage -n vibey -- \
  /garage bucket create custom-bucket
```

## Architecture Caveats (ARM64 vs. AMD64)

- **Cyrenity Kannel** (`cyrenity/kannel:1.4.5-alpine`) and **Wazuh**
  (`wazuh/wazuh-manager`, `indexer`, `dashboard` 4.14.2) publish **AMD64-only**
  container images.
- When deploying on ARM64 nodes (e.g. Apple Silicon minikube, AWS Graviton),
  ensure Rosetta or QEMU binary emulation is active, or target an AMD64 node pool.

## Production Hardening Guidelines

For production environments, customize `values.yaml` as follows:

1. **External PostgreSQL:**
   Set `postgres.enabled: false` and point `dsn.existingSecret` at a managed
   PostgreSQL instance (CloudNativePG, AWS RDS, GCP Cloud SQL, Azure Flexible
   Server).
2. **Secrets Management:**
   Use `existingSecret` fields instead of inline values in `values.yaml`.
3. **OpenBao Production Mode:**
   Transition OpenBao from dev-mode (`-dev`) to a multi-node cluster with Raft
   storage or Consul backend.
4. **Keycloak Database:**
   Migrate Keycloak from default `start-dev` H2 storage to PostgreSQL by configuring
   `KC_DB=postgres` and database connection environment variables.
5. **TLS Ingress & Certificates:**
   Enable `edge.enabled: true` and set `edge.issuer` to a production cert-manager
   `ClusterIssuer` for automated Let's Encrypt TLS certificates.
