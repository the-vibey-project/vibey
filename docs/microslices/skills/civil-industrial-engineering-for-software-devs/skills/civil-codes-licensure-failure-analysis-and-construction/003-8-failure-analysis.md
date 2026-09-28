---
id: skill-8-failure-analysis-21b3494f13
purpose: 8 failure analysis
source: src/vibey_tools/skills/plugins/civil-industrial-engineering-for-software-devs/skills/civil-codes-licensure-failure-analysis-and-construction/SKILL.md
requires: ["skill-7-licensure-and-liability-bcfb07bea8"]
links: ["skill-9-construction-sequencing-dea3bf9a8f"]
---

## §8. ⚠️ Failure Analysis

**⚠️ The practice software should envy most: when a structure fails, an independent body
investigates, publishes, and the code changes.**
```
⚠️ TACOMA NARROWS (1940)  aeroelastic FLUTTER — ⚠️ commonly and incorrectly
   taught as simple resonance from vortex shedding
⚠️ RONAN POINT (1968)  a gas explosion removed one load-bearing panel and a
   corner of the building progressively collapsed. ⚠️ Produced
   disproportionate-collapse provisions worldwide
⚠️ HYATT REGENCY WALKWAY (1981)  ⚠️ a CONNECTION DETAIL changed during
   shop drawing review DOUBLED the load on a connection. 114 died.
   ⚠️ The engineers lost their licences. This is the canonical case
⚠️ CHALLENGER (1986)  ⚠️ known risk normalized over repeated success
⚠️ SAMPOOR / other progressive collapses  modifications without re-analysis
⚠️ HYPERLOOP-ADJACENT / FIU BRIDGE (2018)  design errors compounded by
   pressure not to close the road under a cracking structure
```
> **⚠️ GOTCHA — the Hyatt Regency lesson is not "check your maths."** ⚠️ **It's that a
> seemingly minor constructability change, made by a fabricator and approved in routine
> review, doubled a load — and NOBODY RE-DERIVED the analysis for the changed detail.**
> **⚠️ The software analogue is exact: a change that looks like an implementation detail
> silently invalidates an assumption the original design depended on.** **That's the class
> of bug that causes outages nobody can explain from the diff.**

**⚠️ The institutional practices worth stealing wholesale**: ⚠️ **independent investigation
(the investigator does not work for the builder), published findings regardless of
embarrassment, and a feedback loop into mandatory standards.** ⚠️ **Blameless postmortems
are software's version and they usually stop short of the last step — the finding rarely
becomes a rule anyone else is obliged to follow.**

---
