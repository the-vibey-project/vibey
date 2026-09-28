---
id: skill-12-queueing-theory-and-little-s-law-8f0aad9790
purpose: 12 queueing theory and little s law
source: src/vibey_tools/skills/plugins/civil-industrial-engineering-for-software-devs/skills/civil-industrial-engineering-queueing-toc-and-lean/SKILL.md
requires: ["skill-11-what-industrial-engineering-actually-is-5694cadd39"]
links: ["skill-13-theory-of-constraints-c1173e078b"]
---

## §12. ⚠️ Queueing Theory and Little's Law

**⚠️ The single most valuable import in this document, and it requires no metaphor —
it's a theorem.**
```
⚠️ LITTLE'S LAW:   L = λW
   ⚠️ Work In Progress = Arrival Rate × Time In System
   ⚠️ Holds for ANY stable queueing system regardless of distribution,
   service discipline, or what's queueing. It is a mathematical identity
⚠️ THEREFORE:  cycle time = WIP / throughput
   ⚠️ You cannot reduce cycle time without reducing WIP or raising throughput.
   Exhorting people to "work faster" changes neither
```
> **⚠️ GOTCHA — the utilization curve is the finding that changes how you staff teams,
> and almost nobody internalizes it.** ⚠️ **Queue length rises NON-LINEARLY with
> utilization, approaching infinity as utilization approaches 100%.** **⚠️ Roughly: a
> system at 80% utilization has queues around four times longer than one at 50%; past 90%
> the wait time explodes.**
> **⚠️ Variability makes it worse.** **The Kingman approximation shows waiting time scales
> with the variability of BOTH arrivals and service times — so a team with highly variable
> task sizes queues far worse than one with uniform tasks at the same utilization.**
> **⚠️ The management implication is deeply counterintuitive: a team booked to 100%
> capacity is not efficient, it is GUARANTEED to have exploding lead times.** **Slack is a
> throughput requirement, not a luxury** — **and this is a theorem, not an opinion.**

**⚠️ Practical software applications**: ⚠️ **WIP limits in Kanban are Little's Law applied;
so is limiting concurrent projects per team, sizing thread pools and connection pools,
and understanding why a service at 85% CPU has terrible tail latency.**
**⚠️ M/M/1 vs M/M/c**: ⚠️ **one shared queue served by c servers dramatically outperforms
c separate queues** — **which is the argument for shared work queues over per-person
assignment, and for a single load balancer queue over sticky routing.**

---
