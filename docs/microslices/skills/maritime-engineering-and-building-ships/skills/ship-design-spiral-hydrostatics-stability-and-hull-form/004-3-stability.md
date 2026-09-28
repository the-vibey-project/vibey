---
id: skill-3-stability-8073d7f5ca
purpose: 3 stability
source: src/vibey_tools/skills/plugins/maritime-engineering-and-building-ships/skills/ship-design-spiral-hydrostatics-stability-and-hull-form/SKILL.md
requires: ["skill-2-buoyancy-and-hydrostatics-8e7d75234a"]
links: ["skill-4-hull-form-de5eeaa61e"]
---

## §3. ⚠️ Stability

> **⚠️ THE section. Floating and floating UPRIGHT are different problems, and ships that
> capsize usually had plenty of buoyancy.**
```
⚠️ THE MECHANISM  heel the ship → the underwater shape changes →
   ⚠️ B MOVES toward the immersed side → buoyancy up through B and
   weight down through G form a COUPLE
   ⚠️ If that couple RIGHTS the ship, it's stable. If it heels it
   further, it capsizes
⚠️ GM (metacentric height) = KM − KG  ⚠️ the initial stability measure
   ⚠️ GM POSITIVE → stable · ⚠️ GM NEGATIVE → loll or capsize
   ⚠️ GM TOO LARGE is also bad: ⚠️ a very stiff ship snaps back
   violently with a short roll period, which is uncomfortable,
   damages cargo and can break lashings (§7)
⚠️ GZ CURVE  righting lever versus heel angle. ⚠️ Initial GM is just
   the SLOPE AT THE ORIGIN — the full curve is what matters at
   large angles. ⚠️ Range of stability, angle of vanishing
   stability, area under the curve (= energy to capsize)
```
> **⚠️ GOTCHA — FREE SURFACE EFFECT is the one that catches people, because it reduces
> stability WITHOUT ADDING ANY WEIGHT.** ⚠️ **A partially filled tank lets liquid run to the
> low side as the ship heels, shifting weight in the worst possible direction and producing
> a VIRTUAL RISE IN G.** **⚠️ The effect scales with the CUBE of the tank's breadth, which
> is why tanks are subdivided longitudinally and why slack tanks are minimized.**
> **⚠️ The lethal versions: firefighting water accumulating on a car deck or in a
> superstructure; a partly flooded ro-ro deck (⚠️ a wide undivided deck is a free surface
> nightmare — the mechanism behind several major ferry disasters); and fish or grain
> shifting in bulk.**

**⚠️ Other stability killers**: ⚠️ **free liquid in cargo (liquefaction of ore concentrates
and nickel ore — a recurring cause of bulk carrier losses), ice accretion topside, water
on deck, high loading of containers, and lifting a weight with a crane (⚠️ the load acts at
the DERRICK HEAD the moment it lifts, instantly raising G).**
**⚠️ DAMAGE STABILITY** — ⚠️ **stability after flooding, calculated by the lost buoyancy or
added weight method, with SUBDIVISION and watertight bulkheads sized so the ship survives
defined damage** (§20 → `ship-class-flag-imo-safety-operations-and-losses`).
**⚠️ The inclining experiment** is how KG is determined in reality: ⚠️ **move a known weight
across the deck, measure the heel, and compute G.** **⚠️ It's done on completion because
the calculated lightship weight and centre are never exactly right.**

---
