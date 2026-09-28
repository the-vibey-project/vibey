---
id: skill-19-engine-management-and-forced-induction-17f5911b32
purpose: 19 engine management and forced induction
source: src/vibey_tools/skills/plugins/engines-generators-and-fuels/skills/engines-rebuilding-engines-materials-and-tolerances/SKILL.md
requires: ["skill-18-engine-anatomy-and-the-rebuild-process-c525d46130"]
links: ["skill-20-materials-manufacturing-and-tolerances-f7ed44b9ed"]
---

## §19 Engine management and forced induction

### The ECU feedback loop

The ECU's core job is to maintain air-fuel ratio near **stoichiometric (~14.7:1 for petrol)** because
the three-way catalyst only works in that narrow window (§17 → `engines-fuels-and-combustion`).

The loop: upstream O₂ sensor reads exhaust oxygen → ECU adjusts injector pulse width → **short-term
fuel trim (STFT)** swings moment to moment → **long-term fuel trim (LTFT)** learns the persistent
correction.

**Reading fuel trims is the core diagnostic skill.**

| Trim sign | What the ECU is doing | What it is seeing |
|---|---|---|
| **Positive** trim | Adding fuel | It sees **lean** |
| **Negative** trim | Removing fuel | It sees **rich** |

The **pattern of trim vs load** tells you the cause.

### Open loop vs closed loop

- **Open loop** — cold start, wide-open throttle, some failure modes: the ECU runs from a table,
  ignoring the O₂ sensor.
- **Closed loop** — warm, part throttle: the ECU uses feedback.

**Some faults only appear once the engine warms and closes the loop, which is why a test drive with
live data matters more than a cold idle scan.**

### Forced induction

**Turbochargers** use exhaust energy that would otherwise be wasted to compress intake air. More air →
more fuel → more power from the same displacement. Intercooling cools the compressed air (heated by
compression), increasing its density. A wastegate controls boost pressure.

**Superchargers** are driven directly by the crankshaft (belt or gears), so they respond instantly but
consume engine power (parasitic loss). Turbos have lag — time for exhaust flow to spin up the turbine
— but are more efficient because they use energy that would otherwise be wasted.

**Knock is the key limitation.** More boost means higher effective compression, so turbo engines often
have **lower static compression ratios** and require **higher-octane fuel**. Knock as a phenomenon —
auto-ignition of the end gas ahead of the flame front, and why it is a fuel chemistry problem rather
than a mechanical design problem — is covered at §7 → `engines-otto-diesel-brayton-stirling-and-combined-cycles`;
octane and cetane ratings at §15 → `engines-fuels-and-combustion`.
