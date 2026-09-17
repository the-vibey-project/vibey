# Military Science, Rockets, Space, Fusion, and Mars Plugin

Strategy that has an opponent, and engineering that has only physics — the two halves of
getting anything hard done off the surface of a planet, or deciding whether to.

One reference, split into 12 skills, so a task loads only the part it needs.

**The thesis the military half opens on**, and it is the line that separates this domain from
every other one in this marketplace:

> Military science is **not a science in the physics sense**. The object of study is a reactive,
> adapting adversary, which means no principle holds unconditionally and every advantage is
> temporary. Engineering has constraints; war has an opponent trying to invalidate your
> assumptions.

The engineering half has the mirror image, and it is why the rest of the reference can be
quantitative all the way down: **three facts generate everything in rocket engineering** —
momentum conservation with variable mass gives a logarithm, which is why rockets are 90%
propellant and why staging exists; a converging-diverging nozzle's performance factorizes
cleanly into c* times C_F, which is why combustion and nozzle can be measured and optimized
independently; and orbits are energy states, not altitudes, so vis-viva settles most of mission
design from two numbers.

## The skills

All twelve share the `endeavour-` prefix. It is not a subject shorthand — no single word covers
military science, rocketry, spaceflight, fusion energy and Mars at once, and `mil-`, `rocket-`,
`space-` and `nuclear-` are each already taken by another pack in this marketplace. Read it as
naming the whole undertaking these twelve parts describe. When skills are installed flat, these
are the twelve to look for.

| Skill | Sections | Covers |
|---|---|---|
| `endeavour-military-theory-levels-of-war-and-deterrence` | §1–§3 | Clausewitz, Sun Tzu and the other traditions, Mahan against Corbett and the bombing surveys; the three levels of war and why tactical success does not aggregate; deterrence by punishment and by denial, the measurement problem, nuclear survivability and the triad, escalation thresholds, alliances and grand strategy |
| `endeavour-logistics-doctrine-modern-conflict-and-the-law` | §4–§6 | Force structure and the readiness/modernization/size trilemma, logistics and the industrial base, doctrine and its rigidity paradox, intelligence, procurement; unmanned systems, cyber, space, information operations, irregular warfare and total defence; and the law of armed conflict in full |
| `endeavour-rocket-equation-nozzles-engines-and-propellants` | §7–§10 | Tsiolkovsky, staging and thrust; nozzle thermodynamics, the c*/C_F factorization, expansion ratio and flow separation; L\* and injectors; turbomachinery, the engine-cycle comparison, cooling and the Bartz correlation; propellants and density impulse |
| `endeavour-orbits-ascent-structures-and-reentry` | §11–§16 | Vis-viva and manoeuvres, J₂, sun-synchronous and Molniya; the ascent Δv budget, max-Q and q·α; buckling, balloon tanks and POGO; slosh, notch filters and powered-descent guidance; Sutton-Graves and the entry corridor; and the failure physics that recurs |
| `endeavour-mission-architecture-and-spacecraft-subsystems` | §17–§22 | The design cascade and the architecture trade; power, thermal, communications and navigation; attitude control, in-space propulsion and EDL; crew radiation, bone loss and SANS; ECLSS closure and MOXIE; margins, redundancy and the named failures |
| `endeavour-fusion-physics-confinement-and-engineering` | §23–§25 | The binding energy curve, the Coulomb barrier, the candidate reactions and the Lawson criterion; tokamaks, stellarators, direct and indirect drive; tritium breeding, 14 MeV neutron damage, divertor load and HTS magnets; and the Q-definition trap |
| `endeavour-satellites-flight-software-and-instruments` | §26–§28 | Orbit regimes and the constraint that defines each; flight software, FDIR, safe mode, CCSDS command and telemetry, and in-flight update; remote-sensing and in-situ instruments; planetary protection and the COSPAR categories |
| `endeavour-the-martian-environment-and-in-situ-resources` | §29–§30 | Mars as engineering parameters — pressure, composition, density, gravity, the sol, temperature, the lost dynamo, dust, surface radiation and perchlorates — and the water, CO₂ and regolith you can make propellant, air and structure from |
| `endeavour-mars-mission-design-and-settlement` | §31–§32 | Launch windows and transfer, the Martian EDL squeeze and supersonic retropropulsion, relay communications, surface power; habitats, rovers, ECLSS closure for a settlement, food as the largest unclosed loop, and the psychology |
| `endeavour-terraforming-warming-and-the-magnetic-field-problem` | §33–§35 | What terraforming means, the three habitability thresholds, the mass problem, the five gas sources and their honest assessments, warming strategies with both timescales, and the unsolved magnetic field problem |
| `endeavour-ecopoiesis-oxygen-timelines-and-ethics` | §36–§38 | Ecopoiesis and the extremophiles, the unsolved oxygen problem, the missing nitrogen cycle, the four-phase timeline with both columns, paraterraforming, the ethics of deliberate contamination and the governance vacuum, and Venus |
| `endeavour-reference` | §39–§40 | The 31-entry glossary spanning all six parts, each term pointing at the section that explains it, and the complete further-reading list in the source's own six groups |

