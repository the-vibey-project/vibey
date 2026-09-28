---
id: skill-7-wi-fi-in-practice-888c8e8ed9
purpose: 7 wi fi in practice
source: src/vibey_tools/skills/plugins/wireless-technologies-and-rf-engineering/skills/wireless-wifi-bluetooth-ble-nfc-and-rfid/SKILL.md
requires: ["skill-6-wi-fi-557f3a6933"]
links: ["skill-8-bluetooth-6c026af017"]
---

## §7. Wi-Fi in Practice

**⚠️ Design for the WORST client, not the best** — ⚠️ **a network engineered around a
laptop's radio will fail for a battery-powered sensor with a chip antenna.**
**⚠️ Site survey**: ⚠️ **predictive modelling, then passive and active survey, then
post-deployment validation — ⚠️ and validate with the actual client devices, because
different radios see different coverage.**
**⚠️ Coverage versus CAPACITY** is the design distinction people miss: ⚠️ **in dense
deployments you deliberately LOWER AP power and use narrower channels to create smaller
cells, because more APs at lower power beats fewer at high power.**
**⚠️ The recurring real-world faults**: ⚠️ **co-channel interference from too much power,
hidden nodes, sticky clients, DFS radar events dropping a channel, 2.4 GHz congestion, and
mounting APs above ceiling tiles or in metal enclosures.**
> **⚠️ GOTCHA — "more signal" is usually the wrong fix.** ⚠️ **A client that hears the AP
> fine but whose weak transmitter cannot be heard back has an ASYMMETRIC link, and turning
> AP power up makes it worse by extending the cell without extending the return path.**

---
