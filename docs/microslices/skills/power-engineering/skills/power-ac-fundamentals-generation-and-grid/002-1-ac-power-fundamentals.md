---
id: skill-1-ac-power-fundamentals-de6d548b4f
purpose: 1 ac power fundamentals
source: src/vibey_tools/skills/plugins/power-engineering/skills/power-ac-fundamentals-generation-and-grid/SKILL.md
requires: ["skill-0-routing-b206ad1044"]
links: ["skill-2-generation-368d484124"]
---

## §1. AC Power Fundamentals

### 1.1 Why AC won
**Transformers.** ⚠️ **You can change AC voltage almost losslessly, and you cannot easily
do that with DC.** Since `P_loss = I²R`, **transmitting at high voltage means low current
for the same power, and losses fall with the square of the current.** ⚠️ **This single
fact is why the grid exists in the form it does.**

**⚠️ HVDC is the modern exception** — better for very long distances, undersea cables, and
connecting asynchronous systems, because power electronics made the conversion practical.

### 1.2 ⚠️ Real, reactive, and apparent power — the concept software people get wrong
```
S = P + jQ            S apparent (VA) · P real (W) · Q reactive (VAr)
|S| = √(P² + Q²)
Power factor  PF = P/|S| = cos θ    ⚠️ θ is the angle between voltage and current
```
**Real power `P`** does work — heat, torque, light.
**⚠️ Reactive power `Q`** is energy sloshing back and forth between source and the
magnetic/electric fields of inductive and capacitive loads. **It does no net work over a
cycle — but it occupies current-carrying capacity, causes `I²R` losses, and is what holds
voltage up.**

> **⚠️ GOTCHA — "reactive power is wasted" is wrong and leads to bad engineering.**
> **The grid needs reactive power** to magnetize motors and transformers and to support
> voltage. ⚠️ **The real issue is *where* it's supplied from.** Reactive power doesn't
> transmit well over distance — it causes losses and voltage drop on the way. **So it's
> generated locally: capacitor banks, synchronous condensers, STATCOMs, and increasingly
> inverters (§8 → `power-inverters-storage-markets-and-datacenters`).** **Frequency is a system-wide quantity; voltage is a local one, and
> that asymmetry follows directly from this.**

**⚠️ Poor power factor costs money** — industrial customers are billed for it, because a
0.7 PF load draws ~43% more current than a unity-PF load for the same real power, and the
utility must build for the current.

### 1.3 Three-phase
**Three voltages 120° apart.** ⚠️ **Why it dominates**: constant instantaneous total power
(a single-phase supply pulsates at twice line frequency), **rotating magnetic field for
free** (which is why induction motors work), and **less conductor material for the same
power.**
```
Wye (Y):   V_line = √3 × V_phase,  I_line = I_phase   ⚠️ has a neutral
Delta (Δ): V_line = V_phase,  I_line = √3 × I_phase   ⚠️ no neutral
P_3φ = √3 × V_line × I_line × cos θ
```
**⚠️ In a balanced system the neutral current is zero** — the three phases cancel. **Under
imbalance it isn't, and harmonic currents (particularly triplen harmonics from
switch-mode power supplies) add rather than cancel in the neutral** — ⚠️ **which is why
datacenter and office neutrals can carry more current than the phases, and why undersized
neutrals overheat.**

**Symmetrical components (Fortescue, 1918)** — ⚠️ **decompose any unbalanced three-phase
set into positive, negative, and zero sequence components.** **This is the mathematical
foundation of fault analysis (§4.3 → `power-system-analysis-and-protection`) and protection (§5 → `power-system-analysis-and-protection`)**, and it turns an intractable
unbalanced problem into three balanced ones.

### 1.4 ⚠️ Frequency as the balance signal
**The grid stores essentially no energy.** Generation must match load instantaneously.
- **Load exceeds generation** → generators decelerate → **frequency falls.**
- **The kinetic energy in spinning masses buys you seconds** — this is **inertia** (§8 → `power-inverters-storage-markets-and-datacenters`).
- **`RoCoF` (rate of change of frequency)** is set by the imbalance divided by system
  inertia. ⚠️ **Less inertia means faster collapse from the same disturbance, which is
  the entire §8 → `power-inverters-storage-markets-and-datacenters` problem.**

**Frequency control hierarchy**:
```
Inertial response   ⚠️ instantaneous, physics, no control loop — spinning mass
Primary (governor)  seconds — droop control, arrests the fall
Secondary (AGC)     ⚠️ ~minutes — restores to 60/50 Hz and fixes interchange
Tertiary            economic redispatch (§10)
```
**⚠️ Droop** is deliberate: a generator's speed setpoint falls with output (typically
**4–5%**), so multiple machines **share load automatically without communicating.**
**It's a proportional controller implemented in physics**, and the reason a grid works at
all without central coordination in the first seconds.

### 1.5 Per-unit
**Normalize everything to a base**: `pu = actual/base`. ⚠️ **Why it's universal in power
engineering**: transformer turns ratios vanish, values across voltage levels become
directly comparable, and equipment impedances land in predictable ranges regardless of
size. **⚠️ If you write power system software and don't understand per-unit, every number
you handle will confuse you.**

---
