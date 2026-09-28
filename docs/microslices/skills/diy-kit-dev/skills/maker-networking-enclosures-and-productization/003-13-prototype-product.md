---
id: skill-13-prototype-product-f9661d85a5
purpose: 13 prototype product
source: src/vibey_tools/skills/plugins/diy-kit-dev/skills/maker-networking-enclosures-and-productization/SKILL.md
requires: ["skill-12-enclosures-and-fabrication-fe58655272"]
links: ["skill-14-buying-and-sourcing-666f790fc9"]
---

## §13. Prototype → Product

**[DURABLE] Be honest about which you're doing**, because the gap is enormous and mostly
invisible from the prototype side.

**The reliability layer a permanent installation needs:**
- **⚠️ Watchdog timer.** The device must recover from a hang without you visiting it.
- **Recovery from power loss** — resume state, don't require a button press.
- **Brownout detection** and sane behaviour on marginal power.
- **OTA updates.** ⚠️ **Firmware you can't update is firmware you'll have to physically
  retrieve.**
- **Failsafes** — what happens when Wi-Fi is down, the sensor is disconnected, or the
  server is unreachable? **Default to safe, not to last-known.**
- **Observability** — heartbeat, uptime, error counters, firmware version.
- **Thermal margin** and **conformal coating** for damp environments.

**Custom PCBs** — **KiCad** (free, excellent, now the default) or EasyEDA; **JLCPCB,
PCBWay, OSH Park, Aisler** for fabrication. ⚠️ **Five boards for ~$5 plus shipping is
genuinely accessible**, and **assembly services (JLCPCB's) will place parts for you**,
which changes what's feasible for a small run. **Expect two or three revisions** — order
the cheap prototypes early.

**Going to volume** — the things that surprise software people: **certification** (FCC/CE
for anything with a radio — ⚠️ **using a pre-certified module rather than a bare chip is
the single biggest cost saver**, §3.3 → `maker-boards-and-platforms`), **safety certification** for mains,
**RoHS/REACH/WEEE**, **⚠️ the EU Cyber Resilience Act** which now imposes security
obligations on connected products, **component lifecycle and second sources**,
**manufacturing test fixtures**, **support and returns**, and **the CM4/CM5 or a
module-based design** as the route to a Pi-based product.

**⚠️ And the honest warning: hardware margins are thin, iteration is slow and expensive,
and inventory is real money sitting in a box.** A great prototype is not a business.

---
