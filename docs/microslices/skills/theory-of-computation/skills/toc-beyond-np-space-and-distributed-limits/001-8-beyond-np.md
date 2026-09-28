---
id: skill-8-beyond-np-30e236808e
purpose: 8 beyond np
source: src/vibey_tools/skills/plugins/theory-of-computation/skills/toc-beyond-np-space-and-distributed-limits/SKILL.md
requires: []
links: ["skill-9-fine-grained-complexity-b574dcec9d"]
---

## §8. Beyond NP

**[DURABLE] Worth knowing the landscape so you recognize when you're in worse trouble than
NP.**

**PSPACE** — solvable in polynomial *space*, any amount of time. **PSPACE-complete
problems include quantified Boolean formulas (QBF), most two-player games, and many
planning problems.** ⚠️ **The tell: alternating quantifiers.** "Is there a move such that
for all responses there is a move such that…" That's QBF, that's PSPACE, and **it is a
qualitatively harder thing than a single existential search.** If your problem has an
adversary, you are probably here.

**EXPTIME** and above — **provably harder than P** (by the time hierarchy theorem, this
one is not conjectural). Generalized games on n×n boards, some type-system and logic
decision problems.

**Undecidable** — §4 → `toc-computability-and-complexity`.

**[DURABLE] The hierarchy theorems are among the few unconditional separations we have**:
more time and more space strictly buy you more. Almost everything else in §5 → `toc-computability-and-complexity`'s map is open.

---
