---
id: skill-19-quick-reference-46c6c1fcfc
purpose: 19 quick reference
source: src/vibey_tools/skills/plugins/electrical-engineering/skills/ee-reference/SKILL.md
requires: ["skill-18-books-cde493c143"]
links: ["skill-20-method-15f2fe0645"]
---

## §19. Quick Reference

### 19.1 Equations
```
V = IR · P = VI = I²R = V²/R
I = C·dV/dt · V = L·di/dt          ⚠️ the two that explain most surprises
V_out = V_in · R₂/(R₁+R₂)          ⚠️ unloaded only
Z_L = jωL · Z_C = 1/(jωC) · ω = 2πf
f_c = 1/(2πRC) · τ = RC · f₀ = 1/(2π√(LC))
f_knee ≈ 0.35/t_rise               ⚠️ the spectrum of a digital edge
Γ = (Z_L − Z₀)/(Z_L + Z₀)          reflection
T_j = T_a + P·θ_JA                 ⚠️ θ_JA is optimistic
R_LED = (V_supply − V_f)/I_f
dB = 20log₁₀(V₁/V₂) = 10log₁₀(P₁/P₂)
t_rise(I²C) ≈ 0.85·R·C_bus
```

### 19.2 Picker
| Need | Use |
|---|---|
| Step down, efficiency matters | **Buck** (§8.1 → `ee-semiconductors-op-amps-logic-and-power`) |
| Step down, small drop, quiet rail | **LDO** (§8.1 → `ee-semiconductors-op-amps-logic-and-power`) |
| Switch a load from a 3.3 V GPIO | ⚠️ **Logic-level MOSFET + gate pull-down** (§5.3 → `ee-semiconductors-op-amps-logic-and-power`) |
| Switch a high-side load | P-channel, or N-channel + gate driver (§5.3 → `ee-semiconductors-op-amps-logic-and-power`) |
| Drive an inductive load | ⚠️ **Add the flyback diode** (§1 → `ee-fundamentals-components-and-circuit-analysis`) |
| Buffer a high-impedance node | **Op-amp follower** (§6 → `ee-semiconductors-op-amps-logic-and-power`) |
| Compare two voltages | ⚠️ **Comparator with hysteresis** (§6 → `ee-semiconductors-op-amps-logic-and-power`) |
| Amplify a sensor bridge | **Instrumentation amp** (§6 → `ee-semiconductors-op-amps-logic-and-power`) |
| Convert 5 V logic to 3.3 V | ⚠️ **Translator IC, or divider if slow** (§7.2 → `ee-semiconductors-op-amps-logic-and-power`) |
| Bidirectional level shift (I²C) | **N-FET shifter + pull-ups** (§7.2 → `ee-semiconductors-op-amps-logic-and-power`) |
| Clean up a noisy digital input | **RC + Schmitt**, or debounce in firmware (§7.4 → `ee-semiconductors-op-amps-logic-and-power`) |
| Protect a connector from ESD | **TVS at the connector** (§10 → `ee-signal-integrity-emc-and-pcb-design`) |
| Local transient current for an IC | **100 nF at the pin, minimal loop** (§9.3 → `ee-signal-integrity-emc-and-pcb-design`) |
| Stop ringing on a fast point-to-point trace | **Series termination at the source** (§9.2 → `ee-signal-integrity-emc-and-pcb-design`) |
| Find a short | ⚠️ **Current-limited supply + thermal camera** (§12.3 → `ee-test-selection-safety-and-debugging`, §15 → `ee-test-selection-safety-and-debugging`) |
| Debug a protocol | **Logic analyzer, not a scope** (§12.3 → `ee-test-selection-safety-and-debugging`) |
| Measure a fast edge honestly | ⚠️ **10× probe, compensated, spring ground** (§12.2 → `ee-test-selection-safety-and-debugging`) |

### 19.3 First-power-up checklist
- [ ] Visual inspection under magnification — polarity, bridges, wrong values? (§15 → `ee-test-selection-safety-and-debugging`)
- [ ] Bench supply **current limit set** before connecting? (§12.3 → `ee-test-selection-safety-and-debugging`)
- [ ] Rails checked for shorts to ground with a meter, power off?
- [ ] Power up slowly; watch current draw against expectation (§15 → `ee-test-selection-safety-and-debugging`)
- [ ] Every rail at the correct voltage, **at the load, under load, on a scope**? (§15 → `ee-test-selection-safety-and-debugging`)
- [ ] Thermal check — anything hot? (§15 → `ee-test-selection-safety-and-debugging`)
- [ ] Clocks and resets present? (§15 → `ee-test-selection-safety-and-debugging`)
- [ ] Only then: does the firmware run?

---
