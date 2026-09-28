---
id: skill-14-aerospace-flight-software-adc519bb93
purpose: 14 aerospace flight software
source: src/vibey_tools/skills/plugins/robotics-software/skills/robotics-safety-standards-and-deployment/SKILL.md
requires: ["skill-13-functional-safety-and-standards-ca9acfbfe8"]
links: []
---

## §14. Aerospace Flight Software

**[DURABLE] The far end of the rigour spectrum, and worth knowing even if you never work
there — because it shows what "we cannot fail" looks like as engineering practice.**

**Standards**: **DO-178C** (airborne software, DAL A–E; ⚠️ **DAL A demands MC/DC coverage
and full requirements traceability**), **DO-254** (hardware), **ECSS** (European space),
**NASA NPR 7150.2** and the **NASA/JPL Power of 10** coding rules, **MISRA C/C++** in
adjacent industries.

**The architectural patterns**: **triple modular redundancy with voting**,
**radiation-hardened or rad-tolerant compute** (⚠️ **and the flight computer is often
generations behind consumer silicon precisely because it's qualified**), **watchdogs at
multiple levels**, **partitioned RTOS** (ARINC 653), **NASA cFS** as a reusable flight
software framework, **no dynamic allocation after initialization**, **bounded loops and
bounded recursion**, and **extensive formal analysis**.

**⚠️ The cultural practices are as important as the technical ones**: exhaustive
requirements traceability, independent verification and validation, **change control that
would feel absurd anywhere else**, hardware-in-the-loop and flatsat testing,
**anomaly review boards**, and the doctrine that **every in-flight anomaly is investigated
to root cause and fed back into process.**

**[DURABLE] The transferable lesson for ordinary robotics**: **the practices scale down.**
Requirements traceability, deterministic execution, resource bounds, comprehensive logging,
and a written safety case are all achievable outside aerospace and all improve reliability.
⚠️ **You don't need DO-178C to adopt bounded loops and a no-allocation control path.**
