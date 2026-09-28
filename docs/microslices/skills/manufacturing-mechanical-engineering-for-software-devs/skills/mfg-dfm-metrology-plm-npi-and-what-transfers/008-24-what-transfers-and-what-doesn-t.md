---
id: skill-24-what-transfers-and-what-doesn-t-7d22397fc4
purpose: 24 what transfers and what doesn t
source: src/vibey_tools/skills/plugins/manufacturing-mechanical-engineering-for-software-devs/skills/mfg-dfm-metrology-plm-npi-and-what-transfers/SKILL.md
requires: ["skill-23-new-product-introduction-2d9e56ba92"]
links: []
---

## §24. ⚠️ What Transfers — and What Doesn't

```
⚠️ TRANSFERS WELL
   ⚠️ 1. TOLERANCE THINKING (§8) — ⚠️ nothing is exact; design for
        distributions, not values. ⚠️ The best single import here
   ⚠️ 2. EXACT CONSTRAINT (§7) — over-constraint creates conflict,
        not robustness. Redundant sources of truth fight
   ⚠️ 3. FATIGUE AS A MODEL (§4) — failures that only appear after
        many cycles, invisible in short tests
   ⚠️ 4. DFA's "delete the part" (§17) — ⚠️ the physical version of
        "the best code is no code," and it's taken far more seriously
   ⚠️ 5. GAUGE R&R (§18) — how much of your measured variation is
        the measurement system?
   ⚠️ 6. INTERCHANGEABILITY RULES (§21) — ⚠️ semantic versioning
        with teeth, because you cannot recall the past
   ⚠️ 7. STAGE GATES (§23) where reversal is genuinely expensive
   ⚠️ 8. SIMULATION SCEPTICISM (§20) — validate models against reality

⚠️ DOESN'T TRANSFER
   ⚠️ 1. FRONT-LOADED DESIGN as a universal virtue. ⚠️ It's rational
        when change costs six figures; it's waterfall when change
        costs nothing
   ⚠️ 2. TOOLING AMORTIZATION — ⚠️ software has no equivalent of
        "the first unit costs $80,000 and the rest cost $2"
   ⚠️ 3. PHYSICAL CONSTRAINTS as a forcing function — ⚠️ mechanical
        designs are disciplined by physics; software has no
        equivalent external constraint, which is both freedom and
        the reason scope creeps
   ⚠️ 4. MATERIAL PROPERTY DATA — ⚠️ there is no handbook of code
        strength (see a civil engineering reference)
   ⚠️ 5. ADVERSARIAL LOADS — ⚠️ steel doesn't probe your assumptions
```
**⚠️ The synthesis I'd offer**: ⚠️ **borrow mechanical engineering's TOLERANCE AND
CONSTRAINT thinking, not its process ceremony.** **⚠️ The ceremony is a rational response
to expensive change; the tolerance thinking is true regardless of what change costs.**
