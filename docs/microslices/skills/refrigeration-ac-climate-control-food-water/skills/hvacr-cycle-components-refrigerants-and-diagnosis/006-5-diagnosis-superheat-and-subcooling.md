---
id: skill-5-diagnosis-superheat-and-subcooling-d3c61b8593
purpose: 5 diagnosis superheat and subcooling
source: src/vibey_tools/skills/plugins/refrigeration-ac-climate-control-food-water/skills/hvacr-cycle-components-refrigerants-and-diagnosis/SKILL.md
requires: ["skill-4-charge-evacuation-and-leaks-3e9e5ac36a"]
links: ["skill-6-other-cooling-approaches-7918990085"]
---

## §5. ⚠️ Diagnosis: Superheat and Subcooling

> **⚠️ These two measurements are how you see inside a sealed system, and everything else
> is guessing.**
```
⚠️ SUPERHEAT = actual suction line temp − saturation temp at suction pressure
   ⚠️ Tells you about the EVAPORATOR and the charge/metering
   ⚠️ LOW superheat  → too much refrigerant reaching the evaporator →
      RISK OF LIQUID RETURN TO THE COMPRESSOR (the destructive failure)
   ⚠️ HIGH superheat → refrigerant boiling off too early → undercharge,
      restriction, or a starved evaporator

⚠️ SUBCOOLING = saturation temp at liquid pressure − actual liquid line temp
   ⚠️ Tells you about the CONDENSER and the charge
   ⚠️ LOW subcooling  → undercharge, or condenser not condensing fully
   ⚠️ HIGH subcooling → overcharge, or liquid backing up (restriction)

⚠️ WHICH ONE TO CHARGE BY
   ⚠️ FIXED ORIFICE / CAPILLARY → charge by SUPERHEAT
   ⚠️ TXV / EEV → charge by SUBCOOLING (⚠️ the valve controls superheat,
      so superheat tells you about the VALVE, not the charge)
```
**⚠️ Common patterns:**
```
⚠️ High superheat + low subcooling      → UNDERCHARGE or leak
⚠️ Low superheat + high subcooling      → OVERCHARGE
⚠️ High superheat + high subcooling     → RESTRICTION (metering device, drier)
⚠️ Low superheat + low subcooling       → metering device overfeeding, or
                                          weak compressor
⚠️ High head pressure                   → dirty condenser, overcharge,
                                          non-condensables, high ambient
⚠️ Iced evaporator                      → low airflow (⚠️ FIRST suspect —
   dirty filter or coil), low charge, or low ambient operation
```
> **⚠️ GOTCHA — most "low on refrigerant" calls are airflow problems.** ⚠️ **A refrigerant
> system is SEALED; it does not consume refrigerant.** **If it's low, there is a LEAK, and
> topping it up without finding the leak is both a temporary fix and, for larger systems,
> a compliance failure.** **⚠️ Before adding refrigerant: check the filter, the coil, the
> blower and the ductwork.**

---
