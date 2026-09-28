---
id: skill-7-protocols-e1cb2f0eac
purpose: 7 protocols
source: src/vibey_tools/skills/plugins/power-engineering/skills/power-scada-ems-and-protocols/SKILL.md
requires: ["skill-6-scada-ems-and-dms-4f5de13ad1"]
links: []
---

## §7. Protocols

| Protocol | Domain | ⚠️ Notes |
|---|---|---|
| **Modbus** | Ubiquitous, simple | ⚠️ **No security whatsoever. Assume it's plaintext and trusted-by-position** |
| **DNP3** | ⚠️ **North American SCADA standard** | Event-driven with timestamps and quality flags; **Secure Authentication exists — use it** |
| **IEC 60870-5-101/104** | European SCADA equivalent | 104 is the TCP/IP variant |
| **IEC 61850** | ⚠️ **Substation automation, and the modern one** | Object model + SCL config; **GOOSE** and **Sampled Values** |
| **IEC 61970/61968 CIM** | ⚠️ **Network model exchange** | The semantic model behind EMS/DMS interoperability |
| **IEEE C37.118 / IEEE 2664** | Synchrophasors | PMU streaming (§4.2 → `power-system-analysis-and-protection`) |
| **OpenADR, IEEE 2030.5** | Demand response, DER | Utility-to-customer |
| **OPC UA** | Industrial | Increasingly a bridge layer |

**⚠️ IEC 61850 GOOSE deserves specific attention**: it's a **multicast layer-2 publish/
subscribe message for protection signalling with a ~4 ms delivery requirement.** ⚠️ **It
retransmits with decreasing intervals to survive loss, and it bypasses the IP stack
entirely — so ordinary network engineering intuitions do not apply.** **Sampled Values
(SV)** streams digitized CT/VT waveforms at high rate, ⚠️ **which turns substation
protection into a hard-real-time networking problem and makes PTP time synchronization
safety-relevant.**

> **⚠️ GOTCHA — nearly all of these protocols were designed for physically isolated
> networks and have no meaningful authentication by default.** **Security in this domain
> is overwhelmingly perimeter- and segmentation-based** (§11.2 → `power-inverters-storage-markets-and-datacenters`). ⚠️ **Never assume a
> protocol validates who sent a command.**
