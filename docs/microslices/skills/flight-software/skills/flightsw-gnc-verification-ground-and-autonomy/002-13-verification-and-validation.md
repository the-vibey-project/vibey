---
id: skill-13-verification-and-validation-d6a52a674f
purpose: 13 verification and validation
source: src/vibey_tools/skills/plugins/flight-software/skills/flightsw-gnc-verification-ground-and-autonomy/SKILL.md
requires: ["skill-12-gnc-software-69c4c07d58"]
links: ["skill-14-ground-segment-6abbbf1445"]
---

## §13. Verification and Validation

**[DURABLE] The layered campaign:**
```
Static analysis   ⚠️ multiple tools daily (Power of 10 rule 10) — Coverity,
                  Polyspace, CBMC, clang analyzer
Unit test         with coverage requirements up to MC/DC (§3.3)
Integration       component interactions on the software bus
SIL               software-in-the-loop against a simulated environment
PIL / HIL         ⚠️ processor- and hardware-in-the-loop — the flight code on the
                  flight processor
Testbed           ⚠️ a full engineering-model spacecraft on the ground
Day-in-the-life   realistic operational sequences end to end
Fault injection   ⚠️ deliberately corrupt memory, hang devices, drop messages
```

**⚠️ Formal methods are used here more than anywhere else in industry**, because the cost
of failure justifies it: **SPARK/Ada** for provable absence of runtime errors, **model
checking** (⚠️ **SPIN, developed by Holzmann at JPL, verified concurrency logic for
several missions**), **abstract interpretation** (Astrée), and **theorem proving** for
critical algorithms. **DO-333 provides the certification credit path.**

**13.3 ⚠️ The testbed is where flight software actually gets validated**, and its fidelity
is a mission-level risk. **Discrepancies between testbed and flight configuration are a
recurring source of anomalies** — different EEPROM contents, different table values,
different device firmware revision. **Configuration control of the testbed is as important
as of the flight article.**

**⚠️ And the irreducible gap: you cannot test in flight conditions.** You cannot produce
zero-g, the real radiation environment, or the real thermal-vacuum dynamics simultaneously.
**This is why fault injection and formal methods carry so much weight — they cover what the
test campaign structurally cannot.**

---
