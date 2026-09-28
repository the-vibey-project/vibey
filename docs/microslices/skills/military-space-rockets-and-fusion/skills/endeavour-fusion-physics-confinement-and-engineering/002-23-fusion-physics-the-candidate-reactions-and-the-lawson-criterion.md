---
id: skill-23-fusion-physics-the-candidate-reactions-and-the-lawson-criterion-57f66b235a
purpose: 23 fusion physics the candidate reactions and the lawson criterion
source: src/vibey_tools/skills/plugins/military-space-rockets-and-fusion/skills/endeavour-fusion-physics-confinement-and-engineering/SKILL.md
requires: ["skill-the-framing-for-part-iv-62ba12965d"]
links: ["skill-24-magnetic-and-inertial-confinement-2657877a5e"]
---

## §23 Fusion physics, the candidate reactions, and the Lawson criterion

### The Coulomb barrier is the whole problem

Nuclei must approach to **~1 fm** against electrostatic repulsion. Quantum tunnelling helps, but you
still need **~10–15 keV (~100–150 million K)**. Everything else in fusion — every magnet, every
laser, every confinement scheme — exists to hold matter at that temperature long enough and densely
enough to burn.

### The candidate reactions

| Reaction | Products | Notes |
|---|---|---|
| D + T | ⁴He (3.5 MeV) + n (14.1 MeV) | Highest cross section at lowest temperature. The only near-term option — and 80% of the energy is in a neutron |
| D + D | Two branches | No tritium needed, much harder |
| D + ³He | ⁴He + p | Aneutronic-ish, but ³He is essentially unavailable and needs far higher temperature |
| p + ¹¹B | 3 ⁴He | Truly aneutronic; enormous temperature and bremsstrahlung losses. Very hard |

**Why D-T despite the neutron problem.** Its cross section peaks **about 100× higher and at roughly
a quarter the temperature** of the alternatives. Everything else is a much harder physics problem in
exchange for an easier engineering one — and the engineering price D-T charges in return is the
14.1 MeV neutron, which is where most of §25 goes.

Note the split inside D-T's own energy release: the **3.5 MeV alpha** stays charged and can be
confined, which is what makes self-heating possible; the **14.1 MeV neutron** leaves immediately,
carrying 80% of the yield into the structure. The reaction that is easiest to ignite is also the one
that puts most of its output somewhere you cannot steer it.

### The Lawson criterion / triple product

    n · T · τ_E ≳ 3×10²¹ keV·s·m⁻³   (D-T ignition)

Density × temperature × energy confinement time. **The two confinement approaches attack different
factors of the same product**, which is why they look nothing alike and yet are measured against the
same number:

| | Density | Energy confinement time τ_E | How the product is reached |
|---|---|---|---|
| Magnetic confinement | Low | Long — **seconds** | Hold a thin plasma still for a long time |
| Inertial confinement | Enormous | Vanishing — **nanoseconds** | Compress to extreme density and let inertia do the rest |

Both must reach the same product. A scheme that wins on one factor has to pay for it on another.

> **Q DEFINITIONS — A RECURRING SOURCE OF INFLATED CLAIMS**
>
> - **Q_scientific** is fusion energy out divided by energy delivered to the plasma or target.
> - **Q_engineering** is electricity out divided by total electricity in, *including the whole
>   facility* — **this is the one that matters for a power plant**.
> - **Ignition** is when the alpha particles alone sustain the burn.
> - **NIF's reported gains are scientific Q against laser energy delivered to the target**, not
>   against the wall-plug energy drawn by the laser system, which is far larger.
>
> When a headline reports a gain, the first question is which Q it is measured against, and the
> second is what was in the denominator.
