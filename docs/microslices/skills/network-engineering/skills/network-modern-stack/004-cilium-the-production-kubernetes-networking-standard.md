---
id: skill-cilium-the-production-kubernetes-networking-standard-e4f4f44786
purpose: cilium the production kubernetes networking standard
source: src/vibey_tools/skills/plugins/network-engineering/skills/network-modern-stack/SKILL.md
requires: ["skill-ebpf-the-kernel-programmable-network-primitive-58e3bd207f"]
links: ["skill-aks-networking-the-complete-decision-guide-2067eddce0"]
---

## Cilium: the production Kubernetes networking standard

**Cilium** (CNCF graduated, acquired by Cisco via Isovalent) is eBPF-native Kubernetes networking, security, and observability — replacing kube-proxy entirely.

Key metrics:
- **72× CPU reduction** at Seznam.cz after replacing kube-proxy
- O(1) hash-based service routing versus iptables' O(n) linear rule matching
- Identity-based enforcement (not IP-based) that survives pod restarts

### What Cilium provides

**Networking**: pod-to-pod networking via eBPF, VXLAN or GENEVE encapsulation, native routing mode (no overlay) for BGP-integrated environments.

**kube-proxy replacement**: intercepts connections at socket level (the `connect()` syscall), eliminating per-packet NAT overhead and conntrack table contention. Result: dramatically lower CPU at scale.

**Network Policy**: L3/L4/L7 enforcement. FQDN-based egress filtering. DNS-aware policies. HTTP method/path filtering. L7 Kafka/gRPC policies with ACNS.

**Hubble observability**: flow-level visibility, identity-aware traffic logs, DNS latency metrics, pre-built Grafana dashboards — all without sidecars. Real-time `hubble observe` CLI and UI.

**Cilium Service Mesh**: sidecarless service mesh using ztunnels for L4 mTLS and optional waypoint proxies for L7. Dramatically lower overhead than Envoy-sidecar approaches.

### CiliumNetworkPolicy example

```yaml
apiVersion: cilium.io/v2
kind: CiliumNetworkPolicy
metadata:
  name: allow-payments-to-db
spec:
  endpointSelector:
    matchLabels:
      app: postgres
  ingress:
  - fromEndpoints:
    - matchLabels:
        app: payments-service
    toPorts:
    - ports:
      - port: "5432"
        protocol: TCP
```

FQDN-based egress (requires ACNS or Cilium Enterprise):
```yaml
spec:
  endpointSelector:
    matchLabels:
      app: backend
  egress:
  - toFQDNs:
    - matchName: "api.external-service.com"
    toPorts:
    - ports:
      - port: "443"
        protocol: TCP
```
