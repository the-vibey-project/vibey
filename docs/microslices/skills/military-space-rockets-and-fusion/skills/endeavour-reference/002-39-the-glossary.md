---
id: skill-39-the-glossary-2d6896b621
purpose: 39 the glossary
source: src/vibey_tools/skills/plugins/military-space-rockets-and-fusion/skills/endeavour-reference/SKILL.md
requires: ["skill-how-to-read-a-pointer-cebb306e31"]
links: ["skill-40-further-reading-3fbbca2bd7"]
---

## §39 The glossary

Thirty-one entries, in the source's own order — the first twenty-four run across military science,
rocketry, spaceflight, fusion and flight software; the last seven are the Mars and terraforming block.
Each definition is the reference's own, numbers intact; the pointer sends you to the section where
the term does work.

| Term | Definition | Explained in |
|---|---|---|
| **Auftragstaktik (Mission Command)** | Specify the intent and the task, delegate the method. Requires trust, shared doctrine, and tolerance of subordinate error. | §2 → `endeavour-military-theory-levels-of-war-and-deterrence` |
| **Binding Energy Curve** | Binding energy per nucleon versus mass number. Rises steeply from hydrogen to iron-56 (fusion releases energy), peaks at ~8.8 MeV/nucleon, declines slowly to uranium (fission releases energy). The single curve that explains both fission and fusion. | §23 → `endeavour-fusion-physics-confinement-and-engineering` |
| **Characteristic Velocity (c\*)** | p_c · A\* / ṁ. Measures combustion quality only — how well chemical energy was converted to hot, low-molecular-weight gas. Typical: 1,800 m/s (kerolox) to 2,350 m/s (hydrolox). | §8 → `endeavour-rocket-equation-nozzles-engines-and-propellants` |
| **Clausewitz's Trinity** | Primordial violence (the people), chance and probability (the army), and rational subordination to policy (the government). War is unstable between these three. | §1 → `endeavour-military-theory-levels-of-war-and-deterrence` |
| **Culminating Point** | The point at which an offensive has weakened enough (extending supply lines, absorbing losses) that the defender becomes stronger. Usually a logistics phenomenon. Recognizing it is one of the hardest judgements in operational art. | §1 → `endeavour-military-theory-levels-of-war-and-deterrence` (and again as a logistics phenomenon at §4 → `endeavour-logistics-doctrine-modern-conflict-and-the-law`) |
| **Delta-v (Δv)** | The change in velocity a manoeuvre requires. The currency of spacecraft mission design. The rocket equation relates it to mass ratio: Δv = Isp · g₀ · ln(m₀/m_f). | §7 → `endeavour-rocket-equation-nozzles-engines-and-propellants` |
| **Density Impulse** | I_ρ = Isp × ρ_bulk. Impulse per unit tank volume. For volume-constrained stages, matters more than Isp. The quantitative reason hydrogen loses on first stages. | §10 → `endeavour-rocket-equation-nozzles-engines-and-propellants` |
| **Deterrence by Denial** | Convincing the opponent the objective cannot be achieved. Generally more credible than deterrence by punishment, because it does not require the defender to accept costs of its own. | §3 → `endeavour-military-theory-levels-of-war-and-deterrence` |
| **EDL** | Entry, Descent, and Landing. The sequence from atmospheric entry interface to surface touchdown. Mars EDL is the canonical hard case — the atmosphere is too thin for parachutes alone but thick enough to require a heat shield. | §20 → `endeavour-mission-architecture-and-spacecraft-subsystems` (the Mars case in full at §31 → `endeavour-mars-mission-design-and-settlement`) |
| **FDIR** | Fault Detection, Isolation, and Recovery. The organizing principle of flight software. Detect anomalies, isolate the cause, recover by reconfiguration or safe mode. | §27 → `endeavour-satellites-flight-software-and-instruments` |
| **Friction (Clausewitz)** | "Everything in war is simple, but the simplest thing is difficult." The accumulation of small difficulties that separates the plan from the execution. | §1 → `endeavour-military-theory-levels-of-war-and-deterrence` |
| **Gravity Turn** | After a vertical rise, pitch slightly, then let gravity rotate the velocity vector with zero angle of attack. Zero-α is a structural constraint, not an efficiency choice. | §12 → `endeavour-orbits-ascent-structures-and-reentry` |
| **Hohmann Transfer** | Two-burn, minimum-energy transfer between coplanar circular orbits. The standard orbital manoeuvre for moving between altitudes. | §11 → `endeavour-orbits-ascent-structures-and-reentry` |
| **ISRU** | In-Situ Resource Utilization. Making propellant, oxygen, water, or other consumables at the destination rather than launching them from Earth. Breaks the exponential mass cost of the rocket equation. | §21 → `endeavour-mission-architecture-and-spacecraft-subsystems` (the full Martian mine-to-methalox chain at §30 → `endeavour-the-martian-environment-and-in-situ-resources`) |
| **Lawson Criterion** | n · T · τ_E ≳ 3×10²¹ keV·s·m⁻³ for D-T ignition. The triple product of density, temperature, and energy confinement time that must be achieved for net fusion energy. | §23 → `endeavour-fusion-physics-confinement-and-engineering` |
| **Mass Ratio** | MR = m₀/m_f = exp(Δv / (Isp·g₀)). The ratio of initial to final mass required for a given Δv. At 9.4 km/s to LEO, MR ≈ 15.6, meaning 94% propellant. | §7 → `endeavour-rocket-equation-nozzles-engines-and-propellants` |
| **Normalization of Deviance** | An off-nominal observation recurs without consequence and is reclassified as acceptable. The recurring organizational failure mode in aerospace — Challenger and Columbia both followed this pattern. | §16 → `endeavour-orbits-ascent-structures-and-reentry` |
| **OODA Loop** | Observe, Orient, Decide, Act — Boyd's decision cycle. Operating inside an opponent's cycle causes disorientation and collapse. ORIENT is the part Boyd considered decisive and the part popular versions omit. | §2 → `endeavour-military-theory-levels-of-war-and-deterrence` |
| **Oberth Effect** | The same propellant buys more energy when you're moving faster, because energy change includes a v·Δv term. Hence departure burns at periapsis and the value of dropping deep into a gravity well before burning. | §11 → `endeavour-orbits-ascent-structures-and-reentry` |
| **RTG** | Radioisotope Thermoelectric Generator. Converts heat from ²³⁸Pu decay to electricity at ~6–7% efficiency. ~110 W electrical at BOL. The only practical power source beyond Jupiter. | §18 → `endeavour-mission-architecture-and-spacecraft-subsystems` |
| **SANS** | Spaceflight Associated Neuro-Ocular Syndrome. Optic disc oedema, globe flattening, choroidal folds, hyperopic shifts. Affects ~70% of astronauts on missions over 6 months. Underlying cause not understood. A key constraint on crewed Mars missions. | §21 → `endeavour-mission-architecture-and-spacecraft-subsystems` |
| **Stability-Instability Paradox** | Stability at the nuclear level can enable conflict at lower levels, because both sides know it will not escalate to nuclear exchange. | §3 → `endeavour-military-theory-levels-of-war-and-deterrence` |
| **Thrust Coefficient (C_F)** | Measures nozzle quality only — how well the nozzle expanded the exhaust. Depends on γ, p_c/p_e, and area ratio. Typical: 1.5–1.9. | §8 → `endeavour-rocket-equation-nozzles-engines-and-propellants` |
| **Vis-Viva Equation** | v² = μ(2/r − 1/a). The single most useful formula in mission design. Determines velocity at any point on an orbit from the semi-major axis and radial distance. | §11 → `endeavour-orbits-ascent-structures-and-reentry` |
| **Armstrong Limit** | ~6.3 kPa atmospheric pressure. Below this, water boils at human body temperature (37 °C). The first threshold for Mars terraforming — above it, humans can survive with an oxygen mask rather than a full pressure suit. | §33 → `endeavour-terraforming-warming-and-the-magnetic-field-problem` |
| **Ecopoiesis** | The introduction of microbial life to a sterile planet as the first biological phase of terraforming. Begins oxygen production, nitrogen fixation, and soil formation. | §36 → `endeavour-ecopoiesis-oxygen-timelines-and-ethics` |
| **Paraterraforming** | Creating habitable enclosed environments (domes over craters, roofed lava tubes) rather than transforming an entire planet. Vastly smaller gas volume and immediate practicality make it the tractable alternative to full planetary terraforming. | §37 → `endeavour-ecopoiesis-oxygen-timelines-and-ethics` |
| **Perchlorates** | ClO₄⁻ salts present in Martian regolith at 0.4–0.6% by mass. Toxic to human thyroid function, lower the freezing point of water (enabling transient brines), and are a potential in situ oxygen source. | §29 → `endeavour-the-martian-environment-and-in-situ-resources` |
| **Sol** | The Martian day: 24 hours 39 minutes 35.244 seconds. Remarkably close to Earth's day, simplifying circadian adaptation and solar power scheduling. | §29 → `endeavour-the-martian-environment-and-in-situ-resources` |
| **Super-Greenhouse Gases** | Manufactured gases (PFCs, SF₆, CFCs) thousands to tens of thousands of times more potent as greenhouse gases than CO₂. The most physically plausible method for warming Mars, requiring industrial infrastructure but no unknown physics. | §34 → `endeavour-terraforming-warming-and-the-magnetic-field-problem` |
| **Terraforming** | Deliberate modification of a planet's environment to make it habitable for Earth life without life support. Mars is the only plausible candidate in the solar system. Full terraforming may take 10,000–100,000 years; the warming phase is plausible on century timescales. | §33 → `endeavour-terraforming-warming-and-the-magnetic-field-problem` |

