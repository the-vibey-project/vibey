---
id: skill-18-quick-reference-793df50c98
purpose: 18 quick reference
source: src/vibey_tools/skills/plugins/theory-of-computation/skills/toc-reference/SKILL.md
requires: ["skill-17-the-canon-9b3cddd875"]
links: ["skill-19-sources-and-method-ed1b6e5dd9"]
---

## §18. Quick Reference

### 18.1 The recognition table

| If you see... | Suspect | Do |
|---|---|---|
| Nesting, balancing, recursion in a format | Context-free | Use a parser, not regex (§2.2 → `toc-automata-regex-and-parsing`) |
| Nested quantifiers in a regex on untrusted input | **ReDoS** | Linear-time engine (§2.3 → `toc-automata-regex-and-parsing`) |
| "Detect all X in arbitrary programs" | **Undecidable** (Rice) | Approximate, restrict, or accept false positives (§4.1 → `toc-computability-and-complexity`) |
| Choose a subset / an ordering, constraints interact | **NP-hard** | §6 → `toc-computability-and-complexity` — check the canonical list first |
| "There exists a move such that for all responses…" | **PSPACE** | You have an adversary; it's worse than NP (§8 → `toc-beyond-np-space-and-distributed-limits`) |
| Quadratic on strings or sequences | **Possibly optimal** under SETH | Change the problem, don't optimize (§9 → `toc-beyond-np-space-and-distributed-limits`) |
| "Count distinct over a firehose" | Streaming | HyperLogLog / sketches (§10 → `toc-beyond-np-space-and-distributed-limits`) |
| "Guaranteed agreement over an unreliable network" | **Two Generals / FLP** | Idempotency; add an assumption explicitly (§11 → `toc-beyond-np-space-and-distributed-limits`) |
| "Exactly-once delivery" | **Impossible** | At-least-once + idempotency (§11 → `toc-beyond-np-space-and-distributed-limits`) |
| Big constraint problem with structure | **Solvable** | Throw it at a SAT/SMT/MIP solver (§7 → `toc-computability-and-complexity`) |

### 18.2 Numbers and facts
- **Regular can't count unboundedly** — the source of most "regex can't do that."
- **NFA → DFA is worst-case exponential** in states.
- **Backtracking regex is worst-case exponential**; RE2/Rust/Go are linear.
- **P ⊆ NP ⊆ PSPACE ⊆ EXPTIME**; **P ≠ EXPTIME is proven**, the rest are open.
- **NP = "a solution can be verified quickly."**
- **Set Cover's ln(n) approximation is optimal** unless P = NP.
- **Savitch**: NSPACE(f) ⊆ SPACE(f²).
- **Williams 2025**: TIME[t] ⊆ SPACE[√(t log t)] — was t/log t since 1975.
- **BFT needs n > 3f.**
- **P = BPP is widely conjectured** — randomness probably buys no asymptotic power.

### 18.3 Before you optimize
- [ ] Is this problem in a known hard class? Check §6.1 → `toc-computability-and-complexity`'s list
- [ ] If NP-hard: is n small? is the input structured? would a solver do it? (§6.2 → `toc-computability-and-complexity`)
- [ ] Does the business actually require *optimal*? (§6.2 → `toc-computability-and-complexity` #9)
- [ ] Is there a conditional lower bound saying I'm already optimal? (§9 → `toc-beyond-np-space-and-distributed-limits`)
- [ ] Am I optimizing asymptotics when constants and cache dominate at my n? (§5.2 → `toc-computability-and-complexity`)
- [ ] Am I asking a tool to solve an undecidable problem? (§4.1 → `toc-computability-and-complexity`)
- [ ] Have I named the distributed-systems assumptions I'm relying on? (§11 → `toc-beyond-np-space-and-distributed-limits`)

---
