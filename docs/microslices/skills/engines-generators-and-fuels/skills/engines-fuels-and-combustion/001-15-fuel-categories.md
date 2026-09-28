---
id: skill-15-fuel-categories-aac303d5f4
purpose: 15 fuel categories
source: src/vibey_tools/skills/plugins/engines-generators-and-fuels/skills/engines-fuels-and-combustion/SKILL.md
requires: []
links: ["skill-16-the-fuel-comparison-table-1e7ce1d531"]
---

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
