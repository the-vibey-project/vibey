---
id: skill-4-computability-what-you-cannot-do-c1d36c8bf6
purpose: 4 computability what you cannot do
source: src/vibey_tools/skills/plugins/theory-of-computation/skills/toc-computability-and-complexity/SKILL.md
requires: []
links: ["skill-5-complexity-classes-a018974ce3"]
---

## §4. Computability — What You Cannot Do

### 4.1 The halting problem and what follows

**[DURABLE] There is no program that takes an arbitrary program and input and correctly
decides whether it halts.** The proof is a two-line diagonalization, and its consequences
are everywhere in your tooling.

**Rice's theorem generalizes it, and this is the version engineers should know:**
**every non-trivial semantic property of programs is undecidable.** Not "hard" —
**undecidable.** Does this program ever throw? Is this variable ever null? Are these two
functions equivalent? Is this code dead? Does this ever access out of bounds?
**All undecidable in general.**

> **⚠️ GOTCHA — this is why your tools behave the way they do, and knowing it changes how
> you use them.** A static analyzer cannot be simultaneously **sound** (no false negatives)
> and **complete** (no false positives) and **terminating**. It must pick two. So:
> - **Linters and most analyzers choose "terminating + roughly useful"** and accept both
>   false positives and false negatives.
> - **Sound analyzers** (used in avionics, automotive) accept **false positives** — they'll
>   flag safe code — because missing a real bug is unacceptable.
> - **Type systems** are decidable approximations that reject some correct programs.
>   **When the compiler rejects code you know is fine, that is the theory, not a bug.**
>
> **The engineering consequence: stop asking for a tool with no false positives.** You are
> asking for a solution to the halting problem. Ask instead which side of the trade-off the
> tool sits on, and whether that matches your risk.

### 4.2 Reductions — the most transferable skill here

**[DURABLE] "If I could solve B, I could solve A; A is impossible; therefore B is
impossible."** This is how nearly every undecidability and hardness result is proved, and
**it is a reasoning pattern you can apply directly at work.**

The practical version: when a stakeholder asks for a feature, ask whether it reduces to
something known impossible or known hard. *"Detect all infinite loops before deployment"*
reduces to halting. *"Find the optimal assignment across all these constraints"* frequently
reduces to something NP-hard (§6). **Recognizing the reduction saves you a quarter.**

### 4.3 Other undecidable things you may encounter
Program equivalence. Whether a CFG is ambiguous. Whether two CFGs generate the same
language. The Post Correspondence Problem (the standard tool for proving other things
undecidable). Type inference for some sufficiently expressive systems (§12 → `toc-type-systems-and-randomization`). Whether an
arbitrary Diophantine equation has a solution (Hilbert's 10th). **Some tile-matching and
configuration problems** — which is why certain package-resolution and layout problems are
genuinely, formally hard.

**[DURABLE] Undecidable does not mean useless.** Every practical tool works on a decidable
*subset*, or accepts approximation, or uses a timeout. **Termination checkers, model
checkers, and dependent type systems all exist and work** — by restricting the problem, not
by solving the impossible one.

---
