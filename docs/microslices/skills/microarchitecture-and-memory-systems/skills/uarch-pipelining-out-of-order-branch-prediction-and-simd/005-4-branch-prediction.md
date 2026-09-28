---
id: skill-4-branch-prediction-91d71e6dc6
purpose: 4 branch prediction
source: src/vibey_tools/skills/plugins/microarchitecture-and-memory-systems/skills/uarch-pipelining-out-of-order-branch-prediction-and-simd/SKILL.md
requires: ["skill-3-out-of-order-execution-1711d24fb2"]
links: ["skill-5-execution-units-and-simd-4e3db0260d"]
---

## §4. ⚠️ Branch Prediction

**⚠️ A pipeline must guess where control flow goes, many cycles before it knows.**
```
⚠️ THE STAKES  ⚠️ roughly one in five instructions is a branch, and
   a mispredict costs the full pipeline depth. ⚠️ At 95% accuracy
   a wide deep core loses a large fraction of its throughput —
   which is why modern predictors target 99%+
⚠️ THE PROGRESSION  static → 2-bit saturating counters → ⚠️ TWO-LEVEL
   (global and local history) → tournament/hybrid →
   ⚠️ TAGE (geometric history lengths, the current state of the
   art class) → ⚠️ PERCEPTRON predictors, which are genuinely
   neural and shipping in real silicon
⚠️ ALSO PREDICTED  ⚠️ branch TARGET (BTB), ⚠️ RETURN addresses (a
   dedicated return stack buffer, because returns are highly
   predictable but not by history), and indirect branch targets
   (⚠️ the hardest case — virtual calls and jump tables)
⚠️ THE ALIASING PROBLEM  ⚠️ predictor tables are indexed by hashed
   PC and history, so unrelated branches COLLIDE. ⚠️ This is both
   a performance issue and an attack surface (§19)
```
> **⚠️ GOTCHA — branchless code is not automatically faster.** ⚠️ **A well-predicted branch
> is nearly free, while a conditional move creates a genuine data dependency that always
> costs.** **⚠️ Branchless wins on UNPREDICTABLE branches and loses on predictable ones —
> and which you have is an empirical question, not a stylistic one.**

---
