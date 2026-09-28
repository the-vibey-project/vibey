---
id: skill-16-state-machines-0d3b707caf
purpose: 16 state machines
source: src/vibey_tools/skills/plugins/digital-logic-and-firmware-engineering/skills/logic-sequential-timing-metastability-cdc-and-hdl/SKILL.md
requires: ["skill-15-timing-and-metastability-ebeef6451d"]
links: ["skill-17-clock-domain-crossing-70ed7c2afb"]
---

## §16. State Machines

**⚠️ Moore versus Mealy**: ⚠️ **Moore outputs depend only on state (⚠️ registered, glitch
free, one cycle later); Mealy outputs depend on state AND inputs (⚠️ faster response,
combinational path from input to output, which can create timing problems across module
boundaries).**
**⚠️ State encoding**: ⚠️ **binary (fewest flops), ⚠️ ONE-HOT (⚠️ one flop per state,
simpler and faster decode logic, and usually the right choice in FPGAs where flops are
plentiful), and Gray.**
**⚠️ The design discipline**: ⚠️ **state diagram first, then a coded template — and separate
the next-state logic, the state register and the output logic into distinct blocks, because
that structure both reads clearly and synthesizes predictably.**
**⚠️ Unreachable and illegal states** — ⚠️ **and for anything safety-related, a default case
that returns to a known state, because a glitch or upset can put a machine in a state your
diagram doesn't contain.**

---
