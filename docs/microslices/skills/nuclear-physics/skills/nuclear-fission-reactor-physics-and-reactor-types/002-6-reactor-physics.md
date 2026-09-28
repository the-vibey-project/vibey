---
id: skill-6-reactor-physics-526157a5af
purpose: 6 reactor physics
source: src/vibey_tools/skills/plugins/nuclear-physics/skills/nuclear-fission-reactor-physics-and-reactor-types/SKILL.md
requires: ["skill-5-fission-physics-89ff8cf537"]
links: ["skill-7-reactor-types-70582a2380"]
---

## §6. Reactor Physics

### 6.1 Criticality
**⚠️ The multiplication factor `k` is the whole game:**
```
k = neutrons in one generation / neutrons in the previous
k < 1  subcritical      k = 1  ⚠️ CRITICAL — steady power      k > 1  supercritical
Reactivity ρ = (k−1)/k
```
**⚠️ "Critical" means steady-state operation.** **It is the normal, desired condition of a
running reactor** — and its everyday connotation of danger is precisely wrong (§15 → `nuclear-reference`).

**Six-factor formula** `k = η·f·p·ε·P_FNL·P_TNL` — reproduction factor, thermal
utilization, resonance escape probability, fast fission factor, and the two non-leakage
probabilities. ⚠️ **Leakage is why geometry and size matter, and why there is a critical
size for any given composition.**

### 6.2 Moderation
**⚠️ Fast fission neutrons (~2 MeV) must be slowed to thermal (~0.025 eV) to exploit the
huge thermal cross section** (§3 → `nuclear-structure-decay-reactions-and-dose`).
**⚠️ Elastic scattering transfers most energy when masses match** — **hydrogen is ideal,
which is why water is the standard moderator.**
```
Light water   ⚠️ best moderation per collision, but absorbs neutrons → needs ENRICHED fuel
Heavy water   ⚠️ slightly worse moderation, very low absorption → runs on NATURAL uranium
Graphite      ⚠️ good, low absorption, large core
```
**⚠️ The resonance escape problem**: neutrons must pass *through* `²³⁸U`'s resonance region
without being captured, so **fast, efficient slowing-down is required** (§3 → `nuclear-structure-decay-reactions-and-dose`).

### 6.3 ⚠️ Delayed neutrons — why reactors are controllable at all
> **⚠️ GOTCHA — this is the single most important fact in reactor physics and it is
> almost never mentioned outside the field.**
> **About **0.65%** of fission neutrons from `²³⁵U` are emitted not promptly but seconds
> to minutes later, from decaying fission products.** ⚠️ **This tiny fraction stretches the
> mean neutron generation time from ~10⁻⁴ s to ~0.1 s — a factor of about a thousand.**
> **Without it, power would respond faster than any mechanical control system could act
> and reactors would be uncontrollable.**
>
> ⚠️ **"Prompt critical" means `ρ > β` — critical on prompt neutrons alone, without the
> delayed contribution.** **Power then rises on the microsecond timescale.** **This is the
> boundary that must never be crossed, and reactivity is measured in *dollars* where
> `$1 = β` precisely to make the margin legible.**

### 6.4 Reactivity feedback and control
**⚠️ Feedback coefficients determine whether a reactor is inherently stable:**
- **Fuel temperature (Doppler)** — ⚠️ **ALWAYS negative and ALWAYS prompt.** **Hotter
  `²³⁸U` has thermally broadened resonances, capturing more neutrons.** ⚠️ **This is the
  fastest-acting safety feature in a reactor and it is pure physics, requiring no
  action.**
- **Moderator temperature / void coefficient** — ⚠️ **negative in a light-water reactor:
  losing water loses moderation, so power falls.** ⚠️ **The RBMK design at Chernobyl had a
  *positive* void coefficient at low power, and that is the design root of the accident**
  (§9 → `nuclear-fuel-cycle-waste-and-safety`).
- **Xenon-135** — ⚠️ **the strongest neutron absorber known (~2.6 million barns).** **It
  builds up after shutdown and decays away over ~1–2 days — the "xenon pit," which can
  make a recently shut reactor impossible to restart for a day.** ⚠️ **Mismanaging xenon
  was a proximate factor at Chernobyl.**
- **Burnable poisons** (gadolinium, boron) to flatten reactivity over a fuel cycle;
  **control rods**; **soluble boron** in PWRs.

---
