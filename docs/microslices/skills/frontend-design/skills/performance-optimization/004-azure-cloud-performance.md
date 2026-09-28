---
id: skill-azure-cloud-performance-ad6961f569
purpose: azure cloud performance
source: src/vibey_tools/skills/plugins/frontend-design/skills/performance-optimization/SKILL.md
requires: ["skill-next-js-typescript-performance-341b4ed557"]
links: ["skill-staged-recommendations-027f25a117"]
---

## Azure Cloud Performance

### Compute Tiers and Cold Starts

| Plan               | Cold start        | Notes                                                        |
|--------------------|-------------------|--------------------------------------------------------------|
| Consumption        | 2–7s (.NET isolated); >10s with heavy DI | Scales to zero after ~20 min; Microsoft now labels it "legacy" for new workloads |
| Flex Consumption   | Near-zero with "always ready" instances | Recommended for new serverless; VNet support                 |
| Premium            | ~200ms (pre-warmed) | Keeps ≥1 instance warm                                       |
| Dedicated/App Service | None (always-on) | No scale-to-zero; rule-based autoscale                       |

**Cheap cold-start mitigation (Consumption plan):** Azure Monitor availability tests pinging every ~5 min + smaller packages + `RUN_FROM_PACKAGE=1` + ReadyToRun compilation.

Linux Consumption plan retires Sept 30, 2028 — new Linux serverless should start on Flex Consumption.

### Container Apps + KEDA Scale-to-Zero

Define `minReplicas: 0` + scale rules. No charge at zero.

50+ KEDA scalers: HTTP concurrency, Service Bus queue length, Event Hubs, CPU/mem. HTTP concurrency recomputed every 15s; cooldown + stabilization windows configurable (e.g., 300s scale-down stabilization).

**Warning:** If ingress is disabled and you set neither `minReplicas≥1` nor a custom rule, the app scales to zero and cannot restart.

**ACA cost crossover:** Above ~40% average monthly utilization, ACA dedicated or AKS reserved becomes cheaper than ACA consumption.

### Messaging Service Selection

| Service      | Latency      | Throughput    | Best for                                           | Key characteristic                     |
|--------------|--------------|---------------|---------------------------------------------------|----------------------------------------|
| Event Grid   | Sub-second   | Moderate      | Reacting to Azure resource events, fan-out notifications | Lightweight routing; ~$0.60/M ops; events ≤1MB |
| Event Hubs   | Variable     | Millions/sec  | Telemetry, logs, clickstream, replay              | It is a log, not a queue               |
| Service Bus  | <5ms (Premium) | High       | Orders, payments, FIFO + sessions + transactions  | Enterprise broker; dead-lettering; duplicate detection |

**All three are at-least-once → consumers must be idempotent.**

**Common combination:** Event Grid reacts → Service Bus guarantees downstream processing; Event Hubs captures telemetry.

**Anti-pattern:** Using Service Bus for everything, or buying Event Hubs throughput units "for the future."

### Databases

| Service                        | Best for                                               | Watch out for                                   |
|--------------------------------|--------------------------------------------------------|-------------------------------------------------|
| PostgreSQL Flexible Server     | Lift-and-shift/modernization; read-heavy workloads with read replicas; burstable tier for dev | Async read replicas (single primary writes only) |
| Cosmos DB                      | Global distribution, guaranteed low latency, multi-region multi-master writes | Cost vs Table/Blob for simple cases; partition-key design is critical |
| Cosmos DB for PostgreSQL (Citus) | Distributed/sharded Postgres; high write scalability, multi-tenant, real-time analytics | Requires choosing a distribution column upfront |

Use burstable (B-series) tier for dev/variable Flexible Server load. Co-locate DB and app in the same region.

### Azure Cache for Redis

**Never use Basic tier in production** (single node, no SLA). Use Standard/Premium/Enterprise (at least C1).

**ConnectionMultiplexer rules (StackExchange.Redis):**
- Use a **single long-lived `ConnectionMultiplexer`** — creating one per request is the #1 Redis mistake
- Set `AbortOnConnectFail=false` and let it auto-reconnect
- Avoid `IsConnected` polling
- Consider separate multiplexers for large vs. small keys

