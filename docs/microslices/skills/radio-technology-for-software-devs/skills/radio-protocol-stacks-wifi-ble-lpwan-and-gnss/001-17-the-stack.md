---
id: skill-17-the-stack-f8c2a6f061
purpose: 17 the stack
source: src/vibey_tools/skills/plugins/radio-technology-for-software-devs/skills/radio-protocol-stacks-wifi-ble-lpwan-and-gnss/SKILL.md
requires: []
links: ["skill-18-wi-fi-802-11-7b131e45bf"]
---

## §17. The Stack

**⚠️ Know which layer your problem is at, because the tools are completely different.**
```
PHY   ⚠️ modulation, coding, symbol timing. Tools: SDR, spectrum analyzer
MAC   ⚠️ channel access, addressing, ACK/retry. Tools: sniffer, protocol analyzer
NET+  routing, transport, application. Tools: normal software debugging
```
⚠️ **The most common mistake is trying to debug a PHY problem with application-layer
tools.** **If your packet loss is caused by a fading null (§6 → `radio-antennas-propagation-noise-and-modulation`), no amount of Wireshark
will show you why.**

---
