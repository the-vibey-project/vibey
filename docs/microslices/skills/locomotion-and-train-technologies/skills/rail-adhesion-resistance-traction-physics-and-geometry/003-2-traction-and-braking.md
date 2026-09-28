---
id: skill-2-traction-and-braking-6cc50082ed
purpose: 2 traction and braking
source: src/vibey_tools/skills/plugins/locomotion-and-train-technologies/skills/rail-adhesion-resistance-traction-physics-and-geometry/SKILL.md
requires: ["skill-1-adhesion-and-resistance-c0a0e6d6f5"]
links: ["skill-3-the-wheel-rail-interface-2b8fe97ba9"]
---

## §2. Traction and Braking

**⚠️ Tractive effort is limited by TWO ceilings and the binding one changes with speed:**
```
⚠️ ADHESION LIMIT   TE_max = adhesive weight × adhesion coefficient
   ⚠️ Dominates at LOW speed. More weight on driven axles = more pull
⚠️ POWER LIMIT      TE = Power / velocity
   ⚠️ Dominates at HIGH speed — TE falls hyperbolically as speed rises
```
⚠️ **This is why a locomotive's TE curve is flat at low speed then falls away, and why
"horsepower" and "pulling power" are different questions.**
**⚠️ Axle load and the number of driven axles matter enormously**: ⚠️ **a Co-Co locomotive
(six driven axles) outpulls a Bo-Bo (four) of the same power at low speed, because
adhesive weight is the limit there.**
**⚠️ Wheelslip control** — ⚠️ **modern AC drives detect incipient slip and modulate torque
per axle in milliseconds, which raised usable adhesion substantially over DC-era
equipment** (§8 → `rail-steam-diesel-electric-and-alternative-traction`).
**⚠️ Braking** (detailed in §19 → `rail-rolling-stock-braking-capacity-and-service-types`): **friction (tread, disc), dynamic (rheostatic and
regenerative), and ⚠️ non-adhesion brakes (magnetic track brake, eddy current) which do NOT
depend on wheel-rail adhesion and are therefore the fallback in low-adhesion conditions.**

---
