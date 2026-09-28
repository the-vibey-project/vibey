---
id: skill-16-process-integration-218a8cb63c
purpose: 16 process integration
source: src/vibey_tools/skills/plugins/semiconductors-and-chip-manufacturing/skills/semi-integration-yield-metrology-test-and-packaging/SKILL.md
requires: []
links: ["skill-17-yield-eb314ca3c3"]
---

## §16. Process Integration

**⚠️ The discipline of making hundreds of individually-working steps work TOGETHER.**
⚠️ **FEOL (front end of line — transistors) → MOL (contacts) → BEOL (interconnect).**
**⚠️ A mask set for a leading node runs to dozens of layers and costs millions**, ⚠️ **which
is a large part of why NRE at the leading edge is prohibitive for low-volume designs**
(§25 → `semi-pcb-assembly-reliability-design-flow-and-economics`).
**⚠️ The integration engineer's problem is that everything interacts**: ⚠️ **a change in
etch chemistry shifts a CMP rate, which changes overlay, which shifts device parameters.**
**⚠️ Process control** uses SPC and increasingly run-to-run feedback (see a manufacturing
reference on Cp/Cpk) — ⚠️ **and PROCESS VARIATION is now a first-order design concern:
random dopant fluctuation, line edge roughness and metal grain variation make nominally
identical transistors measurably different.**

---
