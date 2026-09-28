---
id: skill-17-numbers-7486a122f7
purpose: 17 numbers
source: src/vibey_tools/skills/plugins/electrical-engineering/skills/ee-reference/SKILL.md
requires: ["skill-16-anti-patterns-b8125847db"]
links: ["skill-18-books-cde493c143"]
---

## §17. Numbers

```
FUNDAMENTALS
Si diode V_f 0.6–0.7 V · Schottky 0.2–0.4 V · LED 1.8 V (red) to 3.4 V (blue/white)
BJT V_BE 0.7 V · V_CE(sat) ~0.2 V · drive I_B ≈ I_C/10
⚠️ Logic-level MOSFET: check R_DS(on) at YOUR V_GS

LOGIC LEVELS
3.3 V CMOS: V_OH ≥2.4 · V_OL ≤0.4 · V_IH ≥2.0 · V_IL ≤0.8
5 V TTL:    V_IH ≥2.0  ⚠️ (3.3 V drives this)
5 V CMOS:   V_IH ≥3.5  ⚠️ (3.3 V does NOT reliably drive this)

TIME AND FREQUENCY
τ = RC · 63% in 1τ · ~99% in 5τ · f_c = 1/(2πRC)
⚠️ f_knee ≈ 0.35/t_rise  · −3 dB = half POWER (half voltage = −6 dB)
FR4 propagation ~6 in/ns (~150 ps/inch)
⚠️ Transmission-line territory above ~1–2 inches for ns edges

PHYSICAL
Trace/wire inductance ~1 nH/mm · Via ~1 nH
1 oz copper 10 mil trace ≈ 0.05 Ω/inch
Z₀ typical: 50 Ω single-ended, 90–100 Ω differential
Decoupling: 100 nF per power pin + bulk 10–100 µF per region

POWER
Li-ion 4.2 V full / 3.7 nominal / 3.0 empty ⚠️ (40% swing)
LiFePO₄ 3.2 V · Alkaline 1.5 V · NiMH 1.2 V
LDO efficiency = V_out/V_in · Switching 85–95%
⚠️ Derate: power 50%, tantalum voltage 50%+, silicon life halves per +10 °C

SAFETY ⚠️
1 mA perception · 10 mA let-go · 30 mA respiratory · 100 mA fibrillation
Dry skin ~100 kΩ · wet ~1 kΩ  ⚠️ 120 V across 1 kΩ = 120 mA

MEASUREMENT
Scope bandwidth ≥3–5× signal knee frequency · sample rate ≥5× bandwidth
10× probe: 10 MΩ, ~10 pF · 1× probe: 1 MΩ, ~100 pF ⚠️
DMM input ~10 MΩ
I²C pull-ups: 10 kΩ lazy default; 2.2–4.7 kΩ at 400 kHz
Switch bounce 1–50 ms
```

---
