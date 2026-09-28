---
id: skill-load-balancing-decision-matrix-75537f2ba4
purpose: load balancing decision matrix
source: src/vibey_tools/skills/plugins/software-architecture/skills/architecture-patterns/SKILL.md
requires: ["skill-azure-api-management-apim-8ef604f319"]
links: ["skill-catalog-azure-architecture-center-791795e9f3"]
---

## Load Balancing Decision Matrix

| Service | Layer | Scope | Use When |
|---|---|---|---|
| **Azure Load Balancer** | L4 | Regional | VMs/VMSS |
| **Application Gateway v2** | L7 | Regional | WAF, TLS termination, URL/path routing, cookie affinity; AKS ingress via AGIC |
| **Azure Front Door** | L7 + CDN | Global | HTTP(S) with CDN, WAF, geo-routing, caching — **now the unified Azure CDN/edge platform** |
| **Traffic Manager** | DNS | Global | DNS-based routing (performance/priority/weighted/geographic) |

**CDN retirements:**
- **Azure CDN Standard from Microsoft (classic) retires September 30, 2027**
- **Azure Front Door (classic) retires March 31, 2027**
- Classic profiles already blocked new creation and managed certs as of August 15, 2025
- Migrate using the zero-downtime migration tool

---

# PART 6: RESILIENCE PATTERNS
