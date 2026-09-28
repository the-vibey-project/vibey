---
id: skill-19-quick-reference-5bcd608217
purpose: 19 quick reference
source: src/vibey_tools/skills/plugins/space-exploration/skills/space-reference/SKILL.md
requires: ["skill-18-books-c1214f0b39"]
links: ["skill-20-method-ffa7c6e034"]
---

## §19. Quick Reference

### 19.1 Numbers
```
Solar constant 1,361 W/m² at 1 AU; ∝ 1/r²
Mars 590 W/m² · Jupiter 50 · Saturn 15 · Pluto 0.9

Light time: Moon 1.3 s · Mars 3–22 min · Jupiter 33–53 min · Saturn 68–84 min
Mars synodic period 25.6 months           ⚠️ the scheduling quantum

Solar arrays ~50–150 W/kg · RTG ~2–5 W/kg, ~6–7% efficient, ~1.6%/yr decay
MMRTG ≈ 110 W_e from ~2,000 W_th
Batteries 100–250 Wh/kg

Consumables ~5 kg/person/day open loop
ISS water recovery up to ~93%; Sabatier closes ~50% of the O₂ loop
MOXIE: 12 g O₂/hr peak, ≥98% purity, 15 kg, ~300 W, 800 °C, 16 runs
ISRU energy: Mars SOXE 30–70 kWh/kg O₂ · lunar MRE 3–5 kW/kg · H₂ reduction 2–3 kW/kg

NASA career radiation limit 600 mSv · ESA/Roscosmos 1 Sv
⚠️ Mars mission estimate ~1,000 mSv — exceeds NASA's limit
Bone loss ~1–1.5%/month · SANS in ~70% of >6-month crews

Mars atmosphere ~1% of Earth's, ~95% CO₂
Mars landed mass ceiling historically ~1 tonne
Parachute deploy Mach 1.5–2.2
Lunar night 14 Earth days
```

### 19.2 Picker
| Need | Approach |
|---|---|
| Power inside ~Jupiter | Solar (§3 → `space-power-thermal-comms-and-navigation`) |
| Power beyond Jupiter, or through lunar night | RTG or fission (§3 → `space-power-thermal-comms-and-navigation`) |
| Reject heat | Radiator area, and tune `α/ε` (§4 → `space-power-thermal-comms-and-navigation`) |
| High data volume from a surface | ⚠️ **Relay orbiter, not direct-to-Earth** (§5.4 → `space-power-thermal-comms-and-navigation`) |
| Data rate at extreme range | Ka-band or optical + LDPC coding (§5.2 → `space-power-thermal-comms-and-navigation`) |
| Precise interplanetary navigation | Doppler + ranging + **Delta-DOR** (§6.1 → `space-power-thermal-comms-and-navigation`) |
| Landing in hazardous terrain | **Terrain-relative navigation** (§6.1 → `space-power-thermal-comms-and-navigation`) |
| Large Δv, plenty of time | Electric propulsion (§7 → `space-attitude-propulsion-and-edl`) |
| Orbit insertion, fast | Bipropellant (§7 → `space-attitude-propulsion-and-edl`) |
| ~1 tonne to the Martian surface | Sky crane (§8 → `space-attitude-propulsion-and-edl`) |
| Return propellant from Mars | ⚠️ **ISRU — and size the power plant first** (§10.2 → `space-human-factors-life-support-and-reliability`) |
| GCR shielding | ⚠️ **Hydrogen-rich mass, not aluminium** (§11 → `space-human-factors-life-support-and-reliability`) |
| Landing near a special region | ⚠️ **Category IV sterilization** (§13 → `space-human-factors-life-support-and-reliability`) |

### 19.3 Design checklist
- [ ] Mass, power, data, Δv margins per §14.1 → `space-human-factors-life-support-and-reliability` — and are they still intact?
- [ ] Link budget closed at maximum range, worst geometry (§5.1 → `space-power-thermal-comms-and-navigation`)
- [ ] Data volume, not just data rate, closes against the science plan (§5.2 → `space-power-thermal-comms-and-navigation`)
- [ ] Thermal closes at both hot and cold extremes, BOL and EOL (§4 → `space-power-thermal-comms-and-navigation`)
- [ ] Power closes at EOL, worst eclipse, worst dust (§3 → `space-power-thermal-comms-and-navigation`)
- [ ] Every deployment identified as a single-point failure (§14.2 → `space-human-factors-life-support-and-reliability`)
- [ ] Safe mode is survivable indefinitely and Earth-pointed (§6.2 → `space-power-thermal-comms-and-navigation`)
- [ ] Fault protection cannot fire during a critical event (§6.2 → `space-power-thermal-comms-and-navigation`)
- [ ] Autonomy sufficient for the light-time (§5.3 → `space-power-thermal-comms-and-navigation`)
- [ ] Radiation total-dose budget closes for the environment (§11 → `space-human-factors-life-support-and-reliability`)
- [ ] Planetary protection category identified and costed (§13 → `space-human-factors-life-support-and-reliability`)
- [ ] Units checked at every interface ⚠️ (§14.2 → `space-human-factors-life-support-and-reliability`)

---
