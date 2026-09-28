---
id: skill-network-observability-0d261d5e05
purpose: network observability
source: src/vibey_tools/skills/plugins/network-engineering/skills/network-modern-stack/SKILL.md
requires: ["skill-service-meshes-when-to-use-which-c2e5c49ab7"]
links: ["skill-chaos-engineering-for-networks-7918e2f652"]
---

## Network observability

**Monitoring** asks "is it working?" **Observability** asks "why is it behaving this way?" In distributed systems, the difference is existential.

### Network SLO targets

| Tier | Availability SLO | Downtime/month |
|------|-----------------|----------------|
| Ultra-critical (payments) | 99.99% | 4.4 minutes |
| Tier-1 services | 99.9% | 43.8 minutes |
| Important, non-critical | 99.5% | 3.6 hours |

Key SLIs: packet loss rate, RTT at p50/p95/p99, DNS resolution time, connection establishment time. Latency SLOs: p95 < 200ms and p99 < 500ms for critical paths.

**Multi-burn-rate alerting** is the gold standard:
- Fast burn (2% budget consumed in 1 hour): P0
- Medium burn (5% in 6 hours): P1
- Slow burn (10% in 3 days): P2

When budget is exhausted: feature freeze.

### Observability stack for AKS

**ACNS (Advanced Container Networking Services)**: enterprise-grade network observability for both Cilium and non-Cilium clusters. Includes container network metrics, network logs (source/destination IPs, ports, protocols, flow direction), and pre-configured Azure Managed Grafana dashboards for DNS, pod flows, drops, and L7 traffic.

**Hubble** (automatically enabled with ACNS on Cilium clusters):
- `hubble observe --namespace payments` — real-time flow visibility
- `hubble observe --verdict DROPPED` — see all dropped packets and why
- DNS latency metrics per service

**Retina** (retina.sh): open-source eBPF-based observability, CNI-agnostic.

**OpenTelemetry**: vendor-neutral APIs and SDKs for traces, metrics, and logs. OTel Collector acts as telemetry pipeline (receivers, processors, exporters). OTLP over gRPC (port 4317) or HTTP (port 4318). W3C TraceContext headers for distributed trace propagation.

**Cardinality explosion warning**: in cloud-native environments, every unique combination of metric labels creates a separate time series. 20,000 metrics in a monolith can become 800 million in microservices. Never use unbounded values (user IDs, request IDs) as metric labels.
