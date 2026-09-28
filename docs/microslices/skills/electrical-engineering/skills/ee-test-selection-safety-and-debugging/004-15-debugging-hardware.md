---
id: skill-15-debugging-hardware-4fc0818311
purpose: 15 debugging hardware
source: src/vibey_tools/skills/plugins/electrical-engineering/skills/ee-test-selection-safety-and-debugging/SKILL.md
requires: ["skill-14-safety-41d60f128d"]
links: []
---

## §15. Debugging Hardware

**⚠️ The sequence, and it's deliberately unglamorous:**
```
0. ⚠️ POWER OFF and inspect. Backwards parts, solder bridges, cold joints, missing
   components, wrong values. Use magnification. This finds a large share of faults
   before you power anything.
1. Check the rails — ⚠️ EVERY rail, at the load, under load, with a scope not just a DMM.
   Ripple and droop don't show on a multimeter.
2. Current draw sane? ⚠️ Use a current-limited bench supply on first power-up. Way too
   high = short. Way too low = it isn't running.
3. Thermal check — hand or camera. ⚠️ A hot part is a found fault.
4. Clocks and resets present and correct? ⚠️ Nothing else matters if these are wrong.
5. Signals — scope them. Levels, edges, timing. Compare against the datasheet.
6. Bisect: half the circuit at a time. Inject a known-good signal; remove sections.
7. Compare to a known-good board if one exists — ⚠️ the fastest method when available.
```

**⚠️ The rules that keep you honest:**
- **Change one thing at a time.** Under pressure this is the first discipline to go.
- **⚠️ Suspect your measurement setup before you suspect physics.** Probe compensation,
  ground lead, meter mode, and where you clipped the ground are the usual culprits (§12).
- **Connectors, cables, and solder joints first** — ⚠️ **they fail far more often than
  silicon.**
- **⚠️ "It works when I touch it" means a bad joint or a floating input** (§7.4 → `ee-semiconductors-op-amps-logic-and-power`).
- **⚠️ "It works when the lid is off" means thermal.**
- **⚠️ "It fails only at high load" means power delivery, not logic.**
- **⚠️ "It fails only with the long cable" means signal integrity or bus capacitance**
  (§7.3 → `ee-semiconductors-op-amps-logic-and-power`, §9 → `ee-signal-integrity-emc-and-pcb-design`).
- **Write down what you changed and what happened.** You will not remember.