Section numbers are **shared across the set**: a reference written as `§N → skill` points into
that sibling skill.

## ⚠️ Scope — what this reference is and is not

This is **strategic theory and engineering physics**, and it stays exactly there.

Part I is strategic studies at the war-college survey level: Clausewitz and Schelling and Kahn,
deterrence logic, escalation thresholds, alliance credibility, doctrine, procurement, and the
law of armed conflict. Part IV is fusion **energy**: the Lawson criterion, D-T cross sections,
confinement schemes, and what makes a demonstrated gain still not a power plant.

It carries **no weapon design, device physics, yield calculation, targeting, or construction or
employment detail**, in any of its twelve skills — not as an example, not to round out a section,
not in a table. The source document does not contain that material, and a skill that went
further than its source would be inventing it.

The **law of armed conflict is load-bearing, not an appendix**. Distinction, proportionality
stated correctly (expected incidental civilian harm against concrete and direct military
advantage, never a casualty comparison between sides), military necessity, humanity, and command
responsibility sit inside `endeavour-logistics-doctrine-modern-conflict-and-the-law`, so a
reader who loads only the institutional military skill still meets them.

## Where the source is honest, the pack stays honest

The best thing in this document is how carefully it marks the places its own fields get oversold,
and every one of those passages survives intact:

- **Q_scientific is not Q_engineering.** NIF's reported gains are measured against laser energy
  delivered to the target, not against the wall-plug energy the laser system draws. Kept as a
  callout, because it is the single most misread number in fusion.
- **Deterrence "working" for decades is compatible with having been repeatedly lucky**, and you
  cannot observe deterrence succeeding — the absence of attack is consistent with deterrence and
  with an adversary who never intended to attack.
- **The terraforming timeline keeps both columns.** Optimistic and conservative are the source's
  own, they are not a range to be averaged, and they are never collapsed to one number.
- **The magnetic field problem and the oxygen problem are unsolved**, and are presented that way.
  5×10¹⁶ kg of oxygen against essentially no reservoir is not an engineering margin.

## Neighbours in this marketplace

Several plugins cover this ground as **separate disciplines**; this one covers them as **one
problem, from the political decision to the planet**:

- `military-science-and-national-defence` — the same strategic-studies material as a standalone
  six-skill survey, including civil-military relations and the intelligence cycle at more length
- `rocket-science` and `space-exploration` — propulsion and mission design as their own
  disciplines, without the military or Mars-terraforming halves
- `flight-software` — cFS, F Prime, MISRA and JPL standards, radiation effects and V&V at far more
  depth than §27 here
- `aerospace-engineering` — the atmospheric side: airfoils, the drag breakdown, stability and
  control, air-breathing propulsion, aeroelasticity, flight test and certification
- `nuclear-physics` — fission and fusion as physics: cross sections, criticality, reactor types,
  fuel cycle and waste
- `thermodynamics-fluid-mechanics` — the cycles, compressible flow and heat transfer that the
  nozzle, cooling and reentry sections stand on
- `newtonian-mechanics` — orbits, rotation and the inertia tensor from first principles
- `engines-generators-and-fuels` and `power-engineering` — terrestrial energy conversion and the
  grid, where fusion would eventually have to land
- `game-theory` and `political-science-human-systems-governance` — the formal and institutional
  machinery behind deterrence, escalation and collective action
