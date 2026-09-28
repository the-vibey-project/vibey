---
id: skill-core-principle-3f97d4b15f
purpose: core principle
source: src/vibey_tools/skills/plugins/frontend-design/skills/performance-optimization/SKILL.md
requires: []
links: ["skill-python-performance-059ab084a9"]
---

## Core Principle

**The biggest wins come from architecture, not micro-optimization.** In Python, vectorizing Pandas/NumPy loops yields 100–740x speedups while profiler-guided fixes routinely cut P99 ~40%. In Next.js, pushing `"use client"` to the leaves and using RSC streaming/PPR cuts First Load JS 50–70% and moves TTFB from ~350ms to ~40–90ms. In Azure, choosing the right compute tier matters more than any code tweak.

**Measure first. Never optimize without before-numbers.**

---
