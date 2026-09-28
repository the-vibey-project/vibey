---
id: skill-zero-trust-networking-in-production-dbd7f416f3
purpose: zero trust networking in production
source: src/vibey_tools/skills/plugins/network-engineering/skills/network-modern-stack/SKILL.md
requires: ["skill-spiffe-spire-cryptographic-workload-identity-5df13ab509"]
links: ["skill-service-meshes-when-to-use-which-c2e5c49ab7"]
---

## Zero Trust networking in production

**BeyondCorp principles** (Google, 2011): connecting from a particular network must not determine accessible services; access is granted based on user and device context; all access must be authenticated, authorized, and encrypted.

**NIST SP 800-207** (2020) seven tenets:
1. All data sources and computing services are resources requiring authenticated access
2. All communication is secured regardless of location (no trusted network)
3. Access is per-session, not per-user
4. Access is dynamically determined by policy
5. The enterprise monitors and measures integrity of all assets
6. Authentication and authorization are dynamic and strictly enforced
7. Maximum information collected about current state of assets, infrastructure, and communications

**NIST SP 800-207A** (2023) extended this to cloud-native applications, explicitly recommending service meshes, SPIFFE identity, and sidecar proxies.

**CISA 2025 "Journey to Zero Trust Microsegmentation"**: recommends phased adoption with attribute-based (not IP-based) access rules.

### Default-deny network policy pattern

```yaml
# Start with default deny for all ingress and egress
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
---
# Then allow DNS (required for service discovery)
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
spec:
  podSelector: {}
  egress:
  - ports:
    - port: 53
      protocol: UDP
    - port: 53
      protocol: TCP
```

Layer incrementally: allow DNS first → add namespace isolation via namespaceSelector → add pod-level microsegmentation for specific service-to-service flows → add FQDN-based egress policies → add L7 HTTP method/path filtering with Cilium.

Use **Hubble** to observe actual traffic flows before writing restrictive policies.

### mTLS implementation comparison (latency overhead)

From academic benchmarking (arXiv:2411.02267):
- Istio sidecar: **166%** overhead
- Cilium: **99%** overhead
- Linkerd: **33%** overhead
- Istio Ambient: **8%** overhead

Sidecarless architectures show dramatic advantages. For AKS, Cilium mTLS (public preview) uses ztunnel + SPIRE with TLS 1.3 sessions for transparent pod-to-pod encryption.
