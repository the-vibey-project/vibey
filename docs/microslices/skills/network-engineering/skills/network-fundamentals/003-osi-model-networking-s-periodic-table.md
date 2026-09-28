---
id: skill-osi-model-networking-s-periodic-table-5da2fd4257
purpose: osi model networking s periodic table
source: src/vibey_tools/skills/plugins/network-engineering/skills/network-fundamentals/SKILL.md
requires: ["skill-packets-the-unit-of-network-communication-1c3bd97085"]
links: ["skill-layer-1-2-physical-media-ethernet-mac-addresses-switches-arp-vlans-6927395337"]
---

## OSI model: networking's periodic table

The **OSI model** (ISO/IEC 7498, 1984) divides network communication into seven layers. It is a reference model — a conceptual framework, not what the Internet actually runs. Think of it as networking's periodic table: you do not use it to build molecules directly, but understanding it makes everything else make sense.

Data moves down the stack on the sending side. Each layer adds its own header (**encapsulation**). At the receiving side, each layer strips its header (**de-encapsulation**) and passes data up.

| Layer | Name | PDU | Real-world examples | Devices |
|-------|------|-----|---------------------|---------|
| 7 | Application | Data | HTTP, DNS, SMTP, SSH | — |
| 6 | Presentation | Data | TLS/SSL, data formatting | — |
| 5 | Session | Data | Session establishment | — |
| 4 | Transport | Segments/Datagrams | TCP, UDP, ports | — |
| 3 | Network | Packets | IP, ICMP, OSPF, BGP | Routers |
| 2 | Data Link | Frames | Ethernet, MAC addresses | Switches |
| 1 | Physical | Bits | Cables, Wi-Fi radio, voltages | Hubs |

Mnemonic: "**P**lease **D**o **N**ot **T**hrow **S**ausage **P**izza **A**way" (Physical → Application).

**The TCP/IP 4-layer model** is what the Internet actually runs. Developed by DARPA in the 1970s, it collapses OSI into four layers: Network Access (OSI 1-2), Internet (OSI 3), Transport (OSI 4), Application (OSI 5-7). Use OSI for troubleshooting ("which layer is the problem at?"); use TCP/IP for understanding the actual protocol stack.
