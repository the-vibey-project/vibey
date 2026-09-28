---
id: skill-high-availability-b781d238b7
purpose: high availability
source: src/vibey_tools/skills/plugins/software-architecture/skills/architecture-patterns/SKILL.md
requires: ["skill-catalog-azure-architecture-center-791795e9f3"]
links: ["skill-three-pillars-one-05092001b0"]
---

## High Availability

**RTO/RPO drives architecture:**
- 99.9% → single-region zone-redundant
- 99.99% → multi-region

**Azure services:**
- **Availability Zones**: enable for all production resources
- **Cosmos DB multi-region**: multi-region writes with automatic conflict resolution
- **Azure SQL**: active geo-replication / failover groups
- **Redis Premium**: geo-replication
- **ACR**: geo-replication
- **Front Door / Traffic Manager**: multi-region routing

**Service Bus geo features (mutually exclusive on same namespace):**
- **Geo-Disaster Recovery**: metadata only
- **Geo-Replication** (recommended): metadata + message data; doesn't yet support large messages; preview on partitioned namespaces

**Critical sizing gotcha:** Redundancy is architecture; resiliency is behavior. Two zones behind a LB but Zone B sized for 50% load — Zone A fails, B is overwhelmed, the whole service degrades. **Size failover capacity for full load.**

**Chaos engineering:** Azure Chaos Studio.

---

# PART 7: CONFIGURATION & FEATURE FLAGS

- **Azure App Configuration**: feature flags + key-value store, **Sentinel key** for atomic multi-key refresh, geo-replication, Key Vault references
- App Service Application Settings/Connection Strings for simple cases

**Feature flag types:**
| Type | Purpose |
|---|---|
| Release toggles | Decouple deploy from release — the CI/CD enabler |
| Experiment toggles | A/B testing; progressive rollout (10%→50%→100%) |
| Ops toggles | Kill switches |
| Permission toggles | By user segment or tier |

Manage flag lifecycle/hygiene as technical debt. Third-party options: **LaunchDarkly** (Marketplace ISV), **Unleash** on AKS.

---

# PART 8: MULTI-TENANCY

**Isolation models:**

| Model | Isolation | Cost | Complexity |
|---|---|---|---|
| **Silo** | Isolated resources per tenant | Highest | Lowest |
| **Pool** | Shared resources, tenant-ID-keyed | Lowest | Highest |
| **Bridge (Hybrid)** | Shared for small, isolated for large/premium | Medium | Medium |

**Azure implementations:**
- **Azure SQL Elastic Pools**: pool-based with RLS or separate DBs
- **Cosmos DB**: partition key = tenant ID for pool; separate accounts/containers for silo
- **AKS**: namespace-per-tenant (soft isolation) vs node-pool-per-tenant (hard isolation)
- **APIM**: product/subscription per tenant with tenant-specific rate limits
- **Entra External ID / Azure AD B2C**: customer identity

**Critical gotcha:** Pool model with tenant-ID partition key in Cosmos DB risks a hot partition when one large tenant dominates — same irreversible partition-key trap, now with cross-tenant blast radius. Consider a composite key or bridge model for "whale" tenants.

---

# PART 9: OBSERVABILITY
