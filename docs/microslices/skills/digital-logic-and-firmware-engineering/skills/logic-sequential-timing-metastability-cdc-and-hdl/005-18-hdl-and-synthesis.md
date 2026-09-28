---
id: skill-18-hdl-and-synthesis-14bb09b7b7
purpose: 18 hdl and synthesis
source: src/vibey_tools/skills/plugins/digital-logic-and-firmware-engineering/skills/logic-sequential-timing-metastability-cdc-and-hdl/SKILL.md
requires: ["skill-17-clock-domain-crossing-70ed7c2afb"]
links: ["skill-19-test-and-dft-d86b5ec164"]
---

## §18. HDL and Synthesis

**⚠️ Verilog/SystemVerilog and VHDL** — ⚠️ **and the mental correction that matters most:
⚠️ HDL IS NOT A PROGRAMMING LANGUAGE. It DESCRIBES HARDWARE. ⚠️ Statements are concurrent
by default, and "assignment" creates a wire or a register, not an action in time.**
**⚠️ Blocking versus non-blocking assignment** is the canonical beginner trap:
⚠️ **non-blocking (`<=`) for sequential logic, blocking (`=`) for combinational — and mixing
them in one block produces simulation/synthesis mismatch, where the simulation passes and
the chip doesn't work.**
**⚠️ The synthesizable subset is much smaller than the language** — ⚠️ **delays, most
initial blocks and much of the type system exist for simulation and testbenches only.**
**⚠️ The flow**: ⚠️ **RTL → synthesis to a gate netlist → place and route → static timing
analysis → sign-off** (see a microarchitecture reference §24).
**⚠️ FPGA versus ASIC** targets differ enough to change coding style: ⚠️ **FPGAs have
abundant flops and fixed block RAM and DSP resources; ASICs have a cell library and
enormous NRE.**
**⚠️ Verification is the majority of the effort**: ⚠️ **testbenches, constrained-random,
coverage, assertions (SVA), and formal equivalence checking against §10 → `logic-standard-cells-boolean-minimization-and-arithmetic`'s BDDs.**

---
