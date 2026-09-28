---
id: skill-20-method-bd9500d451
purpose: 20 method
source: src/vibey_tools/skills/plugins/flight-software/skills/flightsw-reference/SKILL.md
requires: ["skill-19-quick-reference-399a294531"]
links: []
---

## §20. Method

**This is engineering practice, not reporting.** §1–§3 → `flightsw-architecture-languages-and-standards`, §5–§16 → `flightsw-processors-radiation-and-real-time`, `flightsw-fdir-time-telemetry-and-updates`, `flightsw-gnc-verification-ground-and-autonomy` and §19 rest on the
standard sources — **Holzmann's Power of 10 and the JPL coding standard, MISRA C:2012,
NPR 7150.2, DO-178C, the ECSS software standards, the CCSDS Blue Books, Liu & Layland,
Leveson, and the published NASA anomaly and lessons-learned literature.** None of that has
a currency dependency and none was web-verified; the standards are the authority and they
change on multi-year cycles.

**Deliberately scoped to complement**: this supersedes and expands the compressed
flight-software material in a robotics-software reference; spacecraft systems engineering
(power, thermal, link budgets, EDL) is in a space-exploration reference; launch and orbital
physics in a rocket-science reference.

**Two searches were run in August 2026**, confined to the two things that genuinely moved:
**framework releases** (§2.2 → `flightsw-architecture-languages-and-standards`) and **flight processors** (§4 → `flightsw-processors-radiation-and-real-time`).

**Sources for those**: **NASA Goddard's cFS pages and the 2026 cFS Symposium reporting**,
plus **SpaceNews** coverage of the Symposium, for the Draco/QNX and Gov Alpha details and
the mission-count and Gateway claims; **NASA's own "Hello Universe" release**, the
**Microchip PIC64-HPSC product documentation**, and **JPL reporting via SpaceDaily** for
HPSC's specifications and test status; the **JPL/NASA F Prime documentation** and
**SmallSat Conference papers** for F Prime heritage and the published cFS/F Prime
comparison; and a **2024 arXiv paper (Seidel & Beier)** plus a 2026 industry assessment for
the Rust position.

**Confidence.** **High** in §1–§3 → `flightsw-architecture-languages-and-standards`, §5–§16 → `flightsw-processors-radiation-and-real-time`, `flightsw-fdir-time-telemetry-and-updates`, `flightsw-gnc-verification-ground-and-autonomy` — established practice, and the case studies in
§16 → `flightsw-gnc-verification-ground-and-autonomy` are among the most thoroughly documented failures in engineering. **High** in §2.2 → `flightsw-architecture-languages-and-standards`'s
cFS description and §4 → `flightsw-processors-radiation-and-real-time`'s HPSC specifications, which come from NASA and Microchip directly.

⚠️ **Deliberately hedged in two places.** **The HPSC "500×" figure**: I have stated
explicitly that it is **an early indication from an active test programme against a 100×
program goal, that qualification is incomplete, and that no first mission is named** —
because the secondary coverage repeatedly presents it as a delivered capability, and
⚠️ **several of the sources reporting it are aggregators rather than primary.** **Design
against RAD750/RAD5545-class hardware today.** And **§3.2 → `flightsw-architecture-languages-and-standards`'s Rust position**: ⚠️ **the "highest-leverage
language to learn" characterization comes from a training-industry source with an obvious
incentive to say so** — I have kept the claim but attributed its character. **The
underlying adoption picture — real interest, immature qualification, partial-rewrite
strategy — is corroborated by the peer-reviewed work.**

**§17.1 is engineering judgement**, and the Rust/C and COTS/rad-hard questions in
particular are live disagreements among people with more flight heritage than I have
synthesized here.
