---
id: skill-15-autonomy-and-onboard-ai-86c34ad723
purpose: 15 autonomy and onboard ai
source: src/vibey_tools/skills/plugins/flight-software/skills/flightsw-gnc-verification-ground-and-autonomy/SKILL.md
requires: ["skill-14-ground-segment-6abbbf1445"]
links: ["skill-16-failure-case-studies-ea6529494f"]
---

## §15. Autonomy and Onboard AI

**[DURABLE] Autonomy is forced by light-time** (a space-exploration reference §5.3), not
chosen.

**The ladder**: time-tagged sequences → event-driven sequencing → onboard planning
(⚠️ **Remote Agent on Deep Space 1, 1999, was the first onboard planner in control of a
spacecraft**) → autonomous science (**AEGIS** selects and targets spectroscopy on the Mars
rovers without ground involvement) → **fully autonomous EDL.**

**⚠️ Onboard ML is arriving and the verification problem is unsolved.** cFS's planned
2026 Gov Alpha explicitly targets AI/ML integration, and HPSC (§4 → `flightsw-processors-radiation-and-real-time`) provides the compute.
**The engineering-honest position:**
- **⚠️ Use learned components for perception and classification, not for the safety-critical
  control path.** The architecture that works is a learned layer inside a classical
  envelope with deterministic limits — see a robotics-software reference §8.3 for the same
  pattern in robotics.
- **⚠️ There is no accepted certification path for a neural network at DO-178C DAL A.**
  Saying otherwise is marketing.
- **Bounded compute and bounded latency still apply** (§6 → `flightsw-processors-radiation-and-real-time`) — an inference that occasionally
  takes 3× as long has violated a deadline.

---
