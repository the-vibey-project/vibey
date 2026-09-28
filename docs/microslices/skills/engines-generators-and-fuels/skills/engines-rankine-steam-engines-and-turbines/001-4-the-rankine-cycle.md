---
id: skill-4-the-rankine-cycle-09e4fc9c1c
purpose: 4 the rankine cycle
source: src/vibey_tools/skills/plugins/engines-generators-and-fuels/skills/engines-rankine-steam-engines-and-turbines/SKILL.md
requires: []
links: ["skill-5-steam-engines-in-detail-5df95aaa2e"]
---

## §4 The Rankine cycle

Virtually all steam engines, from the earliest locomotives to the largest nuclear power plants, run the Rankine cycle. It is the engine that launched the industrial revolution and still the dominant method of generating electricity worldwide.

Everything below is one idea in different clothes — **move heat addition to a HIGHER average temperature, or heat rejection to a LOWER one** (the universal design principle; the Carnot ceiling it serves is §2 → `engines-thermodynamics-and-the-carnot-ceiling`).

### Four components, four processes

| # | Component | Process | What happens | Why it matters |
|---|---|---|---|---|
| 1 | **Pump** | Isentropic compression | Liquid water pressurized from condenser pressure to boiler pressure | Requires very little work — liquid water is nearly incompressible. The smallest energy consumer in the cycle. |
| 2 | **Boiler** | Constant-pressure heat addition | Heat from combustion (or nuclear fission, or concentrated solar) is added: sensible heat to saturation, latent heat to evaporate, and in modern plants superheat beyond saturation | **This is where T_H lives.** |
| 3 | **Turbine (or piston/expander)** | Isentropic expansion | High-pressure, high-temperature steam expands, producing work; pressure and temperature drop | In a condensing engine it expands to a vacuum — and that vacuum matters as much as boiler pressure, because it lowers T_C. |
| 4 | **Condenser** | Constant-pressure heat rejection | Expanded steam is condensed back to liquid at low pressure, rejecting heat to the environment (cooling tower, river, lake, or air-cooled condenser) | **This is where T_C lives.** |

The pump then sends condensed water back to the boiler. The working fluid never leaves the system (a **closed cycle**), which is why steam plants can use highly purified water and avoid scale and corrosion.

### Efficiency and the back-work advantage

    η = (W_turbine − W_pump) / Q_boiler = [(h_3 − h_4) − (h_2 − h_1)] / (h_3 − h_2)

Pump work is typically **only 1–2% of turbine work** — the **back-work ratio is very low**, unlike gas turbines where the compressor consumes 50–65% of turbine output (§9 → `engines-otto-diesel-brayton-stirling-and-combined-cycles`). Pressurizing a liquid is cheap; compressing a gas is expensive. This is the Rankine cycle's key structural advantage.

### The five improvements — how real plants reach 40–45%

Ideal Rankine with saturated steam achieves maybe **25–30%**. Real plants achieve **35–45%** via:

| # | Improvement | Mechanism | Figures |
|---|---|---|---|
| 1 | **Superheat** | Heat steam above saturation after evaporation. Raises the average temperature of heat addition and reduces turbine-exhaust moisture (wet steam erodes blades at high speed — a real engineering limit) | Modern superheaters reach **540–600°C**; ultra-supercritical **620–650°C** |
| 2 | **Reheat** | After partial expansion through the HP turbine, steam returns to the boiler for a reheater pass, then to the IP/LP turbine. Raises average heat-addition temperature and keeps exhaust moisture down | Most large plants use **one or two** reheat stages |
| 3 | **Regenerative feedwater heating** | Steam bled from the turbine at intermediate points preheats feedwater before the boiler. Less heat need be added at low temperature, raising the average temperature of heat addition | A large plant may have **6–8** feedwater heaters. **The single most impactful efficiency improvement after superheat.** |
| 4 | **Supercritical operation** | Above water's critical point (**221 bar, 374°C**) there is no distinct boiling phase; water transitions continuously from liquid-like to gas-like. Eliminates the constant-temperature evaporation step that pins part of the heat addition to a relatively low saturation temperature | Supercritical **42–45%**; ultra-supercritical (**300+ bar, 600–650°C**) **45–47%** |
| 5 | **Condensing at vacuum** | The condenser operates well below atmospheric. Condensing *creates* the vacuum, because water occupies about **1600× less volume** as liquid than vapour. Lowers T_C dramatically | Typically **30–50 mbar absolute** (saturation temperature **25–35°C**) |

> **That the vacuum matters as much as the boiler pressure is the most underappreciated principle in steam
> engineering.**

### Worked comparison — why condensing matters so much

Early steam engines exhausted to atmosphere, so T_C ≈ 100°C at 1 bar. A condensing engine exhausting to 30 mbar rejects heat at about 25°C. With a 600°C (873 K) boiler:

| Exhaust condition | T_C | Carnot ceiling |
|---|---|---|
| Atmospheric exhaust, 1 bar | 373 K (100°C) | 1 − 373/873 = **57%** |
| Condensing to 30 mbar | 298 K (25°C) | 1 − 298/873 = **66%** |

A **16% relative improvement in the ceiling alone** — with no change whatsoever to the hot end.

**James Watt's key invention was the separate condenser**, which gave the vacuum without cooling the cylinder, and it **roughly doubled steam-engine efficiency**.

---
