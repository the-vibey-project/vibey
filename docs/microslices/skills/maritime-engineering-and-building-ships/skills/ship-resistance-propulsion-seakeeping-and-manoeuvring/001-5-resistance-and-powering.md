---
id: skill-5-resistance-and-powering-1b0c42714d
purpose: 5 resistance and powering
source: src/vibey_tools/skills/plugins/maritime-engineering-and-building-ships/skills/ship-resistance-propulsion-seakeeping-and-manoeuvring/SKILL.md
requires: []
links: ["skill-6-propulsion-f42cf24295"]
---

## §5. Resistance and Powering

```
⚠️ THE COMPONENTS
   ⚠️ FRICTIONAL  ⚠️ dominant for slow full ships. Scales with
      WETTED SURFACE AREA and roughly with speed squared.
      ⚠️ Hull fouling attacks exactly this (§22)
   ⚠️ WAVE-MAKING  ⚠️ dominant at high speed and rises VERY steeply.
      ⚠️ The ship is generating waves and paying for them
   Form/viscous pressure · appendage · air resistance
⚠️ FROUDE NUMBER Fn = V/√(gL)  ⚠️ the governing similarity parameter
   ⚠️ HULL SPEED — a displacement hull approaches a wall where wave-
   making resistance rises near-vertically. ⚠️ THIS IS WHY LONGER
   SHIPS ARE FASTER: the limit scales with √L
⚠️ POWER SCALES ROUGHLY WITH SPEED CUBED  ⚠️ so a 10% speed cut can
   cut fuel by roughly 25-30%. ⚠️ THIS IS THE ENTIRE LOGIC OF SLOW
   STEAMING, and it's the cheapest decarbonization lever available (§24)
⚠️ MODEL TESTING and FROUDE'S METHOD  ⚠️ you cannot match Reynolds
   and Froude numbers simultaneously at model scale, so you scale
   the wave-making from the model and CALCULATE the friction
   separately. ⚠️ CFD now supplements but has not replaced tank testing
```
**⚠️ Margins**: ⚠️ **sea margin (weather and fouling) and engine margin are added on top of
calm-water trial power, and a ship that only makes its speed in flat calm on a clean hull
is a design failure.**

---
