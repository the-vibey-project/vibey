---
id: skill-chaos-engineering-for-networks-7918e2f652
purpose: chaos engineering for networks
source: src/vibey_tools/skills/plugins/network-engineering/skills/network-modern-stack/SKILL.md
requires: ["skill-network-observability-0d261d5e05"]
links: ["skill-python-network-automation-379d08f99d"]
---

## Chaos engineering for networks

**Steady-state hypothesis**: define what "normal" looks like before injecting failures. Abort criteria: stop experiment if specific conditions are breached. Blast radius limiting: start with a small subset of traffic or pods.

**Chaos Mesh** (CNCF incubating): Kubernetes-native network chaos via CRDs. Can inject latency, packet loss, network partitions, bandwidth throttling.

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: payment-latency-test
spec:
  action: delay
  mode: one
  selector:
    namespaces: [payments]
    labelSelectors:
      app: payment-service
  delay:
    latency: "100ms"
    correlation: "25"
    jitter: "10ms"
  duration: "10m"
```

Linux `tc/netem` is the kernel-level foundation for network emulation. The key insight from Google's SRE practice: chaos experiments must be grounded in SLO preservation, not just recovery testing.
