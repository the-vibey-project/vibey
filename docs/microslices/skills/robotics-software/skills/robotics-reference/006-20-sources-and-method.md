---
id: skill-20-sources-and-method-f462f6af9c
purpose: 20 sources and method
source: src/vibey_tools/skills/plugins/robotics-software/skills/robotics-reference/SKILL.md
requires: ["skill-19-quick-reference-c1c93840e1"]
links: []
---

## §20. Sources and Method

**Method.** Narrative review, written for engineers building robots with real physical
consequences, and deliberately distinct from a hobbyist-kit reference. **§4–§7 → `robotics-stack-ros2-and-perception`, `robotics-planning-control-and-manipulation`'s theory
(estimation, planning, control, kinematics), §11 → `robotics-safety-standards-and-deployment`'s real-time practice, and §12 → `robotics-safety-standards-and-deployment`'s testing
and debugging discipline are decades stable** and rest on the standard literature — Thrun/
Burgard/Fox, LaValle, Lynch & Park, Åström & Murray, Rawlings — rather than on anything
searched; they were not web-verified because they do not need to be. Four targeted searches
were run in **August 2026** on the parts that move: the ROS 2 release state, the
vision-language-action frontier, and the safety-standards regime.

**Search log** (August 2026): ROS 2 distributions, Kilted/Lyrical, Zenoh and DDS ·
vision-language-action and robot foundation models (π-series, Gemini Robotics, GR00T) ·
ISO 10218:2025 revision, ISO/TS 15066 absorption, and humanoid safety standards.

**Primary and near-primary sources consulted (selected):**
- **Open Robotics' own release announcements and ROS 2 documentation** for the Kilted and
  Lyrical release details, Zenoh Tier 1 status, RMW changes and deprecations; the
  **ros2/ros2 GitHub releases page** for current patch releases; **endoflife.date** and
  **LWN's** ROS overview for the support-cadence rules
- **arXiv primary papers** for the VLA lineage — **GR00T N1 (2503.14734)**, **π₀
  (2410.24164)**, **π₀.₅ (2504.16054)**, **Gemini Robotics (2503.20020)** and
  **Gemini Robotics 1.5 (2510.03342)** — plus **NVIDIA's Isaac-GR00T repository** for the
  N1.7 GA status and backbone, and NVIDIA's own technical blog on world-action models
- **A3/Automate's ISO 10218 FAQ**, **The Robot Report**, **ANSI's blog**, **TÜV Rheinland**
  and **IDEC's** analysis series for the 2025 revision's scope, the ISO/TS 15066
  absorption, the terminology change, and the cybersecurity additions; a **ScienceDirect
  comparative analysis (2026)** for the identified regulatory gaps in AI, humanoids and
  mobile manipulation

**Confidence statement.** **Very high confidence** in §3.4 → `robotics-stack-ros2-and-perception`, §4 → `robotics-stack-ros2-and-perception`, §5 → `robotics-planning-control-and-manipulation`, §6 → `robotics-planning-control-and-manipulation`, §7 → `robotics-planning-control-and-manipulation`, §11 → `robotics-safety-standards-and-deployment`, §12 → `robotics-safety-standards-and-deployment` and
§15 — control theory, estimation, and the integration failure modes are settled and
consistently reported across decades of literature and practice. **High confidence in the
ROS 2 facts** (§2 → `robotics-stack-ros2-and-perception`), which come from Open Robotics' own announcements and documentation.
**High confidence in the ISO 10218:2025 changes** (§13.1 → `robotics-safety-standards-and-deployment`) — the terminology change, the
ISO/TS 15066 absorption, the cybersecurity addition and the April 2025 in-force date are
corroborated across A3, ANSI, TÜV and multiple independent legal-technical analyses.
⚠️ **But I read summaries and analyses, not the standards themselves** — ISO standards are
paywalled, and **§18.2's advice to buy the standard rather than work from summaries
applies to this document too.** If you are building a safety case, this section is a
pointer, not a source.

⚠️ **Lower confidence, deliberately, on §8 → `robotics-learning-simulation-and-fleets` and §17's VLA rows.** Model versions, backbones,
and availability status change monthly; several capability claims (demonstration counts,
generalization results) come from **the developing labs' own papers and blog posts, which
are not disinterested and rarely include failure analysis**; and §8.3 → `robotics-learning-simulation-and-fleets`'s assessment of what
is *not* working is my synthesis of the gap between published results and reported
deployment experience rather than a measured finding. **The §16.1 argument is genuinely
unresolved and I have tried to represent both sides rather than adjudicate.** The §13.2 → `robotics-safety-standards-and-deployment`
humanoid-standards gap is corroborated by the academic comparative analysis but the
practical consequences are still being worked out in industry, and anyone deploying should
seek current professional advice rather than rely on this.
