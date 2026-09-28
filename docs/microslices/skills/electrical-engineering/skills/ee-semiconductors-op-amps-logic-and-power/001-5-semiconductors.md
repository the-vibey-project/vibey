---
id: skill-5-semiconductors-aeef74b472
purpose: 5 semiconductors
source: src/vibey_tools/skills/plugins/electrical-engineering/skills/ee-semiconductors-op-amps-logic-and-power/SKILL.md
requires: []
links: ["skill-6-op-amps-7dec5504cb"]
---

## §5. Semiconductors

### 5.1 Diodes
`V_f` ≈ 0.7 V silicon, **0.2–0.4 V Schottky** (⚠️ **lower drop and faster, but higher
reverse leakage**). **Zener** for voltage reference/clamping. **TVS** for transient
protection (§10 → `ee-signal-integrity-emc-and-pcb-design`). **LED** — ⚠️ **always needs a current limit**: `R = (V_supply − V_f)/I_f`.

**⚠️ The diode applications you must know:**
- **Flyback/freewheeling** across every inductive load (§1 → `ee-fundamentals-components-and-circuit-analysis`) — ⚠️ **omit it and you destroy
  the switch.**
- **Reverse polarity protection** — a series diode (costs `V_f`) or ⚠️ **a P-channel MOSFET
  (near-zero drop, and the better answer).**
- **Rectification** — half-wave, full-wave bridge.
- **Clamping** to rails on inputs.

### 5.2 BJTs
Current-controlled: `I_C = β·I_B`, `V_BE ≈ 0.7 V`.
**Saturation** (fully on, `V_CE(sat)` ≈ 0.2 V) is what you want for switching —
⚠️ **drive the base hard enough: `I_B ≈ I_C/10`, ignoring β, because β varies enormously
part to part and with temperature.**

### 5.3 MOSFETs — the ones you'll actually use
**Voltage-controlled** via `V_GS`. `R_DS(on)` when on.
**⚠️ N-channel switches the low side; P-channel switches the high side.** N-channel is
cheaper and better (lower `R_DS(on)` for the same die) — ⚠️ **which is why high-side
N-channel switching needs a gate driver with a charge pump or bootstrap, since the gate
must go above the rail.**

> **⚠️ GOTCHA — "logic level" is the specification that gets missed.** A standard MOSFET
> may specify `R_DS(on)` at **V_GS = 10 V**. Drive it from a 3.3 V GPIO and it is barely
> on, dissipating heat in the linear region, and it will get hot and fail.
> **⚠️ You need a *logic-level* MOSFET rated at V_GS = 2.5 V or 4.5 V — check the
> `R_DS(on)` at YOUR gate voltage, not the headline number.**

**⚠️ Gate charge matters at speed**: the gate is a capacitor (`Q_g`), so switching fast
needs real current. **A GPIO cannot drive a large power MOSFET quickly** — you get slow
edges, long time in the linear region, and heat. **Use a gate driver.**
**⚠️ Always fit a gate pull-down** (10–100 kΩ) so the FET is off while the MCU is in reset
or unprogrammed — otherwise the load turns on at power-up.

**Body diode** conducts from source to drain — ⚠️ **useful in synchronous rectification,
and a hazard if you didn't expect it (it defeats naive reverse-polarity schemes).**

**GaN and SiC** for high-frequency and high-voltage power — ⚠️ **much faster switching,
and correspondingly much more demanding layout and gate drive.**

### 5.4 Thermal
```
T_junction = T_ambient + P·(θ_JA)
```
**⚠️ `θ_JA` from a datasheet assumes a specific board and copper pour** — it is nearly
always optimistic for your layout. **Derate hard.** Heatsinks, thermal vias, and copper
area are the levers. ⚠️ **Silicon lifetime falls roughly by half for every 10 °C rise**;
running cool is a reliability decision, not an aesthetic one.

---
