---
id: skill-11-thread-zigbee-and-matter-fc51ad578a
purpose: 11 thread zigbee and matter
source: src/vibey_tools/skills/plugins/wireless-technologies-and-rf-engineering/skills/wireless-thread-matter-lora-cellular-uwb-and-choosing/SKILL.md
requires: []
links: ["skill-12-lora-and-lpwan-3b01307934"]
---

## §11. Thread, Zigbee and Matter

**⚠️ 802.15.4** is the shared PHY/MAC underneath — ⚠️ **low rate, low power, mesh-capable,
2.4 GHz (and sub-GHz variants).**
**⚠️ Zigbee** adds its own network and application layers, ⚠️ **and its historical problem
was profile fragmentation between vendors.**
**⚠️ Thread** is IPv6-native (6LoWPAN), ⚠️ **self-healing mesh, no single point of failure,
with Border Routers connecting to the wider IP network — and being IP-native is the
architectural advantage over Zigbee.**
**⚠️ MATTER** is an APPLICATION layer running over Thread, Wi-Fi or Ethernet — ⚠️ **it is
explicitly NOT a radio standard, which is the single most common misunderstanding about
it.**
> **⚠️ GOTCHA — Matter's promise was "everything works with everything," and the honest
> assessment is that it has been slower and messier than promised.** ⚠️ **Feature coverage
> lags device categories, vendor implementations differ, and multi-admin sharing has been
> awkward.** **⚠️ It is real and improving; treat maturity claims by device category rather
> than as a blanket.**

**⚠️ Mesh routing realities**: ⚠️ **battery devices are usually END DEVICES that do not
route, so a mesh only heals if enough mains-powered routers exist — a mesh of battery
sensors is not a mesh.**

---
