---
id: skill-12-generator-theory-fa328f21c3
purpose: 12 generator theory
source: src/vibey_tools/skills/plugins/engines-generators-and-fuels/skills/engines-generators-and-house-power/SKILL.md
requires: []
links: ["skill-13-generator-types-and-ac-vs-dc-generation-f459a291ca"]
---

## §12 Generator theory

### Faraday's law and the minus sign

    EMF = −dΦ/dt

A changing magnetic flux Φ through a loop induces a voltage. The minus sign (Lenz's law) means the induced current **opposes** the change — conservation of energy in disguise. If it reinforced instead, you would have a runaway energy source.

**Three ways to change the flux:** change field strength, change loop area, or change loop orientation relative to the field. All three are used in real machines; **the most common is changing orientation** — rotating a coil in a magnetic field.

### The EMF equation and the RPM → Hz consequence

    EMF = N · B · A · ω · sin(ωt)

N = turns, B = field strength, A = coil area, ω = angular velocity. Output is sinusoidal AC. Frequency f = ω/(2π), so a 2-pole machine at **3,600 RPM produces 60 Hz**; at **3,000 RPM, 50 Hz**. This single relationship is why the whole of §14 keeps returning to shaft speed.

### Back-EMF and why speed droops under load

A motor's back-EMF opposes its supply voltage:

    current drawn = (V_supply − back-EMF) / winding_resistance

A generator runs the other way round: the induced EMF drives current **into the load**, and that
current in the machine's own field produces an **electromagnetic torque opposing the prime mover**.
That opposing torque is the load, mechanically speaking — it is how electrical power out becomes
shaft power in. Draw more current and the opposing torque rises, so the prime mover slows and
frequency falls with it, unless the governor (or an electronic inverter) puts in more input power to
hold speed. (Governor and droop: §22 → `engines-safety-and-reference`.)

### The four real loss mechanisms

Four categories; core loss splits into two sub-mechanisms.

| Loss | What it is |
|---|---|
| Copper losses | I²R in the windings |
| Core loss — hysteresis | Energy lost per magnetization cycle, proportional to the area of the B-H loop |
| Core loss — eddy currents | Circulating currents induced in the core iron, **suppressed by laminating the core** |
| Friction and windage | Mechanical drag on the rotating assembly |
| Excitation losses | Power consumed producing the magnetic field in wound-field machines |

Generator efficiency is typically **90–98% above a few kW**.
