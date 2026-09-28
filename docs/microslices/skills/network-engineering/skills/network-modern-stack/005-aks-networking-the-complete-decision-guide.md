---
id: skill-aks-networking-the-complete-decision-guide-2067eddce0
purpose: aks networking the complete decision guide
source: src/vibey_tools/skills/plugins/network-engineering/skills/network-modern-stack/SKILL.md
requires: ["skill-cilium-the-production-kubernetes-networking-standard-e4f4f44786"]
links: ["skill-spiffe-spire-cryptographic-workload-identity-5df13ab509"]
---

## AKS networking: the complete decision guide

### CNI selection — the most consequential AKS decision

Microsoft now explicitly recommends **Azure CNI Overlay** for most scenarios. **Kubenet is retiring March 31, 2028**.

| Mode | Recommended | Pod IPs | Scale | Notes |
|------|-------------|---------|-------|-------|
| Azure CNI Overlay + Cilium | **Yes — production standard** | Separate CIDR, SNAT to node | 5,000 nodes, 250 pods/node | Conserves VNet IP space |
| Azure CNI Pod Subnet | Specific use case | Direct VNet IPs | 5,000 nodes | Use when external systems need pod IPs |
| Azure CNI Node Subnet | Legacy | VNet IPs, pre-allocated | 5,000 nodes | Being superseded |
| Kubenet | No — retiring | VNET IPs for nodes, private for pods | 400 nodes | Linux only, requires UDR management |

**The gold-standard production command**:
```bash
az aks create \
  --name myCluster --resource-group myRG --location eastus \
  --network-plugin azure --network-plugin-mode overlay \
  --pod-cidr 192.168.0.0/16 --network-dataplane cilium \
  --enable-acns --generate-ssh-keys
```

This deploys: Azure CNI Overlay + Cilium eBPF data plane + Advanced Container Networking Services for L7 policies, FQDN filtering, and Hubble observability.

### Network Policy engine comparison

**Azure Network Policy Manager (NPM)**: retiring. Windows support ends September 2026, Linux September 2028. iptables enforcement. Caps at 250 nodes/20,000 pods. No L7 or FQDN capabilities.

**Calico**: standard Kubernetes NetworkPolicy with better scalability. Cross-platform (Linux + Windows). AKS-managed Calico does not expose advanced features.

**Cilium** (Microsoft's recommendation): L3/L4/L7 enforcement, FQDN-based egress, DNS-aware policies, identity-based (not IP-based) enforcement, Hubble observability — all via eBPF with no iptables overhead.

Microsoft's official position: "We recommend using Cilium, which provides robust support for Kubernetes-native policies, extended features such as Layer 7 policy and FQDN filtering, and an eBPF-based dataplane that offers better performance, scalability, and security compared to iptables-based solutions."

### AKS DNS optimization

Default `ndots:5` causes excessive DNS queries for external names. **Optimize to `ndots:2` or `ndots:1`** for pods making frequent external DNS calls.

CoreDNS autoscaling formula: `replicas = max(ceil(cores/coresPerReplica), ceil(nodes/nodesPerReplica))` with minimum 2 replicas.

The **LocalDNS** feature deploys a per-node DNS proxy as a systemd service for lower latency and reduced conntrack usage.

### Ingress and egress

**Ingress — transitioning away from NGINX**: NGINX Ingress Controller is being retired (March 2026 announcement). Moving to **Gateway API** as the long-term standard, via the application routing add-on with Istio control plane. For new L7 ingress with WAF: **Application Gateway for Containers** supports Gateway API natively.

**Egress control options**:
- Default `loadBalancer`: creates public IP for SNAT. Simplest but least controlled.
- **Azure Firewall with UDR** (`userDefinedRouting`): FQDN filtering, compliance, full visibility.
- **NAT Gateway** (StandardV2): simpler IP management without FQDN filtering.

Required AKS egress destinations: `*.azmk8s.io:443`, `mcr.microsoft.com:443`, `management.azure.com:443`, `login.microsoftonline.com:443`.

**Load balancer decision tree**:
- HTTP/S global workloads → Azure Front Door (with Private Link to AKS internal LB)
- Regional L7 with WAF → Application Gateway
- Non-HTTP protocols → Azure Load Balancer Standard
- DNS-based multi-region → Traffic Manager
