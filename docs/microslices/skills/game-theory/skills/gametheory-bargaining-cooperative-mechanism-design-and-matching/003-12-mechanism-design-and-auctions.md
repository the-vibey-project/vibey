---
id: skill-12-mechanism-design-and-auctions-0de48cdb19
purpose: 12 mechanism design and auctions
source: src/vibey_tools/skills/plugins/game-theory/skills/gametheory-bargaining-cooperative-mechanism-design-and-matching/SKILL.md
requires: ["skill-11-cooperative-game-theory-67e7a68c7b"]
links: ["skill-13-matching-markets-622179f1f9"]
---

## §12. Mechanism Design and Auctions

**⚠️ "Reverse game theory": design the rules so that self-interested play produces the
outcome you want.**

**Revelation principle** — ⚠️ **any outcome achievable by any mechanism is achievable by a
direct mechanism in which truth-telling is optimal.** **This is a massive simplification:
you can restrict attention to incentive-compatible direct mechanisms without loss.**

**⚠️ The impossibility results are the substance of the field:**
```
ARROW (1951)                 ⚠️ No voting rule over ≥3 alternatives satisfies
                             unanimity, IIA, and non-dictatorship
GIBBARD-SATTERTHWAITE (1973) ⚠️ Any non-dictatorial deterministic voting rule over
                             ≥3 alternatives is MANIPULABLE. Strategic voting is
                             unavoidable, not a design flaw
MYERSON-SATTERTHWAITE (1983) ⚠️ No mechanism for bilateral trade with private values
                             is simultaneously efficient, individually rational, and
                             budget-balanced. SOME EFFICIENT TRADES CANNOT HAPPEN
HURWICZ                      Incentive compatibility and efficiency conflict generally
```
**⚠️ These are the results to internalize.** **They mean certain design goals are not
merely hard but provably unattainable**, and a proposal that claims all of them is wrong
somewhere.

**VCG (Vickrey-Clarke-Groves)** — ⚠️ **each participant pays the externality they impose on
others; truth-telling is a dominant strategy and the outcome is efficient.** **The
catches**: ⚠️ **not budget-balanced (may require outside subsidy), vulnerable to collusion
and false-name bidding, computationally demanding, and the prices can look
politically indefensible** — which is why it's rarer in practice than its theoretical
prominence suggests.

**Auctions:**
```
English (ascending)     ⚠️ strategically equivalent to second-price for private values
Dutch (descending)      ⚠️ strategically equivalent to first-price
First-price sealed bid  ⚠️ bid BELOW your value; optimal shading depends on beliefs
Second-price (Vickrey)  ⚠️ TRUTHFUL BIDDING IS DOMINANT — the headline result
All-pay                 everyone pays; models lobbying, R&D races, conflict
```
**⚠️ Revenue equivalence theorem**: under private independent values, risk neutrality, and
symmetry, **all four standard auctions yield the same expected revenue.**
⚠️ **The theorem's value is in its assumptions**: **when auctions differ in practice — and
they do — it's because one of those assumptions failed** (risk aversion, correlated values,
asymmetry, budget constraints, collusion). **That's the diagnostic.**

**⚠️ Practical note on second-price auctions**: truthful bidding is dominant only under
private values and a trustworthy auctioneer. **The seller can inflate the second price;
the winner's curse (§9 → `gametheory-zero-sum-sequential-repeated-and-information`) bites under common values.** **The theory is clean; deployment
requires trust in the mechanism operator.**

---
