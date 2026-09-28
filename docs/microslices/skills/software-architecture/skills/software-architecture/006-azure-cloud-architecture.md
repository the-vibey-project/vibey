---
id: skill-azure-cloud-architecture-6770e0d67a
purpose: azure cloud architecture
source: src/vibey_tools/skills/plugins/software-architecture/skills/software-architecture/SKILL.md
requires: ["skill-next-js-typescript-frontend-architecture-2a271c4136"]
links: ["skill-cqrs-and-event-sourcing-34cdbf3349"]
---

## Azure Cloud Architecture

### Landing Zones
- Use the Cloud Adoption Framework **enterprise-scale landing zone**
- Management-group hierarchy with governance/Policy inheriting down
- Separate **platform** subscriptions (management, connectivity, identity) and **application** landing-zone subscriptions
- Eight design areas: billing/Entra tenant, identity & access, management-group/subscription org, network topology & connectivity, security, management, governance, platform automation/DevOps
- Centralized Log Analytics + Defender for Cloud + Sentinel from day one

### Networking: Hub-and-Spoke
- Central hub VNet hosting Azure Firewall, VPN/ExpressRoute gateways, Bastion, and Private DNS zones
- Spokes peer to the hub — no direct spoke-to-spoke (route through hub via UDRs for centralized inspection)
- **Networking is the hardest thing to change after workloads deploy** — plan IP space up front
- Use Private Endpoints for PaaS
- **Application Gateway** (regional, WAF, integrates with Azure Firewall) vs **Front Door** (global L7, CDN, TLS termination, WAF, fast failover) — Front Door for global HTTP(S); Application Gateway for regional control + double inspection

### Multi-Region Active-Active
- **Front Door**: global choice; active-active or active-passive, automatic rerouting, integrated WAF/CDN
- **Traffic Manager**: DNS-based (simpler, slower failover due to DNS TTL caching) — useful as backup router if Front Door is unavailable
- **Cosmos DB multi-region writes**: `--enable-multiple-write-locations`, Session consistency by default, automatic conflict resolution
- Front multi-region APIM Premium by adding each regional gateway endpoint as a Front Door custom origin

### Service Mesh on AKS
- **Linkerd**: pragmatic default — Rust micro-proxy, mTLS on by default, 40–400% less latency overhead vs Istio
- **Istio**: when you need advanced traffic shaping, fine-grained policy, broad Envoy ecosystem, and can staff the complexity. AKS offers a managed Istio-based add-on
- CNCF data shows overall mesh adoption declining (from ~18% peak to ~8% by Q3 2025) — many teams don't need one

### IaC: Bicep vs Terraform
- **Bicep**: Azure-only, native day-0 support for new services, no state file, server-side ARM orchestration, preflight policy validation
- **Terraform**: multi-cloud, explicit state with drift detection, reusable versioned modules, consistent HCL across clouds
- Azure Verified Modules (AVM) increasingly used in ALZ-aligned deployments for both
- **Avoid mixing the two on the same resources** (state/drift conflicts)

### Identity and Data
- **Managed identities** (not connection strings/secrets) for service-to-service auth
- **Microsoft Entra External ID**: successor to Azure AD B2C for customer identity
- CQRS read models in Cosmos DB; event sourcing via Event Hubs; Synapse for analytics
- Key Vault with Private Endpoints for secrets/certs

---
