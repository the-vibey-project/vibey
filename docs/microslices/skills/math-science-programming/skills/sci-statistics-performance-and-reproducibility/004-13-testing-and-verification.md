---
id: skill-13-testing-and-verification-a58519bdbd
purpose: 13 testing and verification
source: src/vibey_tools/skills/plugins/math-science-programming/skills/sci-statistics-performance-and-reproducibility/SKILL.md
requires: ["skill-12-data-i-o-and-units-4adaa9e87b"]
links: ["skill-14-reproducibility-793922bcb7"]
---

## §13. Testing and Verification

**[DURABLE] The most under-practised discipline in scientific software, and the direct
answer to this document's opening framing.**

**⚠️ The vocabulary matters and is worth getting right:**
- **Verification: are we solving the equations right?** (A software question.)
- **Validation: are we solving the right equations?** (A science question — compare against
  experiment.)
- **⚠️ Both are needed, and passing one tells you nothing about the other.**

**The techniques that actually work:**
- **Analytical solutions.** Test against problems with known closed-form answers.
- **⚠️ The Method of Manufactured Solutions (MMS)** — **the most powerful verification tool
  in scientific computing and the least used.** Pick an arbitrary solution, substitute it
  into your PDE to derive the source term that makes it true, then check your solver
  recovers it. **It works for problems with no natural analytical solution.**
- **⚠️ Convergence-order testing.** A second-order method must show error dropping 4× when
  you halve h. **If your observed order doesn't match the theoretical order, you have a
  bug** — and this catches an enormous class of subtle errors that eyeballing a plot will
  not.
- **Conservation checks** — mass, energy, momentum, probability summing to 1. **Cheap,
  and they catch real bugs.**
- **Symmetry and invariance tests** — translate, rotate, or rescale the problem and the
  answer should transform correspondingly.
- **Property-based testing** — Hypothesis, and metamorphic relations generally.
- **Comparison against an independent implementation.**
- **Regression tests with tolerances** — ⚠️ **and pin the tolerance thoughtfully, because
  `assert_allclose` with default tolerances either passes everything or fails on noise.**
- **Test the edge cases**: zero, negative, NaN, inf, empty arrays, singular matrices,
  and the degenerate geometry.

**⚠️ And the mindset**: your code produces numbers whether or not it is correct.
**"It ran and the plot looks reasonable" is not evidence.**

---
