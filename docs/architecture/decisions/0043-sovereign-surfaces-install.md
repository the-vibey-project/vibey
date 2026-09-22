# 0043 — Sovereign operational surfaces deploy into the Kubernetes cluster with reconciled health

**Status:** proposed · **Date:** 2026-09-22 · **Cites:** sub-doctrine 8.b, ADR-0016, ADR-0025, ADR-0042 ·
**Related:** ADR-0002, ADR-0015, ADR-0018, ADR-0027, ADR-0037, ADR-0038 ·
**Evidence:** live-tested Garage SigV4, Kannel sendsms, Synapse homeserver init, Loki filesystem mode, Wazuh indexer; Helm chart `deploy/helm/vibey`

**Owes:** sub-doctrine 8.b mandates that self-hosted, sovereign surfaces are the default everywhere, and ADR-0042 established the operational protocols and declared-relay posture. This record decides the delivery and deployment mechanism: a self-hosted installation where every sovereign surface deploys into the Kubernetes cluster as its own pod(s), monitored by kopf-reconciled health (`VibeySurface` CRD), all ON by default, with the worker auto-wired via environment-variable config overlay.

## Context

ADR-0042 declared sovereign defaults across operational surfaces (tracker, docs, secrets, files, email, sms, messaging, configstore, cache, bus, blob, siem). However, defining Python ports and adapters alone leaves adopters with the burden of installing and wiring eighteen separate open-source services.

To deliver an autonomous software delivery platform that is truly sovereign and ready out-of-the-box, the Helm chart (`deploy/helm/vibey`) must package and orchestrate these surfaces directly into the cluster, establish their dependencies, monitor their readiness via Kubernetes custom resources, and wire the worker pods to communicate with them seamlessly.

## Decision

The Helm chart ships with all sovereign operational surfaces enabled by default (`surfaces.enabled: true`), deploying each into the cluster as its own Deployment(s) or StatefulSet with TCP socket health probes, persistent storage claims where needed, and an associated `VibeySurface` custom resource (`vibeysurfaces.vibey.dev/v1alpha1`) whose status is continuously reconciled by the vibey kopf operator.

### 1. Concrete Platform Selections and Rationale

- **Secrets: OpenBao over Bitwarden/Vaultwarden.** Bitwarden Secrets Manager has no standalone single-container self-hosted distribution. Vaultwarden enforces client-side cryptographic decrypts via AES (which is not in Python stdlib, preventing an honest dependency-free standard-library adapter). OpenBao (MPL-licensed community fork of Vault) provides a clean, static-token REST KV-v2 API readily driven via `urllib.request`. In dev mode, OpenBao boots with an in-memory or file backend and static root token.
- **SMS: Kannel over Fossify Server.** Fossify SMS remains the default client on physical mobile handsets, but does not provide an in-cluster server daemon. Kannel provides an established, multi-protocol SMS gateway speaking `GET /cgi-bin/sendsms`. The `cyrenity/kannel` image runs bearerbox and smsbox connected via localhost port 13001, holding STDIN open.
- **Blob: Garage over MinIO.** MinIO's community edition was folded into commercial AIStor behind commercial licensing gates. Garage (`dxflrs/garage`) provides a lightweight, pure Rust, AGPL-licensed S3-compatible object store verified live with AWS Signature Version 4 (SigV4) against SQLite metadata storage and local data directories.
- **Forge: Gitea.** Gitea provides verifiable, digest-pinned multi-arch OCI distribution images (`gitea/gitea`). Forgejo is supported as a 100% API-compatible, configuration-only image swap.
- **Tracker: Plane Work-Items API.** Plane backend exposes workspace-scoped work-items (`/api/v1/workspaces/{slug}/projects/{id}/work-items/`) where the item title field is `name`. Plane backend and frontend deploy alongside background beat/worker processes and an asynchronous schema migration job.

### 2. Full Surface Inventory

