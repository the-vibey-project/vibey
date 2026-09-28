---
id: skill-network-devices-roles-and-layers-e7d53f5d8a
purpose: network devices roles and layers
source: src/vibey_tools/skills/plugins/network-engineering/skills/network-fundamentals/SKILL.md
requires: ["skill-layers-5-7-tls-http-dns-d019076848"]
links: ["skill-vpns-site-to-site-vs-client-5b81299002"]
---

## Network devices: roles and layers

| Device | Layer | Function |
|--------|-------|----------|
| Hub | L1 | Dumb repeater — blasts to all ports. Extinct. |
| Switch | L2 | Reads MAC addresses, forwards to correct port only. |
| Router | L3 | Forwards packets between networks using IP, routing table. |
| Firewall | L3-L7 | Controls traffic based on rules; stateful inspection. |
| Load Balancer | L4/L7 | Distributes traffic across server pools. |
| Access Point | L1-L2 | Bridges Wi-Fi (802.11) to wired Ethernet (802.3). |

**Stateless firewalls** (packet filters): inspect each packet against rules (source/destination IP, ports, protocol). Fast but cannot distinguish legitimate responses from attacks. **Stateful firewalls** maintain a connection state table. Return traffic matching an established session is automatically permitted — only outbound rules needed. **NGFWs** add application awareness, deep packet inspection, TLS decryption, user identity.
