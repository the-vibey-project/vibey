---
id: skill-data-center-networking-spine-leaf-0f660a8c73
purpose: data center networking spine leaf
source: src/vibey_tools/skills/plugins/network-engineering/skills/network-fundamentals/SKILL.md
requires: ["skill-vpns-site-to-site-vs-client-5b81299002"]
links: ["skill-cloud-networking-fundamentals-95561870b7"]
---

## Data center networking: spine-leaf

Traditional three-tier networks (core/distribution/access) used STP to prevent loops by blocking redundant links — wasted bandwidth and caused 30-50 second convergence delays.

**Spine-leaf (Clos) topology**: every leaf switch connects to every spine switch. Any server-to-server communication traverses exactly 3 hops (leaf → spine → leaf). ECMP load-balances across all spine links simultaneously — no blocked paths. Adding capacity is horizontal: more spines increase bisection bandwidth; more leaves add server ports. Layer 3 routing (typically eBGP) replaces STP entirely.

East-west traffic (server-to-server) now accounts for 70-80%+ of data center traffic, driven by microservices and distributed storage — the primary reason spine-leaf won.
