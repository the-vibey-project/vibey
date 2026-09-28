---
id: skill-4-networking-93a6cbf897
purpose: 4 networking
source: src/vibey_tools/skills/plugins/it-infrastructure-governance/skills/itgov-infrastructure-layers-compute-storage-and-networking/SKILL.md
requires: ["skill-3-storage-6c9137c57a"]
links: []
---

## §4. Networking

**Layers and segmentation**: **VLANs**, **subnets**, **routing**, ⚠️ **microsegmentation
— and the point of segmentation is blast radius: it limits lateral movement after an
initial compromise, which is the assumption you should be designing to.**
**Firewalls** (stateful, NGFW), **load balancers**, **proxies**, **NAT**, **VPN**
(⚠️ **site-to-site and remote access, and remote-access VPN is progressively being
displaced by zero-trust network access, which authenticates per-application rather than
granting network presence**).
**⚠️ DNS and DHCP are load-bearing and under-appreciated** — ⚠️ **a large share of "the
network is down" incidents are DNS**, and **in a Windows environment AD depends on DNS
absolutely** (§5 → `itgov-directory-authentication-authorization-and-privileged-access`).
**WAN**: MPLS, SD-WAN, internet breakout. **NTP** — ⚠️ **time skew breaks Kerberos, logging
correlation, and certificate validation, and it is the cause of a surprising number of
authentication failures** (§6 → `itgov-directory-authentication-authorization-and-privileged-access`).
