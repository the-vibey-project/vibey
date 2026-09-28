---
id: skill-2-real-components-313b1689b7
purpose: 2 real components
source: src/vibey_tools/skills/plugins/electrical-engineering/skills/ee-fundamentals-components-and-circuit-analysis/SKILL.md
requires: ["skill-1-fundamentals-01b33fcac1"]
links: ["skill-3-dc-analysis-580757f7af"]
---

## §2. Real Components

**⚠️ This section is the one that catches software people out.** The schematic symbol is a
lie of convenience.

### 2.1 Resistors
Real = R + series L + parallel C. **Tolerance** (1% is standard and cheap; 5% for
non-critical), **power rating** (⚠️ **derate to ~50% of rated dissipation for reliability
and temperature**), **temperature coefficient (ppm/°C)**.
**⚠️ Pull-up sizing is a real trade**: too high and noise or leakage wins and edges are
slow; too low and you waste current and stress the driving pin. **10 kΩ is the lazy
default; I²C at 400 kHz typically wants 2.2–4.7 kΩ** because the bus capacitance and the
required rise time set it (§7.3 → `ee-semiconductors-op-amps-logic-and-power`).

### 2.2 Capacitors — and the one that surprises everyone
| Type | Use | ⚠️ Notes |
|---|---|---|
| **Ceramic X7R/X5R** | Decoupling, general | ⚠️ **See the DC bias gotcha below** |
| **Ceramic C0G/NP0** | Timing, filters, precision | Stable, small values only |
| **Ceramic Y5V/Z5U** | ⚠️ **Avoid** | Terrible tempco and bias behaviour |
| **Electrolytic** | Bulk energy storage | ⚠️ **Polarized. Dries out. Finite life, worse hot** |
| **Tantalum** | Compact bulk | ⚠️ **Fails SHORT and can ignite. Derate voltage 50%+** |
| **Film** | Audio, precision, high current | Bulky, excellent |

> **⚠️ GOTCHA — a ceramic capacitor loses most of its capacitance under DC bias.**
> An X5R rated 10 µF at 6.3 V, operated at 5 V, may deliver **2 µF or less.** The
> derating is worse in smaller packages for the same value. ⚠️ **Datasheets bury this in a
> bias-vs-capacitance curve, and it is the reason a decoupling network that looks right on
> the schematic doesn't work on the bench.** **Check the curve, and use a higher voltage
> rating or a larger package than you think you need.**

**⚠️ ESR and ESL are the parameters that matter for decoupling**, not the capacitance
alone. Every capacitor self-resonates at `f = 1/(2π√(LC))`; **above that it is
inductive and no longer a capacitor** (§9.3 → `ee-signal-integrity-emc-and-pcb-design`).

### 2.3 Inductors and ferrites
**Saturation current** — ⚠️ **above it, inductance collapses and current rises without
limit.** **This is the failure mode in switching supplies**, and it's why you size for
peak, not average. **DCR** costs efficiency. **Ferrite beads** are lossy resistors at RF,
specified in **Ω at 100 MHz, not henries** — ⚠️ **and putting one in a power rail with a
big cap after it makes an LC resonant tank that can *amplify* noise at the resonant
frequency.**

### 2.4 Wires, traces, connectors
**⚠️ Every conductor has inductance — roughly 1 nH per mm.** At high `di/dt`, that
matters: 10 nH with a 100 mA/ns edge gives 1 V of ground bounce.
**Trace resistance and current capacity**: 1 oz copper, 10 mil trace ≈ 0.05 Ω/inch;
⚠️ **use an IPC-2221 calculator rather than guessing.**
**⚠️ Connectors and cables are the most common physical failure point** — flex, corrosion,
and contact resistance. **Suspect them early** (§15 → `ee-test-selection-safety-and-debugging`).

---
