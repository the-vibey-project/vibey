---
id: skill-15-interlocking-c82835b84d
purpose: 15 interlocking
source: src/vibey_tools/skills/plugins/locomotion-and-train-technologies/skills/rail-signalling-interlocking-train-protection-and-safety/SKILL.md
requires: ["skill-14-block-signalling-41b5431dfe"]
links: ["skill-16-train-protection-atp-etcs-ptc-cbtc-d9af39c4cc"]
---

## §15. Interlocking

**⚠️ The logic that prevents conflicting movements being signalled, and the safety-critical
heart of a railway.**
```
⚠️ THE CORE RULES
   ⚠️ Points must be correctly SET, LOCKED and DETECTED before a
      signal can clear
   ⚠️ Conflicting routes cannot be set simultaneously
   ⚠️ Route locking holds the route until the train has passed
   ⚠️ Approach locking prevents pulling a route from under an
      approaching train
   ⚠️ Flank protection guards against a movement running into the route
GENERATIONS  ⚠️ mechanical (lever frames with physical locking bars —
   the logic is literally machined into metal) → relay → ⚠️ SSI and
   computer-based interlocking
```
**⚠️ Mechanical interlocking deserves respect**: ⚠️ **the safety logic was implemented as
physical shapes that could not be defeated by a wiring error or a software bug**, **and
migrating that assurance level to software is precisely why modern signalling projects are
slow and expensive** (§26.1 → `rail-reference`).

---