The surfaces deploy in three categories:

1. **Port-Backed Surfaces (Python Port + Adapter + Chart Deployment + VibeySurface CR):**
   - **Tracker:** Plane (`makeplane/plane-backend`, `makeplane/plane-frontend`)
   - **Docs:** BookStack (`linuxserver/bookstack` + `linuxserver/mariadb`)
   - **Secrets:** OpenBao (`openbao/openbao`)
   - **Files:** Nextcloud (`library/nextcloud`, SQLite backend)
   - **Email:** Postfix (`boky/postfix`, submission port 587)
   - **SMS:** Kannel (`cyrenity/kannel`, bearerbox + smsbox)
   - **Messaging:** Matrix Synapse (`matrixdotorg/synapse`)
   - **ConfigStore:** Infisical (`infisical/infisical`)
   - **Cache:** Redis (`library/redis:8-alpine`, shared across vibey, Plane, and Infisical)
   - **Bus:** RabbitMQ (`library/rabbitmq:4-management-alpine`, AMQP 5672 + Mgmt 15672)
   - **Blob:** Garage (`dxflrs/garage`, S3 API 3900)
   - **SIEM:** Wazuh (`wazuh/wazuh-manager`, `wazuh-indexer`, `wazuh-dashboard` v4.14.2)

2. **Chart-Managed Surfaces (Chart Deployment + VibeySurface CR, no vibey Port):**
   - **Forge:** Gitea (`gitea/gitea`)
   - **Registry:** OCI Distribution Registry (`library/registry`)
   - **Identity:** Keycloak (`keycloak/keycloak`, `start-dev`)
   - **Logs:** Loki (`grafana/loki`, filesystem store)
   - **Status:** Uptime Kuma (`louislam/uptime-kuma`)
   - **Monitoring:** Prometheus (`prom/prometheus`) + Grafana (`grafana/grafana`)

3. **Upstream-Managed Integrations (Chart renders namespaced CRs only, disabled by default):**
   - **Edge:** Ingress and cert-manager Certificates (`edge.enabled: false`)
   - **Backup:** Velero BackupStorageLocation and Schedule to Garage S3 (`backup.enabled: false`)

### 3. Wiring Model and In-Memory Fallbacks

Surfaces with chart-managed static credentials (files, email, sms, messaging, secrets, cache, bus, blob, siem) are fully wired into worker environment variables automatically via in-cluster DNS service names and Kubernetes Secrets.

For surfaces requiring interactive initial setup and operator-generated tokens (Plane user API token, BookStack system access token, Infisical machine token):
- Tokens are injected into the worker pod via `secretKeyRef` with `optional: true`.
- If the token key is empty or absent, the worker starts without crashing, and `vibey.bootstrap` falls back to the in-memory adapter until the operator provisions and pastes the token.

### 4. Health Reconciliation via VibeySurface CRD

The operator watches `VibeySurface` custom resources. Each `VibeySurface` declares `spec.components` listing the Deployment names backing the surface. The kopf operator periodically observes `availableReplicas` on those Deployments:
- If all components have `availableReplicas >= 1`, the surface condition `Ready` is `True` with reason `Available`.
- If any component is down, `Ready` is `False` with reason `Degraded`.
- If no components are declared, `Ready` is `Unknown` with reason `NoComponents`.

## Security Impact

All images run with restricted capabilities (`drop: [ALL]`). Probes use TCP socket checks rather than unauthenticated HTTP paths. Services that require root execution due to container construction (e.g. Garage, linuxserver images) declare explicit `runAsUser` and `fsGroup` overrides scoped strictly to their own pod templates, preserving the non-root chart-wide security context on the worker and operator.

## Migration

No existing worker or CLI configuration is invalidated. When running outside Kubernetes or with `surfaces.enabled: false`, vibey continues to use in-memory fallbacks or external services configured via `vibey.toml` or environment variables.
