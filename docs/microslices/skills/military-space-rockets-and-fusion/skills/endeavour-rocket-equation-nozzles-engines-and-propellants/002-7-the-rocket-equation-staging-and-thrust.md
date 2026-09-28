---
id: skill-7-the-rocket-equation-staging-and-thrust-859667a789
purpose: 7 the rocket equation staging and thrust
source: src/vibey_tools/skills/plugins/military-space-rockets-and-fusion/skills/endeavour-rocket-equation-nozzles-engines-and-propellants/SKILL.md
requires: ["skill-the-three-facts-that-generate-rocket-engineering-76672f2c79"]
links: ["skill-8-nozzle-thermodynamics-the-c-c-f-factorization-and-the-combustion-chamber-eaf6cdcfc6"]
---

## §7 The rocket equation, staging, and thrust

The **Tsiolkovsky rocket equation**, derived from momentum conservation: a vehicle of mass m expels
propellant at exhaust velocity v_e. Integrating from initial mass m_0 to final mass m_f gives:

    Δv = v_e · ln(m_0/m_f) = Isp · g_0 · ln(m_0/m_f)

The consequences are brutal. Rearranged, the **mass ratio**:

    MR = m_0/m_f = exp(Δv / (Isp·g_0))

**The worked consequence.** For Δv of 9.4 km/s to LEO at Isp = 350 s, the mass ratio is **15.6** —
meaning **94% propellant**. Structure, engines and payload share the remaining 6%. A stage
**structural coefficient** ε (structure mass divided by structure plus propellant) of **0.06–0.10**
is typical for a good aluminium stage. If ε alone were 0.06, you would have zero payload — which is
why **single-stage-to-orbit is marginal**.

### Staging mathematics

For n stages, Δv is additive:

    Δv_total = Σ Isp_i · g_0 · ln(MR_i)

The optimization: for stages with **equal Isp and equal ε, the Δv-optimal split is equal Δv per
stage**. With differing Isp and ε, optimal staging puts more Δv on the stage with the **higher Isp
and lower ε** — which is why upper stages use hydrogen (§10) and are pushed to do a disproportionate
share.

**Diminishing returns.** Going from 2 to 3 stages typically buys **10–15% payload**; 3 to 4 buys a
few percent, at the cost of another separation event — a top failure mode (§16 →
`endeavour-orbits-ascent-structures-and-reentry`).

### Thrust

    F = ṁ · v_e + (p_e − p_a)·A_e

The **pressure term** is why Isp is altitude-dependent. The same engine quotes two numbers: the
Merlin 1D delivers **~282 s at sea level and ~311 s in vacuum**. When the exhaust pressure p_e
matches ambient p_a, the term is zero and the nozzle is **optimally expanded**.
