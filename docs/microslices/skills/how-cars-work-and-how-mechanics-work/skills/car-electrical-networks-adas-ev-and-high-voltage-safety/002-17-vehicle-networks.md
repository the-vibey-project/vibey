---
id: skill-17-vehicle-networks-c434e11b4c
purpose: 17 vehicle networks
source: src/vibey_tools/skills/plugins/how-cars-work-and-how-mechanics-work/skills/car-electrical-networks-adas-ev-and-high-voltage-safety/SKILL.md
requires: ["skill-16-the-12v-system-f980c18879"]
links: ["skill-18-adas-adaed10b9f"]
---

## §17. ⚠️ Vehicle Networks

**⚠️ A modern car is a distributed computer network on wheels, with dozens of ECUs.**
```
⚠️ CAN  differential pair (CAN-H / CAN-L), ⚠️ noise-immune, message-based
   with priority arbitration. ⚠️ ~120Ω terminating resistors at each
   end — measuring ~60Ω across the pair is the classic quick check
LIN  cheap single-wire subnet for slow things (mirrors, seats)
FlexRay · MOST · ⚠️ AUTOMOTIVE ETHERNET for cameras and high bandwidth
⚠️ GATEWAY MODULE  segregates networks — and in newer vehicles
   ⚠️ SECURE GATEWAY authentication is required for a scan tool to
   perform WRITE operations. ⚠️ This is precisely the §30.1 fight
```
**⚠️ Network fault symptoms are distinctive**: ⚠️ **a shorted CAN line takes out MANY
unrelated systems at once and produces a storm of communication codes** — **so when
everything fails simultaneously, suspect the network or a ground (§16), not each system.**
**⚠️ Module programming and coding**: ⚠️ **many replacement parts are inert until programmed
to the vehicle, and some are VIN-locked** — **which is the parts-pairing issue in §30.1 → `car-reference`.**

---
