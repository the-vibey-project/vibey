---
id: skill-22-glossary-82df7851df
purpose: 22 glossary
source: src/vibey_tools/skills/plugins/engines-generators-and-fuels/skills/engines-safety-and-reference/SKILL.md
requires: ["skill-21-safety-the-things-that-kill-728f5eb5d6"]
links: ["skill-23-further-reading-the-books-that-actually-teach-this-d9c0c55bc9"]
---

## §22 Glossary

Twenty-one entries, alphabetical. The final column points at the section — in this skill set —
that explains the term in context.

| Term | Definition | Explained in |
|---|---|---|
| **Back-Work Ratio** | The fraction of a turbine's gross output consumed by the compressor or pump. In Rankine cycles ~1–2%; in Brayton cycles 50–65%. The Rankine cycle's key advantage. | §4 → `engines-rankine-steam-engines-and-turbines` |
| **BSFC (Brake Specific Fuel Consumption)** | Fuel consumed per unit of mechanical work output, typically g/kWh. Lower is better. A good diesel might achieve 200 g/kWh; a good petrol engine 250 g/kWh. The most useful single number for comparing engine efficiency. | §14 → `engines-generators-and-house-power` |
| **Carnot Efficiency** | 1 − T_C/T_H. The maximum possible efficiency of any heat engine between two temperatures. Unreachable in practice but defines the ceiling. | §2 → `engines-thermodynamics-and-the-carnot-ceiling` |
| **Cetane Rating** | A diesel fuel's ignition quality. Higher cetane means shorter ignition delay and smoother combustion. The diesel equivalent of octane, measuring the opposite property. | §15 → `engines-fuels-and-combustion` |
| **Compression Ratio** | Cylinder volume at BDC divided by volume at TDC. Higher = more efficient (Otto: η = 1 − 1/r^(γ−1)) but limited by knock in petrol engines. | §7 → `engines-otto-diesel-brayton-stirling-and-combined-cycles` |
| **Cut-off** | The point in the power stroke at which steam admission to a reciprocating cylinder stops. Early cut-off = expansive working = higher efficiency, lower power. The steam engine's gearbox. | §5 → `engines-rankine-steam-engines-and-turbines` |
| **Enthalpy (h)** | h = u + Pv. Internal energy plus flow work. A bookkeeping convenience for open systems, not a distinct form of energy. | §1 → `engines-thermodynamics-and-the-carnot-ceiling` |
| **Entropy (S)** | A measure of energy unavailability and microstate multiplicity. S_gen ≥ 0 for any real process. The Second Law quantified. | §1 → `engines-thermodynamics-and-the-carnot-ceiling` |
| **Exergy** | The maximum useful work obtainable as a system comes to equilibrium with the environment. Destroyed in proportion to entropy generated: X_destroyed = T₀ · S_gen. The rigorous tool for finding where real losses occur in a power plant. | §1 → `engines-thermodynamics-and-the-carnot-ceiling` |
| **Governor** | A device regulating engine speed by adjusting fuel or steam input in response to load. Mechanical governors use flyweights; electronic ones use sensors and actuators. Droop (a deliberate speed decrease with load) allows multiple generators to share load without communication. | §12 → `engines-generators-and-house-power` |
| **HHV / LHV** | Higher/Lower Heating Value. HHV includes the latent heat of water vapour in combustion products; LHV does not. Condensing boilers can exceed 100% efficiency on an LHV basis. | §16 → `engines-fuels-and-combustion` |
| **Isentropic** | Constant entropy; an ideal (reversible, adiabatic) process. Real turbines and compressors deviate; the deviation is measured by isentropic efficiency. | §4 → `engines-rankine-steam-engines-and-turbines` |
| **Knock (Detonation)** | Uncontrolled auto-ignition of end gas ahead of the flame front in a petrol engine. Destructive pressure spikes. Limits compression ratio. Detected by knock sensors; managed by retarding timing. | §7 → `engines-otto-diesel-brayton-stirling-and-combined-cycles` |
| **Octane Rating** | A petrol fuel's resistance to knock. Higher octane allows higher compression ratios. NOT a measure of energy content — premium fuel in an engine that does not require it buys nothing. | §15 → `engines-fuels-and-combustion` |
| **Quality (x)** | In a two-phase liquid-vapour mixture, the mass fraction that is vapour. Determines enthalpy, entropy and volume in the saturation region. | §3 → `engines-thermodynamics-and-the-carnot-ceiling` |
| **Regenerative Feedwater Heating** | Bleeding steam from intermediate turbine stages to preheat boiler feedwater. Raises the average temperature of heat addition. The most impactful Rankine improvement after superheat. | §4 → `engines-rankine-steam-engines-and-turbines` |
| **Reheat** | Returning partially-expanded steam to the boiler for another superheater pass before continuing through the turbine. Raises average heat-addition temperature and reduces exhaust moisture. | §4 → `engines-rankine-steam-engines-and-turbines` |
| **Specific Speed** | A dimensionless group selecting turbomachine type (radial, mixed, axial) for a given duty. The practical application of dimensional analysis. | §5 → `engines-rankine-steam-engines-and-turbines` |
| **Stoichiometric** | The chemically correct air-fuel ratio with neither excess air nor excess fuel. For petrol ~14.7:1 by mass. The point where a three-way catalyst works. | §17 → `engines-fuels-and-combustion` |
| **Superheat** | Heating steam above its saturation temperature at a given pressure. Raises average heat-addition temperature and reduces turbine exhaust moisture. | §4 → `engines-rankine-steam-engines-and-turbines` |
| **Volumetric Efficiency** | How completely an engine cylinder fills with fresh charge. The target of every intake design, valve timing and forced-induction decision. Typically 85–90% for a well-designed naturally aspirated engine at peak torque. | §7 → `engines-otto-diesel-brayton-stirling-and-combined-cycles` |
