---
id: skill-14-safety-41d60f128d
purpose: 14 safety
source: src/vibey_tools/skills/plugins/electrical-engineering/skills/ee-test-selection-safety-and-debugging/SKILL.md
requires: ["skill-13-datasheets-and-selection-1877b5a1af"]
links: ["skill-15-debugging-hardware-4fc0818311"]
---

## §14. Safety

> **⚠️ GOTCHA — it is current through the body that harms, not voltage, and the threshold
> is far lower than people assume.**
> ```
> ~1 mA      perception
> ~10 mA     ⚠️ "let-go" threshold — above this you may not be able to release the conductor
> ~30 mA     respiratory arrest risk
> ~100 mA    ⚠️ ventricular fibrillation — this is the lethal mechanism, and it is not a
>            large current
> ```
> **Dry skin is ~100 kΩ; wet or broken skin can be ~1 kΩ.** ⚠️ **At 1 kΩ, 120 V gives
> 120 mA. Mains kills, routinely, and the fatal current is small.**

**Mains work**: ⚠️ **if you are not confident, don't.** Use an **isolation transformer**
and **RCD/GFCI**, work one-handed where possible (⚠️ **keeps current out of the
heart-crossing path**), **never work alone on live mains**, and **verify de-energized with
a meter you have just tested on a known-live source.**

**⚠️ Capacitors store lethal energy after power is removed.** Mains-rated bulk caps and
flash/CRT circuits especially. **Discharge through a resistor and verify with a meter.**

**Batteries**: ⚠️ **Li-ion shorted delivers enormous current and can vent, ignite, or
explode.** Never puncture, never charge below 0 °C, and use protection circuitry.
**⚠️ Lead-acid produces hydrogen — no sparks.**

**Other**: **ESD** protection for components (wrist strap, mat) — ⚠️ **you can destroy or,
worse, *partially* damage a part without feeling the discharge, producing an
intermittent field failure**; **soldering** (⚠️ **lead and flux fumes — ventilate**); and
**eye protection when cutting leads.**

---
