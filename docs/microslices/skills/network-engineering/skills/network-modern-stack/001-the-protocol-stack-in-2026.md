---
id: skill-the-protocol-stack-in-2026-301e97ecd3
purpose: the protocol stack in 2026
source: src/vibey_tools/skills/plugins/network-engineering/skills/network-modern-stack/SKILL.md
requires: []
links: ["skill-spine-leaf-dominance-and-east-west-traffic-4fa9b06328"]
---

## The protocol stack in 2026

The OSI model remains a pedagogical framework, but production networking has evolved significantly. Key shifts:

**BGP as universal control plane**: not just for inter-domain routing, but for data center fabrics (eBGP underlay), EVPN overlays (MP-BGP), and segment routing advertisement. RPKI adoption crossed 50% of IPv4 routes — nearly all Tier-1 transit providers now reject RPKI-invalid prefixes. BGPsec remains largely experimental; the industry focused on RPKI/ROV and ASPA objects for path security.

**OSPF v3** (RFC 5340) serves as the workhorse underlay routing protocol in spine-leaf fabrics, providing ECMP paths between VTEPs.

**MPLS → SR-MPLS → SRv6 trajectory**: SR-MPLS eliminates the complexity of RSVP-TE and LDP signaling. SRv6 (Segment Routing over IPv6) is the next wave, driven by 5G network slicing. Microsoft Azure's Fairwater data center uses SRv6 for what it describes as the largest AI backend network in the world. Bell Canada, Alibaba, and Rakuten have all committed to SRv6 migrations.
