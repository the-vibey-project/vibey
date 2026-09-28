---
id: skill-19-reliability-engineering-e11d53ceff
purpose: 19 reliability engineering
source: src/vibey_tools/skills/plugins/civil-industrial-engineering-for-software-devs/skills/civil-reliability-safety-and-what-transfers-to-software/SKILL.md
requires: ["skill-18-human-factors-and-ergonomics-bc131ff60b"]
links: ["skill-20-safety-engineering-349ef869c4"]
---

## §19. Reliability Engineering

```
⚠️ MTBF / MTTF / MTTR  ⚠️ MTBF is a RATE parameter, not a lifespan —
   a 100,000-hour MTBF does not mean the unit lasts 11 years
⚠️ THE BATHTUB CURVE  infant mortality (decreasing rate) → useful life
   (roughly constant) → wear-out (increasing rate)
   ⚠️ Software has infant mortality and NO wear-out — but it has a
   third mode hardware lacks: the environment changes underneath it
AVAILABILITY = MTBF / (MTBF + MTTR)  ⚠️ note both terms; halving MTTR
   improves availability as much as doubling MTBF, and is usually cheaper
⚠️ SERIES vs PARALLEL  series reliability MULTIPLIES (⚠️ ten 99.9%
   components in series gives 99%); parallel redundancy multiplies FAILURE
   probabilities instead
⚠️ FMEA  Failure Modes and Effects Analysis — enumerate failure modes,
   rate severity × occurrence × detectability, prioritize
FAULT TREE / EVENT TREE  top-down vs bottom-up
```
**⚠️ The series-reliability arithmetic is the one software most needs**: ⚠️ **a request
path through ten services each at 99.9% is 99% end-to-end**, **which is why microservice
architectures need explicit reliability budgeting rather than per-service targets.**
**⚠️ FMEA transfers directly and is under-used** — **it's a structured version of what a
good design review does informally, and the DETECTABILITY axis is the one software forgets:
a failure you can't observe is worse than one you can.**

---
