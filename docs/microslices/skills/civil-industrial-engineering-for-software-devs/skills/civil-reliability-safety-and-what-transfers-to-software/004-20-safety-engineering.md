---
id: skill-20-safety-engineering-349ef869c4
purpose: 20 safety engineering
source: src/vibey_tools/skills/plugins/civil-industrial-engineering-for-software-devs/skills/civil-reliability-safety-and-what-transfers-to-software/SKILL.md
requires: ["skill-19-reliability-engineering-e11d53ceff"]
links: ["skill-21-what-transfers-well-f20e862ea2"]
---

## §20. ⚠️ Safety Engineering

```
⚠️ HIERARCHY OF CONTROLS — in order of effectiveness, and the order matters
   1. ELIMINATE the hazard
   2. SUBSTITUTE something less hazardous
   3. ENGINEERING CONTROLS — guards, interlocks; work without cooperation
   4. ADMINISTRATIVE CONTROLS — procedures, training, warnings
   5. PPE — last resort, protects one person, depends on compliance
```
> **⚠️ GOTCHA — software defaults to levels 4 and 5 and calls it security.** ⚠️ **Training,
> policies and "be careful" documentation are ADMINISTRATIVE controls, the second-weakest
> tier.** **⚠️ Making a dangerous operation impossible (type systems, capability-based
> permissions, removing the production credential entirely) is ELIMINATION, and it's the
> strongest.** **The hierarchy is a ranking of effectiveness, and it should reorder most
> security backlogs.**

**⚠️ The Swiss cheese model** (Reason): ⚠️ **accidents require multiple independent
defensive layers to fail simultaneously; each layer has holes and the holes move.**
**⚠️ The corollary is that near-misses are the same event with one layer holding, which is
why reporting them matters more than counting accidents.**
**⚠️ Normal Accidents (Perrow)**: ⚠️ **systems with high interactive complexity AND tight
coupling will have accidents that are, in a real sense, inevitable** — **and the remedy is
reducing coupling, not adding procedures.** ⚠️ **Distributed systems are the textbook case.**
**⚠️ High Reliability Organizations (Weick and Sutcliffe)**: **preoccupation with failure,
reluctance to simplify, sensitivity to operations, commitment to resilience, and
⚠️ DEFERENCE TO EXPERTISE — decisions migrate to whoever knows most, regardless of rank.**
⚠️ **That last one is the andon cord again** (§14 → `civil-industrial-engineering-queueing-toc-and-lean`), **and it's the practice most
organizations claim and fewest have.**
**⚠️ Safety-II and resilience engineering** (Hollnagel): ⚠️ **study why things normally go
RIGHT, not only why they occasionally go wrong** — **because the same adaptive behaviour
produces both, and removing it to prevent failure removes the source of everyday success.**

---

# PART III — THE TRANSFER
