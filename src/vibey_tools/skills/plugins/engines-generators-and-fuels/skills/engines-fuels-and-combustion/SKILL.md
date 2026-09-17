---
name: engines-fuels-and-combustion
description: "Use when choosing a fuel for an engine or generator, comparing energy densities, sizing fuel storage, deciding between internal and external combustion or no heat engine at all, reconciling efficiency figures quoted on HHV versus LHV, or working out air-fuel ratios, equivalence ratio and why a three-way catalyst forces closed-loop fuelling. Covers every fossil fuel, biofuel and non-combustion source with its energy density and matching engine type, the eleven-row fuel comparison table, and stoichiometric combustion chemistry. Part 5 of the Engines, Generators and Fuel Sources reference."
---

# Fuel Sources and Combustion Chemistry

> **Part 5 of 7** of the *Engines, Generators, and Fuel Sources* reference (plugin
> `engines-generators-and-fuels`), covering §15–§17 — every fuel that can be burned, transformed or harvested, with energy densities and what engine each pairs with. Sibling skills:
> `engines-thermodynamics-and-the-carnot-ceiling` (§1–§3 — the four laws, the Carnot ceiling, working fluids and phase behaviour),
> `engines-rankine-steam-engines-and-turbines` (§4–§6 — the Rankine cycle and its five improvements, reciprocating engines and turbines, and what you would actually build),
> `engines-otto-diesel-brayton-stirling-and-combined-cycles` (§7–§11 — internal combustion, gas turbines, the Stirling engine, and the combined cycle),
> `engines-generators-and-house-power` (§12–§14 — Faraday to a wired house: generator theory, the four machine types, and designing or buying a house system),
> `engines-rebuilding-engines-materials-and-tolerances` (§18–§20 — engine anatomy and the rebuild process, engine management and forced induction, and the materials and tolerance thinking that makes parts real),
> `engines-safety-and-reference` (§21–§23 — the six things that kill, the glossary, and the books that actually teach this),
>
> Section numbers are **shared across the whole set**: a reference written as §N → `skill` points
> into that sibling skill. Everything here is durable engineering and physics — the laws, cycles and
> equations do not expire; efficiency figures for current plant and practice do drift.

**The organising idea: the source determines the engine type.** Fuels that burn *internally* (petrol,
diesel, gas) pair with internal combustion engines. Fuels that burn *externally* (coal, wood, biomass,
waste heat) pair with external combustion engines — steam, Stirling. Non-thermal sources (hydro, wind,
solar PV) skip the heat engine entirely and convert energy directly. Pick the fuel and you have largely
picked the machine.

| Class | Examples | Engine it pairs with | Heat engine? |
|---|---|---|---|
| Burns internally | Petrol, diesel, natural gas, propane, ethanol, biodiesel, biogas | Otto, Diesel, Brayton (§7–§11 → `engines-otto-diesel-brayton-stirling-and-combined-cycles`) | Yes |
| Burns externally | Coal, wood/biomass, waste heat | Rankine steam (§4–§6 → `engines-rankine-steam-engines-and-turbines`), Stirling (§10 → `engines-otto-diesel-brayton-stirling-and-combined-cycles`) | Yes |
| Heats without burning | Nuclear fission, concentrated solar, geothermal | Rankine — the reactor, the mirror field or the Earth replaces the boiler | Yes |
| No heat at all | Hydro, wind, solar PV | Direct conversion to rotation or to electricity (§12–§14 → `engines-generators-and-house-power`) | No |

## §15 Fuel categories

### Fossil fuels

**Coal.** Ranked by carbon content and energy along a fixed ladder — **peat → lignite → sub-bituminous →
bituminous → anthracite**. Thermal coal burns in pulverized-coal boilers at **~1,500°C** to make steam at
**250–600°C and 150–300 bar**. **15–30 MJ/kg** depending on rank. It is the most carbon-intensive fuel per
kWh — about **2× natural gas** for the same electricity. Metallurgical/coking coal is a separate market:
processed into coke for steelmaking, currently **with no drop-in substitute at scale**.

**Petroleum (crude oil).** A mixture of hydrocarbons refined by *distillation* (separating by boiling point)
and *conversion* (cracking heavy fractions into lighter, more valuable ones).

| Fraction | Distillation cut | Energy density |
|---|---|---|
| Petrol | 40–60°C | 44 MJ/kg |
| Diesel / kerosene | 150–250°C | 43 MJ/kg |
| Heavy fuel oil | residual | 40 MJ/kg |

Refining also produces lubricants, asphalt and petrochemical feedstocks. **Octane rating is knock resistance,
not energy content.** **Cetane rating** (diesel) measures ignition quality — *the opposite of octane*; higher
cetane means easier ignition.

