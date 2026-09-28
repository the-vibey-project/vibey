---
id: skill-3-transmission-and-distribution-c5981012e8
purpose: 3 transmission and distribution
source: src/vibey_tools/skills/plugins/power-engineering/skills/power-ac-fundamentals-generation-and-grid/SKILL.md
requires: ["skill-2-generation-368d484124"]
links: []
---

## §3. Transmission and Distribution

```
Generation (~15–25 kV) → step-up → TRANSMISSION (115–765 kV)
  → substation → SUBTRANSMISSION (34.5–138 kV) → DISTRIBUTION (4–35 kV)
    → service transformer → CUSTOMER (120/240 V, 480 V, ...)
```
**Transmission** is a meshed network (⚠️ **redundant paths — a single failure shouldn't
cause an outage; this is the `N−1` criterion**). **Distribution is usually radial** —
⚠️ **simple and cheap, and a fault upstream takes out everything downstream**, which is
why distribution automation and reconfiguration matter.

**Key equipment**: transformers (⚠️ **the long-lead-time bottleneck item — see §15.2 → `power-reference`**),
circuit breakers, **reclosers** (⚠️ **most distribution faults are temporary — a branch,
an animal — so reclosers trip and re-close automatically, which is why your lights blink
rather than going out**), switches, capacitor banks, voltage regulators, **and the
protective relays of §5 → `power-system-analysis-and-protection`**.

**⚠️ Line limits are not one number.** Thermal (conductor sag — ⚠️ **a sagging line
contacting vegetation is a documented blackout initiator**), voltage drop, and **stability
limits** — and **for long lines the stability limit binds well before the thermal limit.**
**Dynamic line rating** uses real weather to reclaim capacity that static ratings leave on
the table.
