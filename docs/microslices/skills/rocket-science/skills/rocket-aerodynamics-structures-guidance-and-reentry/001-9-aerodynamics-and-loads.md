---
id: skill-9-aerodynamics-and-loads-02ebf59191
purpose: 9 aerodynamics and loads
source: src/vibey_tools/skills/plugins/rocket-science/skills/rocket-aerodynamics-structures-guidance-and-reentry/SKILL.md
requires: []
links: ["skill-10-structures-df4fb486f4"]
---

## §9. Aerodynamics and Loads

**Dynamic pressure** `q = ½ρv²` drives everything structural in the atmosphere.
**Aerodynamic normal force** `N = q·S·C_N·α`, and the resulting **bending moment**
`M ≈ q·α·(something)` — ⚠️ **the `q·α` product is the load metric launch vehicles are
actually flown to.** Guidance limits `q·α`, and **wind shear is dangerous precisely because
it creates α that the vehicle didn't command.**

**⚠️ Launch vehicles are aerodynamically unstable** — the centre of pressure is typically
ahead of the centre of mass, so any disturbance grows. **They are actively stabilized by
thrust vectoring**, which is why a control failure is immediately catastrophic rather than
gradually degrading. Fins (on some vehicles) move CP aft.

**Transonic** (M 0.8–1.2) brings shock formation, buffet, and a drag rise; **supersonic**
brings wave drag. **Base drag** behind the vehicle is significant and is one reason engine
plumes matter aerodynamically.

**Acoustic loads at liftoff: 160–180 dB OASPL.** ⚠️ **Water deluge isn't for cooling
primarily — it's acoustic suppression**, protecting the payload and vehicle from
reflected acoustic energy that could shake components apart.

---
