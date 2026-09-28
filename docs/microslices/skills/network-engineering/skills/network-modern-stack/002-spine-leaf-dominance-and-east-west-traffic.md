---
id: skill-spine-leaf-dominance-and-east-west-traffic-4fa9b06328
purpose: spine leaf dominance and east west traffic
source: src/vibey_tools/skills/plugins/network-engineering/skills/network-modern-stack/SKILL.md
requires: ["skill-the-protocol-stack-in-2026-301e97ecd3"]
links: ["skill-ebpf-the-kernel-programmable-network-primitive-58e3bd207f"]
---

## Spine-leaf dominance and east-west traffic

East-west traffic now accounts for **70-80%+ of data center traffic**. Spine-leaf (Clos) topology replaced three-tier architectures because STP could not handle the east-west explosion driven by microservices and distributed storage.

In spine-leaf, every leaf connects to every spine: predictable two-hop latency, ECMP load balancing across all paths, horizontal scalability. Layer 3 routing (eBGP) replaces STP entirely.

**EVPN-VXLAN** is the standard overlay control plane:
- **VXLAN** (RFC 7348): MAC-in-UDP encapsulation. Uses 24-bit VNI supporting ~16 million logical segments (versus VLAN's 4,096 limit). UDP port 4789. VTEPs terminate tunnels at each leaf.
- **EVPN** (carried over MP-BGP): distributes MAC/IP reachability explicitly, eliminating flood-and-learn. Route Type 2 (MAC/IP Advertisement) is the workhorse. Spine switches serve as BGP route reflectors. Distributed anycast gateways eliminate traffic tromboning for east-west routing.
- **GENEVE** (RFC 8926): emerging as VXLAN's successor due to extensible TLV metadata. AWS Gateway Load Balancer already uses GENEVE. Cilium supports it as an alternative encapsulation.

**Symmetric IRB** is the production standard for inter-subnet routing in EVPN-VXLAN fabrics: each VTEP only configures VLANs for locally connected hosts, using a dedicated L3 VNI per tenant VRF. Both ingress and egress perform routing and bridging. Asymmetric IRB (every VTEP must host every VLAN's routing state) does not scale.
