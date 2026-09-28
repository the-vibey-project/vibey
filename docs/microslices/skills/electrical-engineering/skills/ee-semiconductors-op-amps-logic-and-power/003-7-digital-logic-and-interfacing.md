---
id: skill-7-digital-logic-and-interfacing-655dbae1c7
purpose: 7 digital logic and interfacing
source: src/vibey_tools/skills/plugins/electrical-engineering/skills/ee-semiconductors-op-amps-logic-and-power/SKILL.md
requires: ["skill-6-op-amps-7dec5504cb"]
links: ["skill-8-power-fbfe972514"]
---

## §7. Digital Logic and Interfacing

### 7.1 Logic levels — where the real bugs live
```
V_OH  minimum the driver guarantees as HIGH
V_OL  maximum the driver guarantees as LOW
V_IH  minimum the receiver accepts as HIGH
V_IL  maximum the receiver accepts as LOW
Noise margin = V_OH − V_IH  (high side)   ⚠️ this is what you're actually designing
```
**⚠️ The interoperability trap**: a 3.3 V CMOS output has `V_OH` ≈ 3.0 V, and 5 V TTL
needs `V_IH` = 2.0 V — **that works.** But **5 V CMOS needs `V_IH` = 3.5 V** —
⚠️ **and 3.3 V will not reliably drive it.** **Always compare the actual numbers from both
datasheets; "3.3 V and 5 V are compatible" is not a fact, it's a coincidence that
sometimes holds.**

### 7.2 Level shifting
```
3.3 V → 5 V input     often works directly ⚠️ IF the receiver is TTL-threshold. Verify.
5 V → 3.3 V input     ⚠️ NOT safe unless the pin is 5V-tolerant — check the datasheet
                      Options: resistor divider (slow), series R + clamp diode,
                      dedicated translator IC, or a MOSFET shifter for bidirectional
Bidirectional (I²C)   ⚠️ the classic single-N-FET shifter with pull-ups to each rail
```
**⚠️ Feeding 5 V into a non-tolerant 3.3 V pin doesn't always fail immediately.** The
internal ESD diode conducts into the 3.3 V rail — **it may work, may raise the 3.3 V rail,
and may kill the part slowly.** Intermittent, temperature-dependent, and awful to debug.

### 7.3 Open-drain and buses
**Open-drain/open-collector** can only pull low; a pull-up provides the high.
⚠️ **This enables wired-AND and multi-master buses (I²C), and level shifting for free by
pulling up to the lower rail.**
**⚠️ Pull-up sizing for I²C**: `t_rise ≈ 0.85 · R · C_bus`. The spec caps rise time
(1 µs standard, 300 ns fast mode), so **more bus capacitance demands a smaller resistor**,
which raises current. ⚠️ **The classic "I²C works on the bench and fails with the long
cable" is exactly this.**

### 7.4 Inputs
**⚠️ Never leave a CMOS input floating** — it drifts through the threshold region, both
output transistors conduct, and you get oscillation and heating. **Pull it somewhere.**
**Switch debouncing** — mechanical contacts bounce for **1–50 ms**. ⚠️ **Debounce in
firmware (simplest and most flexible) or with an RC + Schmitt trigger.**
**Protection**: series resistor limits fault current, clamp diodes to the rails,
TVS for ESD (§10 → `ee-signal-integrity-emc-and-pcb-design`).

---
