---
id: skill-20-method-ffa7c6e034
purpose: 20 method
source: src/vibey_tools/skills/plugins/space-exploration/skills/space-reference/SKILL.md
requires: ["skill-19-quick-reference-5bcd608217"]
links: []
---

## §20. Method

**This is engineering, not reporting.** §1–§8 → `space-mission-architecture-and-trajectory`, `space-power-thermal-comms-and-navigation`, `space-attitude-propulsion-and-edl`, §11–§14 → `space-human-factors-life-support-and-reliability` rest on the standard systems
literature — **SMAD, Fortescue, Brown, the Gilmore thermal handbook, and the NASA Systems
Engineering Handbook** — plus physics established elsewhere; none of it has a currency
dependency and none of it was web-verified. **Deliberately scoped to complement rather than
duplicate**: launch, staging, orbital mechanics and reentry heating are in a rocket-science
reference; flight software practice is in a robotics-software reference.

**Two searches were run in August 2026**, confined to the two areas where hard numbers have
landed and where the constraint is genuinely binding: **human radiation limits and SANS**
(§9 → `space-human-factors-life-support-and-reliability`), and **ISRU and life-support performance** (§10 → `space-human-factors-life-support-and-reliability`).

**Primary and near-primary sources for those sections**: **NASA's own MOXIE mission-completion
reporting** and the **Science Advances** MOXIE paper (Hoffman, Hecht et al.) for the
12 g/hr, ≥98% purity, 16-run figures and the instrument parameters; the **PDS MOXIE
instrument page** for the warm-up/production duty cycle and the ~650 W·h allocation; a
2026 **ScienceDirect ECLSS review** for the comparative ISRU energy costs; **NASA's ECLSS
page** and a 2026 **Water Resources Research** review for the ~93% water recovery figure;
**NASA's Human Research Roadmap** and peer-reviewed SANS literature (Lee et al. and
successors) for §9.2 → `space-human-factors-life-support-and-reliability`; and multiple peer-reviewed sources plus the **NASA 2022 standard**
for the 600 mSv career limit and the ~1,000 mSv Mars estimate.

**Confidence.** **High** in §1–§8 → `space-mission-architecture-and-trajectory`, `space-power-thermal-comms-and-navigation`, `space-attitude-propulsion-and-edl` and §11–§14 → `space-human-factors-life-support-and-reliability` — settled subsystem engineering with
numbers that are representative sizing values rather than specifications; treat the ranges
as design guidance. **High** in §10.2 → `space-human-factors-life-support-and-reliability`'s MOXIE figures, which come from NASA and the
instrument team directly. **High** in §9.1 → `space-human-factors-life-support-and-reliability`'s dose limit and the statement that a Mars
mission exceeds it — ⚠️ **this is consistently reported across independent peer-reviewed
sources, and the ~1,000 mSv estimate is an estimate with real uncertainty, resting on
Curiosity RAD measurements extrapolated to a mission profile that hasn't been flown.**

⚠️ **Moderate confidence on the SANS incidence figure (~70% of >6-month crews)**: it comes
from clinical review literature rather than a single definitive study, **the astronaut
sample is small enough that percentages should be treated as indicative**, and the
underlying aetiology being unknown means the risk model itself may shift. **§16 is
engineering and values judgement, not physics** — particularly §16.1, where the crewed
versus robotic question is not settled by any technical argument and I have not pretended
otherwise. **§17's list is my assessment** of where the open problems sit; specialists in
life support or EDL would weight them differently.
