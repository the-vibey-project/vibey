---
id: skill-11-minimization-8b7ee9f5cc
purpose: 11 minimization
source: src/vibey_tools/skills/plugins/digital-logic-and-firmware-engineering/skills/logic-standard-cells-boolean-minimization-and-arithmetic/SKILL.md
requires: ["skill-10-boolean-algebra-c97637a5eb"]
links: ["skill-12-combinational-building-blocks-018455c32e"]
---

## §11. Minimization

**⚠️ KARNAUGH MAPS** — ⚠️ **a truth table rearranged in GRAY CODE order so that adjacent
cells differ in one variable, making groupings visible.** ⚠️ **Practical to about four
variables, six with effort — ⚠️ and their real value now is TEACHING the structure, not
production optimization.**
**⚠️ Quine-McCluskey** is the systematic tabular method, ⚠️ **and ESPRESSO is the heuristic
that real tools actually use, because exact minimization is NP-hard.**
> **⚠️ GOTCHA — minimal gate count is not the design goal.** ⚠️ **Synthesis optimizes for
> TIMING, area and power together, against a real cell library with real delays.** **⚠️ A
> "minimal" expression on paper may map to a slower circuit than a redundant one — and
> hand-minimizing before synthesis usually makes results worse, not better.**

**⚠️ HAZARDS are the reason redundancy is sometimes deliberately KEPT**: ⚠️ **a static
hazard is a momentary wrong output caused by unequal path delays, and adding a redundant
term can eliminate it.** ⚠️ **This matters in asynchronous logic and for signals feeding
asynchronous inputs; in synchronous logic the flip-flop hides glitches — which is one of
the main reasons synchronous design won.**

---
