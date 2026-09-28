---
id: skill-4-power-system-analysis-e9d8115bb5
purpose: 4 power system analysis
source: src/vibey_tools/skills/plugins/power-engineering/skills/power-system-analysis-and-protection/SKILL.md
requires: []
links: ["skill-5-protection-and-relaying-03fa27ac86"]
---

## §4. Power System Analysis

### 4.1 Power flow (load flow)
**⚠️ The fundamental calculation of the field**: given generation and load, find all bus
voltages and line flows.
```
Bus types:  Slack (V, θ fixed — absorbs the mismatch)
            PV (P, |V| specified — generators)
            PQ (P, Q specified — loads)
```
**⚠️ It's a nonlinear system solved iteratively — Newton-Raphson is the standard**, with
fast-decoupled variants exploiting the physical fact that ⚠️ **P is strongly coupled to
angle and Q to voltage magnitude.** **DC power flow** linearizes it (⚠️ **ignoring
reactive power and losses — fast enough for market clearing, and wrong for voltage
studies**).

**⚠️ Convergence failure is meaningful, not just numerical**: a power flow that won't
converge often indicates a genuinely infeasible operating point — **voltage collapse
territory** — rather than a bad initial guess. **Don't just relax the tolerance.**

### 4.2 State estimation
**⚠️ The measurement layer under everything in §6 → `power-scada-ems-and-protocols`.** Redundant, noisy SCADA measurements
are fitted to the network model by weighted least squares, producing **the best estimate
of the actual system state** and **flagging bad data.**
⚠️ **The control room does not act on raw telemetry; it acts on the state estimate.**
**PMUs (phasor measurement units)** give GPS-time-synchronized voltage and current
phasors at 30–120 Hz, enabling direct wide-area observation.

### 4.3 Fault analysis
**Short circuits — bolted three-phase, line-to-ground (⚠️ most common), line-to-line,
double-line-to-ground.** Analyzed with **symmetrical components** (§1.3 → `power-ac-fundamentals-generation-and-grid`).
**⚠️ You need fault current magnitudes for two reasons**: to size breakers with adequate
**interrupting capacity**, and to set the relays of §5. ⚠️ **Inverter-based resources
break both assumptions — see §8 → `power-inverters-storage-markets-and-datacenters`.**

### 4.4 Stability
```
Rotor angle stability   ⚠️ do generators stay in synchronism after a disturbance?
  transient (large disturbance, first swing, ~seconds)
  small-signal (oscillatory modes, damping)
Frequency stability     does frequency stay in bounds? (§1.4)
Voltage stability       ⚠️ can the system sustain voltage? Collapse is a real,
                        fast, and historically catastrophic failure mode
```
**⚠️ The critical clearing time** — how fast a fault must be removed for the system to
remain stable — **is why protection speed (§5) is a stability requirement, not just an
equipment-protection one.**

---
