---
id: skill-6-op-amps-7dec5504cb
purpose: 6 op amps
source: src/vibey_tools/skills/plugins/electrical-engineering/skills/ee-semiconductors-op-amps-logic-and-power/SKILL.md
requires: ["skill-5-semiconductors-aeef74b472"]
links: ["skill-7-digital-logic-and-interfacing-655dbae1c7"]
---

## §6. Op-Amps

**⚠️ The two golden rules (for an ideal op-amp with negative feedback):**
1. **No current flows into the inputs.**
2. **The output does whatever it takes to make `V+ = V−`.**

**⚠️ Rule 2 only holds with negative feedback and within the output's ability.** Remove the
feedback and it's a comparator; exceed the rails and it clips.

**The standard configurations:**
```
Buffer/follower     gain 1 ⚠️ — impedance conversion, and the fix for a loaded divider (§1)
Inverting           −R_f/R_in
Non-inverting       1 + R_f/R_in     ⚠️ minimum gain 1
Differential        amplifies (V₂−V₁), rejects common mode
Instrumentation     ⚠️ high input Z + high CMRR — the right choice for sensor bridges
Integrator / Differentiator
Comparator          ⚠️ use an actual comparator, not an op-amp
Sallen-Key          active filter (§4)
Transimpedance      current → voltage (photodiodes)
```

**⚠️ Real op-amp limits that break designs:**
- **Input offset voltage** — matters at high gain.
- **Bias current** — ⚠️ **flows through your source impedance and becomes an error
  voltage.**
- **Slew rate** (V/µs) — ⚠️ **large-signal bandwidth is limited by this, not by GBW.**
- **Gain-bandwidth product** — ⚠️ **available gain falls with frequency: GBW/gain = usable
  bandwidth.**
- **Rail-to-rail?** ⚠️ **Most op-amps cannot swing to their rails, and many cannot accept
  inputs at the rails.** Check both input and output specs separately.
- **⚠️ Capacitive loading causes oscillation.** Adding a cap on an op-amp output to "clean
  it up" is a classic way to make it ring.

**⚠️ Comparators need hysteresis.** Without it, a slowly-crossing noisy input produces
multiple transitions — **the analogue of switch bounce, and it produces the same class of
mysterious multiple-interrupt bugs.** Add positive feedback (Schmitt trigger).

---
