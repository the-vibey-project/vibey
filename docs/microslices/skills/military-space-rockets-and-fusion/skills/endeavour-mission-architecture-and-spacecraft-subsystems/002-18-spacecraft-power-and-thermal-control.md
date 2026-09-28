---
id: skill-18-spacecraft-power-and-thermal-control-c22f9581f6
purpose: 18 spacecraft power and thermal control
source: src/vibey_tools/skills/plugins/military-space-rockets-and-fusion/skills/endeavour-mission-architecture-and-spacecraft-subsystems/SKILL.md
requires: ["skill-17-mission-architecture-and-the-design-cascade-c4264fc4ce"]
links: ["skill-19-communications-navigation-and-autonomy-bf7f34e526"]
---

## §18 Spacecraft power and thermal control

A spacecraft is a **bus** (the supporting infrastructure — power, thermal, attitude control,
propulsion, communications, command and data handling, structure) plus a **payload** (the instrument
or communication package the mission exists for); the split itself, and the orbit regimes it gets
designed into, are at §26 → `endeavour-satellites-flight-software-and-instruments`. This section
covers the first two subsystems.

### Power

**Solar flux scales as 1/r², and this single fact partitions the solar system.** At Mars (1.52 AU),
590 W/m² — 43% of Earth. At Jupiter (5.20 AU), 50 W/m². Solar becomes impractical roughly beyond
Jupiter; Juno flies enormous arrays and is the outer limit. Beyond that, radioisotope power is not a
preference, it is the only option.

- **RTGs.** ²³⁸Pu, 87.7-year half-life, thermoelectric conversion at only **~6–7% efficiency**.
  MMRTG ≈ **110 W electrical at BOL** from ~2,000 W thermal, decaying ~1.6%/yr. The binding
  constraint is **plutonium supply, not engineering**. The waste heat is a feature — RTG thermal
  output keeps spacecraft warm in the outer solar system.
- **Batteries.** Li-ion at ~100–250 Wh/kg, sized to eclipse duration and peak load, with
  depth-of-discharge traded against cycle life. A LEO spacecraft sees **~16 eclipses/day — about
  90,000 cycles over 15 years**, which forces shallow DoD.
- **Fission.** Kilopower/KRUSTY demonstrated the 1–10 kW class, for surface power where solar duty
  cycle fails: **a lunar night is 14 Earth days, and no practical battery bridges it.**

### Thermal

In vacuum there is no convection. Heat moves by conduction and radiation only, and **radiation is
the only path off the vehicle**:

    Q_rad = εσA(T⁴ − T_sink⁴)

> **THE T⁴ IS BRUTAL.** A radiator at 300 K rejects ~460 W/m²; at 200 K, only ~91 W/m². Rejecting
> heat from a cold instrument therefore costs area out of all proportion to the wattage, which is
> why cryogenic payloads are a structural and geometric problem, not a plumbing one.

The **α/ε ratio** — solar absorptivity over infrared emissivity — is the primary design knob, which
is why thermal control is largely a **coatings** problem. **MLI blankets** (10–30 layers of
aluminized Mylar, effective emissivity ~0.01–0.03) are the single most effective thermal component
on most spacecraft.

The extremes are what break designs. JWST needs its instruments below ~40 K, achieved with a
tennis-court-sized sunshield giving ~300 K of gradient across five layers. Parker Solar Probe
survives ~1,400 °C on a carbon-composite shield while the bus stays near room temperature. The lunar
surface swings ~120 °C to −170 °C, and permanently shadowed craters sit near 25–40 K — colder than
Pluto's surface.
