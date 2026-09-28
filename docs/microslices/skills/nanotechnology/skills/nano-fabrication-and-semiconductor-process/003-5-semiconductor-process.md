---
id: skill-5-semiconductor-process-4b8a6a5e49
purpose: 5 semiconductor process
source: src/vibey_tools/skills/plugins/nanotechnology/skills/nano-fabrication-and-semiconductor-process/SKILL.md
requires: ["skill-4-bottom-up-synthesis-and-self-assembly-42e4a1d919"]
links: []
---

## §5. Semiconductor Process

**[VERSIONED — §14.1 → `nano-reference` dates this. This is the nanotechnology that built your computer.]**

### 5.1 What "2nm" actually means

> **⚠️ GOTCHA — the node name is not a measurement.** "2nm" is **a marketing and
> generational label rather than a literal measurement of any single feature size.** It
> denotes the process generation after 3nm, characterized primarily by contacted gate
> pitch and metal pitch. ⚠️ **No feature on a 2nm chip is 2 nm.** Gate lengths are more
> like 12–18 nm. **Comparing nodes across foundries by name alone is meaningless** —
> compare transistor density, performance, and power.

### 5.2 The transistor evolution
```
Planar MOSFET     → gate controls the channel from ONE side
                    ⚠️ short-channel effects and leakage killed it below ~28 nm
FinFET (~22 nm)   → vertical fin, gate on THREE sides
                    ⚠️ ran out of road: fin height/width limits and quantized widths
GAA nanosheet     → ⚠️ gate wraps ALL FOUR sides of stacked horizontal sheets
                    Better electrostatic control, lower leakage, and — importantly —
                    ⚠️ continuously TUNABLE channel width (vs FinFET's quantized fins)
CFET (future)     → stack n- and p-type devices vertically
```
**⚠️ Why GAA was necessary**: as channels shorten, the drain starts to compete with the
gate for control of the channel, and leakage rises. **Wrapping the gate completely
restores electrostatic control.** Fabricating it requires **ALD to deposit high-k
dielectric and metal gate uniformly into the gaps between suspended nanosheets** (§3) —
⚠️ **which is why ALD is load-bearing for the whole node.**

**Backside power delivery** — ⚠️ **the other major architectural change, and the reason is
a genuine conflict**: in a conventional stack, the metal layers above the transistors carry
**both signals and power, and the two compete for the same tracks.** Power wants fat
low-resistance lines; signals want density. **At low voltage this shows up as IR drop and
dynamic droop — the transistor doesn't get the voltage the timing analysis assumed.**
**Moving power to the wafer's back frees the frontside entirely for signal routing.**

**High-NA EUV** — NA 0.55 vs 0.33. ⚠️ **The business case is replacing costly
multi-patterned layers with cleaner single-exposure steps**, not resolution for its own
sake. **It is a later overlay-and-pitch tool, and it is not what makes a nanosheet wrap** —
first-generation GAA does not depend on it.

### 5.3 ⚠️ Why this matters to a software engineer
**Dennard scaling ended around 2005** — power density stopped falling with feature size,
which ended frequency scaling and forced multicore. **Moore's Law in the density sense
continues; the free-lunch performance sense died two decades ago.**

**What replaced it**: **architectural specialization** (GPUs, TPUs, accelerators),
**advanced packaging and chiplets** (⚠️ **2.5D/3D integration, because moving data between
dies is now cheaper than making one bigger die yield**), and **design-technology
co-optimization** — ⚠️ **the node and the design rules are now developed together, which is
why "just port it to the new node" stopped working.**

**⚠️ And the practical consequence for code**: performance now comes from data movement, not
arithmetic. **The energy to move a word across a chip exceeds the energy to compute on it
by orders of magnitude** — which is why locality, blocking, and memory hierarchy dominate
optimization, and why that will not reverse.
