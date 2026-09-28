---
id: skill-16-contested-questions-e9b03d7d84
purpose: 16 contested questions
source: src/vibey_tools/skills/plugins/robotics-software/skills/robotics-reference/SKILL.md
requires: ["skill-15-anti-patterns-87eeba3c05"]
links: ["skill-17-currency-snapshot-verified-august-2026-41a96e5e78"]
---

## §16. Contested Questions

**16.1 End-to-end learning vs. modular classical stacks.** ⚠️ **The field's central live
argument.** *For learning*: hand-engineered pipelines don't generalize to the long tail,
and VLAs demonstrably do semantic generalization classical systems cannot. *For classical*:
**guarantees, interpretability, debuggability, and the ability to write a safety case** —
and when a learned system fails you often cannot say why. **[CONTESTED. Production systems
are overwhelmingly hybrid, and §8.3 → `robotics-learning-simulation-and-fleets`'s split — learned perception and policy, classical
control and safety — is where the evidence currently sits.]**

**16.2 Is ROS 2 the right foundation for production?** *For*: the ecosystem is
irreplaceable, and rebuilding drivers and tooling is enormous undeveloped work.
*Against*: **the companies with the highest reliability requirements — Boston Dynamics,
most AV stacks, aerospace — largely don't use it**, for real-time and certification
reasons. **⚠️ A defensible read: ROS 2 for the mission layer, something else for the
hard real-time and safety layers.**

**16.3 Are humanoids the right form factor?** *For*: the world is built for human
morphology, and one platform could serve many tasks. *Against*: ⚠️ **bipedal locomotion is
an enormous cost paid to solve a problem wheels solved**, and task-specific robots
outperform generalists at almost everything today. **The honest position: the bet is on
future generality and data network effects, not on current capability.**

**16.4 Simulation-first or hardware-first?** *Sim*: parallel, cheap, safe, and the only
way RL is tractable. *Hardware*: ⚠️ **the gap is real and sim-validated systems fail in
ways sim cannot show.** **The synthesis everyone converges on is sim for coverage,
hardware for truth, and HIL bridging them.**

**16.5 How much does foundation-model progress transfer to robots?** *Optimistic*:
Open X-Embodiment showed cross-embodiment transfer, and the scaling story has held so far.
*Sceptical*: ⚠️ **robotics has no internet-scale data and cannot easily get it; the
bottleneck is physical interaction data, not model capacity.** ⚠️ **World models and
synthetic data generation are the field's current bet on escaping that**, and whether it
works is genuinely open.

**16.6 Should safety-critical robotics use learned components at all?** *For*: learned
perception already outperforms classical on most metrics, and refusing it forfeits
capability. *Against*: **no current method produces the evidence a safety case needs.**
**⚠️ SOTIF (ISO 21448) is the standards world's attempt to grapple with this**, and it's
incomplete. **Live and unresolved.**

---
