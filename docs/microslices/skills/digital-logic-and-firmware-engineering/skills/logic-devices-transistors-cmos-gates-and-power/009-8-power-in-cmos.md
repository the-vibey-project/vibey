---
id: skill-8-power-in-cmos-7175d37001
purpose: 8 power in cmos
source: src/vibey_tools/skills/plugins/digital-logic-and-firmware-engineering/skills/logic-devices-transistors-cmos-gates-and-power/SKILL.md
requires: ["skill-7-other-logic-families-2091a99b66"]
links: []
---

## §8. ⚠️ Power in CMOS

```
⚠️ ⚠️ DYNAMIC POWER  P = α · C · V² · f
   ⚠️ α = ACTIVITY FACTOR (fraction of cycles the node switches)
   ⚠️ THE V² TERM is why voltage scaling was the most powerful
   lever ever available — and why its end mattered so much
   (see a semiconductor reference §5)
⚠️ SHORT-CIRCUIT POWER  ⚠️ during a transition BOTH networks are
   briefly partially on. ⚠️ Small if edges are fast, and it
   grows badly with slow edges (§4)
⚠️ ⚠️ STATIC / LEAKAGE POWER  ⚠️ subthreshold conduction, gate
   oxide tunnelling, junction leakage. ⚠️ Negligible in old
   processes, MAJOR in modern ones — and it rises sharply with
   temperature, creating a THERMAL RUNAWAY risk
⚠️ THE TECHNIQUES
   ⚠️ CLOCK GATING  ⚠️ the highest-value one — the clock network
      itself switches every cycle and can be a large fraction of
      dynamic power
   ⚠️ POWER GATING  cut supply to idle blocks, attacking leakage
   ⚠️ MULTI-Vt  ⚠️ high-Vt cells on non-critical paths (slow,
      low leakage), low-Vt only where speed is needed
   ⚠️ DVFS · multiple voltage domains with level shifters ·
      operand isolation
⚠️ ⚠️ THE GLITCH PROBLEM  ⚠️ unbalanced path delays cause spurious
   transitions that do real work and burn real power before
   settling — ⚠️ a meaningful fraction of dynamic power in
   arithmetic-heavy logic
```
