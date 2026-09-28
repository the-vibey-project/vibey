---
id: skill-30-method-3429315842
purpose: 30 method
source: src/vibey_tools/skills/plugins/manufacturing-mechanical-engineering-for-software-devs/skills/mfg-reference/SKILL.md
requires: ["skill-29-quick-reference-3b5321079d"]
links: []
---

## §30. Method

**§1–§24 → `mfg-mechanics-stress-fatigue-and-materials`, `mfg-machine-elements-mechanisms-and-tolerances`, `mfg-process-families-machining-additive-and-moulding`, `mfg-dfm-metrology-plm-npi-and-what-transfers` rests on settled mechanics and standard manufacturing practice** — **stress and
fatigue theory, materials science, GD&T as codified in ASME Y14.5, the process families,
DFM/DFA, metrology, and PLM conventions.** ⚠️ **None of it needed verification; Wöhler
characterized fatigue in the 1860s and the volume-versus-process economics has not
changed.**

**Two searches were run in August 2026**, on **additive manufacturing** and **industrial
robotics** — ⚠️ **both chosen because they are the two areas where software people's
expectations diverge most from manufacturing reality, and both now have data rather than
projections.**

**Confidence.** **High** in §8 → `mfg-machine-elements-mechanisms-and-tolerances`, §7 → `mfg-machine-elements-mechanisms-and-tolerances` and §4 → `mfg-mechanics-stress-fatigue-and-materials`, which are the sections I'd most want read.
⚠️ **Tolerance thinking is the single best import from this field into software: nothing is
exact, everything is a distribution, and a design requiring exactness fails.** ⚠️ **Exact
constraint (§7 → `mfg-machine-elements-mechanisms-and-tolerances`) is the second — over-constraint produces conflict rather than robustness,
and the redundant-sources-of-truth analogy is exact.** **§4 → `mfg-mechanics-stress-fatigue-and-materials`'s fatigue framing gives software
a vocabulary for defects that only appear after many cycles.**

**High** in §21 → `mfg-dfm-metrology-plm-npi-and-what-transfers`'s PLM section, and ⚠️ **the interchangeability rule is the part worth
carrying: if the change makes the part non-interchangeable it needs a new identifier, not a
revision — because you cannot recall what already exists.** **That is semantic versioning
with genuinely irreversible consequences.**

**Moderate-to-high** on §25.1. ⚠️ **The AMPOWER 5.6% and Wohlers 15.3% figures and the
78.3% market-share number are attributed to named industry reports and recur across
coverage.** ⚠️ **But essentially all of this space is covered by AM trade press with
commercial interests, so I weighted the sceptical framing — the retrenchment narrative,
the "took too long to focus on customer outcomes" self-criticism, and the plain statement
that AM loses to moulding at volume — over the promotional material.** **⚠️ The 40–60%
weight reduction and 20–30 part consolidation figures come from a vendor blog and are
marked as reported.**

**High** on §25.2's IFR data, which is the field's authoritative source and consistent
across outlets: ⚠️ **542,076 installations in 2024, Asia 74%, US 38,000 in 2025 at +11%,
Korea's density of 1,220, and the US$16.7 billion market value.**
⚠️ **The humanoid framing is deliberately drawn from the IFR's own careful language rather
than from vendor claims** — **the fact that the industry body lists cycle times, energy
consumption, maintenance costs and human-level dexterity as unmet requirements is more
informative than any forecast.** **⚠️ The cobot price and payback figures come from a
marketing site and are indicative only.**
