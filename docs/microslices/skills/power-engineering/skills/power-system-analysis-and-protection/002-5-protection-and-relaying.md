---
id: skill-5-protection-and-relaying-03fa27ac86
purpose: 5 protection and relaying
source: src/vibey_tools/skills/plugins/power-engineering/skills/power-system-analysis-and-protection/SKILL.md
requires: ["skill-4-power-system-analysis-e9d8115bb5"]
links: []
---

## §5. Protection and Relaying

**⚠️ The fastest and highest-stakes software in the power system.**

**The requirements are in tension**: **speed** (limit damage, preserve stability),
**selectivity** (⚠️ **trip only the faulted element — coordination**), **sensitivity**
(detect every real fault), **and security** (⚠️ **don't trip for anything else**).
**⚠️ Dependability and security trade against each other directly, and the choice is a
deliberate engineering decision, not a default.**

**Relay types by ANSI device number**:
```
50  instantaneous overcurrent      51  time overcurrent    ⚠️ inverse-time curves
27  undervoltage                   59  overvoltage
81  under/over frequency           ⚠️ 81R rate-of-change (RoCoF) — see §8
87  differential  ⚠️ compares current in vs out — the gold standard for transformers,
                  buses and generators; inherently selective
21  distance (impedance)  ⚠️ the transmission workhorse; zones of reach
25  synchronism check     67  directional overcurrent   79  reclosing
```
**⚠️ Coordination** means the device nearest the fault operates first, with upstream
devices delayed enough to let it. **Time-current curves must not cross**, and
**coordination studies are redone whenever the system changes.**

> **⚠️ GOTCHA — protection assumes large, predictable fault current from synchronous
> machines, and inverters violate that assumption.** ⚠️ **An inverter typically limits
> fault current to roughly 1.1–2× rated** — because the semiconductors cannot survive
> more — **whereas a synchronous generator delivers many times rated current.**
> **Consequences**: overcurrent relays may not see the fault at all; **directional
> elements can misoperate because inverter fault current has a controlled, software-defined
> phase angle rather than a physical one**; and **fault type classification becomes
> unreliable.** ⚠️ **This is an active research problem, not a solved one.**
