---
id: skill-21-802-15-4-zigbee-thread-matter-ef24979a81
purpose: 21 802 15 4 zigbee thread matter
source: src/vibey_tools/skills/plugins/radio-technology-for-software-devs/skills/radio-protocol-stacks-wifi-ble-lpwan-and-gnss/SKILL.md
requires: ["skill-20-lpwan-and-cellular-iot-4a54bbb8fa"]
links: ["skill-22-gnss-2a72609cf0"]
---

## §21. 802.15.4, Zigbee, Thread, Matter

**⚠️ Keep the layers straight, because the marketing does not:**
```
802.15.4  ⚠️ the PHY/MAC. 2.4 GHz (and sub-GHz), DSSS, 250 kbps
Zigbee    full stack on top of 802.15.4. ⚠️ Older; vendor profile fragmentation
Thread    ⚠️ IPv6 (6LoWPAN) MESH on 802.15.4. Self-healing, no single
          coordinator, border router bridges to your LAN
Matter    ⚠️ APPLICATION layer. Runs over Thread, Wi-Fi, or Ethernet.
          ⚠️ NOT a radio — this is the single most common confusion
```
**⚠️ Mesh networking is genuinely useful and genuinely costly**: **self-healing and
extended coverage, at the price of routing overhead, latency that grows with hop count,
and routers that cannot sleep.** ⚠️ **In a mesh, only leaf/end devices get long battery
life.**

---
