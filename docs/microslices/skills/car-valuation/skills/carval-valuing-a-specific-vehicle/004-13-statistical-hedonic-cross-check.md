---
id: skill-13-statistical-hedonic-cross-check-08977b682c
purpose: 13 statistical hedonic cross check
source: src/vibey_tools/skills/plugins/car-valuation/skills/carval-valuing-a-specific-vehicle/SKILL.md
requires: ["skill-12-time-season-and-the-asking-to-sale-gap-0a97015647"]
links: ["skill-14-guides-special-vehicle-types-and-collectors-f4d4228a4b"]
---

## §13. Statistical (Hedonic) Cross-Check

**Model:** `ln(price) = b0 + b1·age + b2·(miles/10k) + b3·condition + b4·accidents + b5·owners + b6·months + trim dummies`. Use **one model/generation** at a time.

**When:** 50+ comparable observations. **Checks:** hold-out error (MdAPE), residual patterns (a trim or a region the model misses), sign/size sanity (older → lower, higher miles → lower, condition → higher), **treat active listings consistently** (deflate asks or include a status dummy).
**Limits:** it cannot see paint/interior quality, rust, maintenance history, modifications or cosmetic damage unless captured in your condition score; a *well-specified* model in a simulation outperforms reality. **Use it as a cross-check on comps, never alone.**

---