**Natural gas.** Primarily methane (CH₄) with some ethane, propane, butane. **50–55 MJ/kg — the highest
energy density per kg of any fossil fuel.** Burns cleanly: no particulate, low NOx if premixed, CO₂ about
**60% that of coal per kWh**. Used in gas turbines (Brayton) and reciprocating gas engines (Otto modified for
gas). Compressed (**CNG, ~200 bar**) or liquefied (**LNG, −162°C**) for storage and transport.

**Propane (LPG).** A byproduct of natural gas processing and crude refining. **46 MJ/kg.** Clean-burning,
**stores indefinitely in pressurized tanks**, excellent for standby generators. Popular for dual-fuel and
tri-fuel generator conversions.

### Biofuels

**Wood and biomass.** The original fuel. **15–20 MJ/kg dry.** Burns at **600–1200°C** depending on moisture and
airflow — though in a steam system the combustion temperature matters less than heat transfer to the boiler.
**Wood gasification** (heating wood in low oxygen to produce a combustible gas of CO, H₂ and CH₄) was used
extensively in WWII to run petrol engines when petrol was unavailable. Producer gas is about **5–6 MJ/m³ vs
38 MJ/m³ for natural gas** — much lower energy density, but it works.

**Ethanol.** **30 MJ/kg** (about **70% of petrol's energy density by volume**). From fermentation of sugars —
sugarcane, corn, cellulosic. Blended with petrol (E10, E85). **High octane (~110)**, so it allows higher
compression ratios, partially offsetting the lower energy density. The energy balance (energy out vs energy in
to produce) is debated and depends heavily on feedstock and process.

**Biodiesel.** **38 MJ/kg.** From vegetable oils or animal fats via transesterification. Usable in unmodified
diesel engines or blended. Renewable, biodegradable, lower particulate emissions. The feedstock — crop oils,
used cooking oil, algae — determines energy balance and economics.

**Biogas.** **20–25 MJ/m³.** From anaerobic digestion of organic waste (manure, food waste, sewage). Typically
**55–70% methane** with CO₂ and trace gases. Usable in modified gas engines, or cleaned to biomethane
(pipeline quality) and injected into the gas grid. **The cleaning — removing CO₂, H₂S and moisture — is the
main cost.**

### Non-combustion energy sources

**Nuclear fission.** U-235 fission releases about **200 MeV per atom** — roughly **80 million MJ/kg of
U-235, about 2–3 million times the energy density of coal**.

> **Nuclear reactors ARE steam plants.** Fission heats water (directly in a BWR, or via a heat
> exchanger in a PWR) and the rest is a conventional Rankine cycle (§4–§6 →
> `engines-rankine-steam-engines-and-turbines`). **The reactor replaces the boiler.** Nothing
> downstream of the steam is nuclear engineering.

Fuel is cheap per kWh (capital cost dominates), supply is abundant, emissions near-zero. Challenges: capital
cost, construction time, waste management, public acceptance.

**Solar thermal (concentrated).** Mirrors concentrate sunlight to heat a fluid — oil, molten salt, or steam —
to **300–600°C**, driving a Rankine cycle. Thermal storage (**molten salt at 560°C**) allows generation after
sunset: **the only large-scale solar technology that includes economical storage.**

**Solar PV.** Converts sunlight directly to electricity, no heat engine — so the Carnot ceiling (§1–§3 →
`engines-thermodynamics-and-the-carnot-ceiling`) does not bound it.

| Cell type | Efficiency |
|---|---|
| Commercial silicon | 15–22% |
| Premium | 25–30% |
| Multi-junction (expensive, aerospace) | 40%+ |

No moving parts, no fuel, minimal maintenance. Paired with battery storage for 24-hour supply.

**Wind.** Kinetic energy converted directly to rotation by the rotor, then to electricity. No heat engine.
**Power scales with the CUBE of wind speed:**

    P ∝ v³

which is why wind is extremely sensitive to site conditions — on that law alone, a site with twice the wind
speed yields **eight times** the power (arithmetic on P ∝ v³, not a source figure). Turbines use induction
generators or PM synchronous generators with full power conversion (AC → DC → AC); for the machine types
themselves see §12–§14 → `engines-generators-and-house-power`.

**Hydro.** Potential energy of falling water drives a turbine directly. No heat engine. **The most mature,
efficient and reliable renewable: 85–95% water-to-wire.** Pumped hydro is the dominant form of grid-scale
energy storage.

**Geothermal.** Heat from the Earth's interior — radioactive decay of uranium, thorium and potassium in the
crust. **High-temperature resources (150–350°C+)** drive conventional steam turbines. **Low temperature
(80–150°C)** can drive organic Rankine cycles (ORC) using refrigerants or hydrocarbons instead of water.
Essentially a heat engine where **the boiler is the Earth**.

**Waste heat.** Industrial processes reject enormous amounts of heat. It can drive an **Organic Rankine
Cycle** — a Rankine cycle using a low-boiling-point working fluid (refrigerants, silicones, hydrocarbons)
boiling at **80–200°C instead of water's 100°C**. Increasingly used for waste-heat recovery from engines,
industrial furnaces and geothermal sources.

## §16 The fuel comparison table

| Fuel | Energy density | Engine type | Combustion | Notes |
|---|---|---|---|---|
| Petrol | 44 MJ/kg (32 MJ/L) | Otto (spark-ignition) | Internal | Octane-rated; limited shelf life (3–6 months); vapour pressure varies by season |
| Diesel | 43 MJ/kg (38 MJ/L) | Diesel (compression-ignition) | Internal | Higher efficiency engine; longer shelf life (6–12 months); safer to store than petrol |
| Natural gas | 50 MJ/kg (38 MJ/m³) | Brayton, Otto-gas | Internal | Cleanest fossil fuel; no liquid storage; needs pipeline or CNG/LNG |
| Propane (LPG) | 46 MJ/kg (25 MJ/L liquid) | Otto-gas, Brayton | Internal | Stores indefinitely; clean-burning; excellent for standby generators |
| Coal (bituminous) | 24 MJ/kg | Rankine (steam) | External | Most carbon-intensive; cheap and abundant; boiler/ash handling complex |
| Wood (dry) | 15–18 MJ/kg | Rankine, Stirling, gasifier-Otto | External | Renewable; moisture kills efficiency; ash and creosote management needed |
| Ethanol (E85) | 30 MJ/kg (25 MJ/L) | Otto (spark-ignition) | Internal | High octane; renewable; lower energy density than petrol |
| Biodiesel (B100) | 38 MJ/kg (33 MJ/L) | Diesel (compression-ignition) | Internal | Renewable; biodegradable; may gel in cold weather; can affect seals in old engines |
| Biogas | 20–25 MJ/m³ | Otto-gas, Brayton | Internal | Renewable; requires cleaning (H₂S removal); low energy density |
| Hydrogen | 120 MJ/kg (but 10 MJ/L at 700 bar) | Brayton, Otto-modified, fuel cell | Internal or electrochemical | Highest energy per kg, lowest per litre; embrittles steel; hard to store; NOx if burned in air |
| Uranium-235 | ~80 million MJ/kg | Rankine (steam) | Nuclear fission | Extraordinary energy density; zero emissions; waste and safety challenges |

**Reading the table:** MJ/kg and MJ/L tell different stories and the disagreement is the point. Hydrogen has
the highest energy per kg of anything listed and the lowest per litre.


### HHV vs LHV

**Higher Heating Value** includes the latent heat of water vapour formed during combustion; **Lower
Heating Value** does not.

- A **condensing boiler can recover that latent heat and appear to exceed 100% efficiency** — but only because
  efficiency is quoted on LHV.
- Cross-comparisons between fuels are frequently apples-to-oranges if one uses HHV and the other LHV.
- **European practice typically uses LHV; American practice varies.** Always check which basis a quoted
  efficiency uses before comparing two numbers.

## §17 Combustion chemistry

**Stoichiometric air-fuel ratio.**

| Fuel | Stoichiometric AFR (by mass) | How it is actually run |
|---|---|---|
| Petrol | **about 14.7:1** (1 kg fuel needs 14.7 kg air) | Held at stoichiometric by closed-loop control |
| Diesel | **about 14.5:1** | Typically **lean, 20:1 to 60:1**, because power is controlled by fuel quantity, not air |

**The equivalence ratio φ.** **φ > 1 is rich** (excess fuel); **φ < 1 is lean** (excess air).

**The rich/lean trade-off — there is no free side.**

| | Power | Efficiency | Emissions |
|---|---|---|---|
| **Rich (φ > 1)** | More power | Lower efficiency | Higher CO / HC |
| **Lean (φ < 1)** | Less power | More efficient | **More NOx** — peak flame temperatures are high with excess oxygen |

**Why closed-loop fuel control exists.** Modern engines use **three-way catalysts, which require
stoichiometric operation** — the converter only works inside a narrow window around φ = 1. That constraint,
not fuel economy, is what forces the engine to hold stoichiometric continuously, and it is the whole reason
for the O₂-sensor feedback loop and fuel trims described in §18–§20 →
`engines-rebuilding-engines-materials-and-tolerances`. The same chemistry explains a structural asymmetry
between the two engine families: **diesels run lean overall, so a three-way catalyst cannot work** (excess
oxygen in the exhaust), which is why diesel aftertreatment takes the entirely different DPF-plus-SCR route
covered in §7–§11 → `engines-otto-diesel-brayton-stirling-and-combined-cycles`.

> **Fuel handling is a safety subject, not a logistics one.** Flash points, vapour pooling, storage siting,
> extinguisher selection and fuel-supply shutoff are covered in full in §21–§23 → `engines-safety-and-reference`.
> Read it before storing any quantity of fuel.
