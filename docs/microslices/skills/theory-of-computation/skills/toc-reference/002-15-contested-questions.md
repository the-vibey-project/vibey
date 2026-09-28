---
id: skill-15-contested-questions-1ef970f6be
purpose: 15 contested questions
source: src/vibey_tools/skills/plugins/theory-of-computation/skills/toc-reference/SKILL.md
requires: ["skill-14-anti-patterns-9c567e5762"]
links: ["skill-16-currency-snapshot-verified-august-2026-79175ff51c"]
---

## §15. Contested Questions

**15.1 Does P = NP?** **[DURABLE] Overwhelming consensus is no** — polls of theorists
return large majorities — but it is unproven and it is one of the Millennium Problems.
**⚠️ The known barriers matter**: relativization, natural proofs, and algebrization each
rule out a broad class of techniques, which is why progress is slow and why "we just need
a clever construction" underestimates the difficulty. **Practically it changes nothing**:
plan as if P ≠ NP, because that's the world we can build for.

**15.2 How much theory does a working engineer need?** *For more*: it prevents whole
categories of wasted effort, it's the vocabulary for reasoning about limits, and the
ReDoS/FLP/undecidability cases are direct production concerns. *For less*: most engineers
ship valuable software without it, and the classical curriculum (heavy on Turing machine
constructions and pumping-lemma proofs) is a poor match for what practice needs.
**[CONTESTED] The synthesis this document takes: fluency in what things mean and how to
recognize them matters enormously; the ability to construct a formal proof matters much
less** — and most courses invert that weighting.

**15.3 Is the Turing machine still the right model?** *For*: extreme robustness, and the
Church–Turing thesis has held for ninety years. *Against*: it models nothing about memory
hierarchy, parallelism, or communication — which is where all real performance lives. Hence
RAM models, external-memory and cache-oblivious models, PRAM, and the LOCAL/CONGEST models
for distributed computing. **The right answer is that the model should match the resource
you're actually spending.**

**15.4 Is quantum computing a genuine complexity change?** BQP is believed to contain
problems outside P (factoring, discrete log) but **is not believed to contain NP** — so
**quantum computers are not believed to solve NP-complete problems efficiently.** Grover
gives quadratic, not exponential, speedup on unstructured search.

**15.5 Are formal methods worth it?** *For*: they find design bugs testing cannot, and the
verified-kernel and verified-compiler projects are real. *Against*: cost, specialist
skills, and the risk of verifying against a wrong specification. **The strong middle
position: lightweight methods (TLA+, Alloy, property-based testing, model-checking a
protocol) are badly under-used relative to their cost/benefit**, whatever you think about
full verification.

**15.6 Does fine-grained complexity actually help practitioners?** *For*: it tells you when
to stop optimizing, which is genuinely valuable. *Against*: the bounds are conditional,
often asymptotic, and rarely change what you'd do next anyway. **The honest answer is that
it matters most when someone is about to spend a quarter making a quadratic algorithm
subquadratic.**

---
