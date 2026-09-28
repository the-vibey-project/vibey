---
id: skill-11-process-and-toolchain-01fdb9fa6f
purpose: 11 process and toolchain
source: src/vibey_tools/skills/plugins/automotive-software/skills/auto-process-testing-domains-and-supply-chain/SKILL.md
requires: []
links: ["skill-12-testing-cde13d451c"]
---

## §11. Process and Toolchain

**⚠️ The V-model dominates because ISO 26262 requires traceable verification at every
level** — and it is more compatible with iteration than its reputation suggests.
```
Requirements ─────────────────────────────────► Validation
  Architecture ───────────────────────────► System test
    Design ──────────────────────────► Integration test
      Implementation ──────────► Unit test
```
**Each left-side activity has a corresponding right-side verification, and traceability
runs both ways.** ⚠️ **Traceability is what auditors check.**

**Automotive SPICE (ASPICE)** — the process assessment model. ⚠️ **OEMs routinely require
Tier-1s to demonstrate ASPICE Level 2 or 3**, which makes it a commercial requirement, not
just a quality aspiration.

**Model-based development**: **Simulink/Stateflow** or **ASCET**, with **autocoding**
(⚠️ **Embedded Coder and TargetLink are qualified for safety-critical use — the
qualification is why they're used**). **The model is the specification and it's
executable.** ⚠️ **But generated code's WCET, stack usage and MISRA conformance still need
checking — autocoding does not exempt you** (§5 → `auto-real-time-safety-and-cybersecurity`).

**Coding standards**: **MISRA C:2012** (⚠️ **the automotive standard, with a formal
deviation process — documented deviations are acceptable, undocumented ones are a
finding**), **MISRA C++** and **AUTOSAR C++14** (⚠️ **now merged into MISRA C++:2023**).
**Static analysis** (Polyspace, Coverity, QAC, Astrée) is expected, not optional.

**Tooling reality**: **Vector** (CANoe, CANalyzer, DaVinci — ⚠️ **near-ubiquitous**),
**dSPACE** and **ETAS** (HIL, calibration, INCA), **Lauterbach TRACE32** (debug),
**Elektrobit**, **Green Hills** and **QNX** (RTOS/hypervisor), **PTC/Polarion/DOORS**
(requirements). ⚠️ **This toolchain is expensive and vendor-locked, and it is a real
barrier to entry for the industry — which is part of why the SDV movement has an
open-source counter-current** (Eclipse SDV, COVESA, SOAFEE).

---