### The same thirty-one, grouped by part

| Part | Terms |
|---|---|
| I — Military Science | Auftragstaktik (§2), Clausewitz's Trinity (§1), Culminating Point (§1, §4), Deterrence by Denial (§3), Friction (§1), OODA Loop (§2), Stability-Instability Paradox (§3) |
| II — Rocket Science | Characteristic Velocity (§8), Delta-v (§7), Density Impulse (§10), Gravity Turn (§12), Hohmann Transfer (§11), Mass Ratio (§7), Normalization of Deviance (§16), Oberth Effect (§11), Thrust Coefficient (§8), Vis-Viva Equation (§11) |
| III — Space Exploration | EDL (§20), ISRU (§21), RTG (§18), SANS (§21) |
| IV — Fusion Reactors | Binding Energy Curve (§23), Lawson Criterion (§23) |
| V — Satellites and Space Probes | FDIR (§27) |
| VI — Mars and Terraforming | Armstrong Limit (§33), Ecopoiesis (§36), Paraterraforming (§37), Perchlorates (§29), Sol (§29), Super-Greenhouse Gases (§34), Terraforming (§33) |

### Three pairs worth reading together

Drawn from the reference's own sections, not added to them:

- **c\* and C_F are a deliberate separation.** Characteristic velocity measures the injector and the
  chamber; thrust coefficient measures the nozzle. Because Isp · g₀ = c\* · C_F and both are separately
  measurable, a single hot-fire tells you which end of the engine is the problem (§8).
- **The culminating point and the Δv budget are the same lesson in two domains.** An offensive stops
  when it outruns supply, not when it runs out of courage (§4); a stage stops when the logarithm runs
  out, which is why rockets are 94% propellant (§7). Both are hard limits that look like failures of
  will from the outside.
- **Normalization of deviance and FDIR point in opposite directions.** One is an organization quietly
  reclassifying an anomaly as acceptable (§16); the other is a machine designed to detect an anomaly,
  isolate it and stop (§27). The failure mode the first names is the one the second exists to resist.
