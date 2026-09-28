---
id: skill-service-meshes-when-to-use-which-c2e5c49ab7
purpose: service meshes when to use which
source: src/vibey_tools/skills/plugins/network-engineering/skills/network-modern-stack/SKILL.md
requires: ["skill-zero-trust-networking-in-production-dbd7f416f3"]
links: ["skill-network-observability-0d261d5e05"]
---

## Service meshes: when to use which

**Istio** (Google/IBM/Lyft): most feature-rich. Envoy proxies as sidecars, istiod as control plane. Newer Ambient Mesh eliminates per-pod sidecars using node-level ztunnels (L4) and optional waypoint proxies (L7), reducing resource overhead by up to 92%. The Istio add-on for AKS is GA (revisions asm-1-25 through asm-1-28).

**Linkerd** (Buoyant, CNCF graduated): Rust-based proxy consuming only ~10MB RAM per instance — roughly 8× more efficient than Istio's Envoy. Trades feature breadth for operational simplicity. Enables mTLS by default with zero configuration.

**Cilium Service Mesh**: use if already using Cilium CNI. No additional infrastructure. L4 mTLS via ztunnel, L7 via waypoint proxies. Hubble observability included.

**Decision rule**: use Cilium if already on Cilium CNI; use Linkerd for lowest overhead with minimal features; use Istio for maximum features and multi-cluster support.
