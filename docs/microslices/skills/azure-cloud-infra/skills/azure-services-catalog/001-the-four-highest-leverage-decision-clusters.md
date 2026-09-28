---
id: skill-the-four-highest-leverage-decision-clusters-454da6b97d
purpose: the four highest leverage decision clusters
source: src/vibey_tools/skills/plugins/azure-cloud-infra/skills/azure-services-catalog/SKILL.md
requires: []
links: ["skill-storage-redundancy-decision-matrix-a79219fb84"]
---

## The Four Highest-Leverage Decision Clusters

### 1. Compute — the Four-Way Decision

Microsoft's own Azure Architecture Center guidance establishes a clear preference order:

1. **Azure Container Apps (ACA)** — the modern default for container workloads. Built on Kubernetes + KEDA + Dapr but hides the control plane; scale-to-zero, event-driven scaling, no node-pool management. Key constraint: single top-level security boundary (the Container Apps environment) with unrestricted intra-environment communication and a shared Log Analytics workspace — if you need granular multi-workload isolation, use AKS or multiple ACA environments.
2. **AKS** — only when you need direct Kubernetes API access, custom service mesh, node-level control, or strict multi-workload isolation.
3. **Azure Functions (Flex Consumption)** — event-driven spiky workloads. Flex Consumption is now the recommended default (GA November 2024): scale from zero to 1,000 instances, no cold start with Always Ready, VNet integration, per-function scaling, configurable instance memory, Linux-only.
4. **App Service** — straightforward HTTP services and web apps. Deployment slots enable zero-downtime blue-green via slot swap.

**Anti-pattern to avoid:** every additional service is operational surface area and on-call burden — resist the Swiss Army knife.

#### Compute Details

**Virtual Machines — series selection:**
- B: burstable, dev/test
- D: general purpose
- E: memory-optimized (databases/caches)
- F: compute-optimized
- L: storage-optimized
- N: GPU
- H: HPC
- Use Availability Zones over Availability Sets for new production workloads; VMSS for scale
- Managed disks: Standard HDD (dev/backup) → Standard SSD (light production) → Premium SSD (production) → Ultra Disk/Premium SSD v2 (highest IOPS, databases)

**AKS networking models (decision is fixed at cluster creation):**
- **kubenet**: UDR-based, ~400-node limit, IP-efficient but limited
- **Azure CNI**: pods get VNet IPs, direct connectivity but IP-hungry
- **Azure CNI Overlay**: pods get IPs from a private CIDR, fixed /24 per node (~250 pods), scales to 5,000 nodes, comparable throughput to host networking — **now the recommended default**
- **Azure CNI Powered by Cilium**: eBPF dataplane, no kube-proxy, built-in network policy + observability, Linux-only
- **Identity**: AAD Pod Identity is deprecated — migrate to Workload Identity
- Standard/Premium tier supports up to 5,000 nodes

**ACA 2024–2025 additions:**
- Dynamic Sessions (GA): Hyper-V-isolated sandboxes for running untrusted/LLM-generated code
- Jobs: event-driven/scheduled/manual batch
- Serverless GPU (preview)
- Native Azure Functions hosting
- Free managed TLS certificates

**App Service tiers:** Free/Shared/Basic/Standard/Premium/Isolated
- App Service Environment (ASE) v3: only justified for network isolation/compliance at scale (max 200 instances vs 30 on Premium)

**Functions — Flex Consumption vs alternatives:**
- Flex Consumption: Linux-only, VNet, per-function scaling, ~zero cold starts with Always Ready
- Classic Consumption: caps at 10-minute execution, 200 instances, no VNet; cold starts 1–3s (.NET/JS/Python), 3–7s (Java)
- Premium (~$150–170/month minimum for EP1): eliminates cold starts via always-ready + prewarmed; worth it if not on Flex

---

### 2. Messaging — the Most-Confused Cluster

**The canonical distinction:** an **event** is a lightweight notification of a state change; a **message** is actionable data with delivery expectations.

| Service | Use For | Key Features |
|---|---|---|
| **Service Bus** | Transactional messages, orders, financial | FIFO via sessions, transactions, dead-lettering, duplicate detection, scheduled messages |
| **Event Hubs** | Telemetry streams, IoT, logs, clickstreams | Millions of events/sec, Kafka-compatible endpoint, Capture to Blob/ADLS |
| **Event Grid** | Reactive pub/sub ("react when X happens") | HTTP + MQTT, Event Grid Namespaces (MQTT broker, pull delivery); does NOT guarantee ordering |
| **Storage Queue** | Basic decoupling, cheap queuing | Simple REST-based; no sessions, transactions, or duplicate detection |

These are **complementary**. The canonical example: e-commerce uses Service Bus for orders, Event Hubs for telemetry, and Event Grid for shipment notifications.

---

### 3. Networking — Hub-Spoke vs Virtual WAN

**Hub-and-spoke:** full routing control, lower cost at small scale, supports specific third-party NVAs.

**Virtual WAN:** Microsoft-managed hub with native transitive routing and "routing intent" (auto-route all spoke traffic through Azure Firewall).

**Crossover point:** ~2–3 active regions or ~30 spokes, or when branch/SD-WAN connectivity at scale is needed.

**vWAN gotchas:**
- NAT Gateway is not supported in a vWAN hub
- Long-lived TCP flows through shared Azure Firewall drop on idle timeouts/instance recycling — workloads need bidirectional TCP keep-alives

**Private Endpoint vs Service Endpoint:**

| | Service Endpoint | Private Endpoint |
|---|---|---|
| Cost | Free | ~$7–8/month + data processing |
| On-premises access | No | Yes (via ExpressRoute/VPN) |
| DNS resolution | Public DNS | Private DNS (must configure) |
| Third-party support | No | Yes (Snowflake, etc.) |
| When required | Never (legacy) | SQL MI, ASE, AKS private API server, on-prem access |

---

### 4. Databases — the Three-Way Decision

**Azure SQL Database:** relational, DTU or vCore model, serverless tier (auto-pause), Hyperscale for large DBs, elastic pools for multi-tenant SaaS.

- **SQL Managed Instance:** near-full SQL Server compatibility; requires private endpoints (not service endpoints)

**Cosmos DB:** globally distributed NoSQL. The #1 performance lever is **partition key selection** — choose high cardinality, even RU/storage distribution, and a key that appears in query filters.
- Five consistency levels: Strong → Bounded Staleness → Session (default) → Consistent Prefix → Eventual
- Session consistency tokens must be passed explicitly between microservices or read-your-writes breaks
- Hierarchical partition keys and partition-level auto-failover (new 2025–2026) ease scaling
- **Warning:** "Scale failures are almost always design failures" — invest in partition-key design before launch; Cosmos DB is expensive and unforgiving when misused
- Reserve for genuine global-distribution or flexible-schema needs

**PostgreSQL:**
- **Flexible Server:** zone-redundant HA, burstable tiers, read replicas — use for migrating/modernizing existing PostgreSQL or Oracle apps
- **Cosmos DB for PostgreSQL (Citus):** for new cloud-native apps needing horizontal sharding
- Single Server is the deprecated path — do not use

---