**Pipelining:** Pipeline commands to maximize network throughput. Avoid expensive commands like `KEYS`.

**Clustering (Premium+):**

| Policy               | Characteristics                                            |
|----------------------|------------------------------------------------------------|
| OSS clustering       | Clients connect directly to nodes; best latency/throughput; needs client cluster support |
| Enterprise clustering | Single proxy endpoint; simpler; possible bottleneck       |

Throughput scales ~linearly with shards (e.g., P4 × 10 shards ≈ 2.5M RPS). Redis is single-threaded per node. On Premium, scale out (cluster) before scaling up.

**Note:** Azure Cache for Redis has a published retirement timeline — evaluate Azure Managed Redis for new builds.

### Application Insights Sampling

| Mode             | Behavior                                                      | Recommendation          |
|------------------|---------------------------------------------------------------|-------------------------|
| Adaptive (default) | Dynamically adjusts to `MaxTelemetryItemsPerSecond` target; keeps complete end-to-end transactions | Use in production       |
| Fixed-rate       | Constant %                                                    | Use when you need precise % |
| 100% (no sampling) | Full fidelity                                               | Development/debugging only |

Typical production sampling: 10–25%.

**Distributed tracing caveat:** If a busy server samples down to 0.1% while clients sample 100%, trace correlation breaks. Standardize sampling rates across services.

**Research context (Google Dapper):** Tracing at 100% imposed 1.5% throughput / 16% response time overhead; sampling at 0.01% cut to 0.20% latency / 0.06% throughput.

### VMSS Autoscale

**Use different scale-out and scale-in thresholds.** Microsoft explicitly warns that scaling out at >50% CPU and in at <50% causes oscillation ("flapping"). Thresholds must be "sufficiently different."

**Microsoft's recommended example:** Scale out at >70% CPU, scale in at <20%.

**Best practice ("scale out fast, scale in slow"):**
- Keep a 40–50 percentage-point gap between scale-out and scale-in thresholds
- Set cooldowns longer than instance startup time
- Use 10–15 minute smoothing windows

**Sanity check:** After a scale-out, per-instance CPU should still sit above the scale-in threshold. Example: 4 instances at 75% → adding one gives 75×4/5 = 60% — still above the scale-in threshold of 20%.

When multiple rules trigger, the highest resulting instance count wins.

### Azure Front Door / CDN

**Caching defaults:** If `Cache-Control` isn't present on the origin response, AFD randomly determines a cache duration of 1–3 days. Max: 366 days. AFD honors `private`/`no-cache`/`no-store`.

**Compression (Standard/Premium):** Compresses MIME-type responses between 1 KB and 8 MB. Brotli takes precedence over gzip when both are accepted. On cache-miss, compresses at the POP.

**WAF:** Custom rules evaluate before managed rule sets. DRS 2.0+ uses anomaly scoring (earlier versions block on first match). Policy changes propagate globally in under 20 minutes.

**Split TCP:** AFD terminates client TCP at the nearest POP; connection setup happens over 3–5 short roundtrips instead of 3–5 long roundtrips.

**Note:** AFD documents an in-progress migration from anycast to unicast routing — verify current behavior for latency-sensitive decisions.

### Cost-Performance Tiers

**B-series (burstable):**
- Accumulates CPU credits when below baseline; burns credits above baseline; throttles to baseline when credits depleted
- B1s baseline: ~10% (banks 6 credits/hr); B2s baseline: ~40%
- Credits lost on redeploy to new node; retained on same-node stop/start
- Good for: web servers, dev/test, small DBs with spiky load
- NOT for: sustained high CPU (throttles; D-series wins)

**Spot VMs:**
- Up to ~75–90% cheaper than pay-as-you-go
- 30-second eviction notice
- No high availability guarantees
- For: fault-tolerant, stateless, batch workloads

**Reserved Instances:**
- Up to ~72% discount for 1- or 3-year commitment
- "Use-it-or-lose-it" per hour; stopped VMs still consume reservation hours
- Not available for Spot

---
