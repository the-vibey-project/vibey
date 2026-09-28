---
id: skill-16-contested-questions-b4fc0fecdf
purpose: 16 contested questions
source: src/vibey_tools/skills/plugins/math-science-programming/skills/sci-reference/SKILL.md
requires: ["skill-15-anti-patterns-053ce7d4bd"]
links: ["skill-17-currency-snapshot-verified-august-2026-b101cffa6a"]
---

## §16. Contested Questions

**16.1 Julia, Python, or MATLAB?** §4 → `sci-tooling-and-symbolic-computation`. **[CONTESTED and genuinely unsettled.]** Julia is
technically excellent and mature by download and package count, with real enterprise
backing — **and its adoption metrics remain modest, its compile latency and AOT story draw
persistent criticism, and one 2024 assessment argued its language-level limitations are
"severe enough to prevent widespread adoption."** Meanwhile **Python closed much of the
performance gap** through Numba, JAX, and the Array API. **The honest answer is
ecosystem-dependent, and §4.1 → `sci-tooling-and-symbolic-computation`'s first criterion usually decides it.**

**16.2 Is MATLAB worth the licence?** *For*: toolbox quality is genuinely unmatched in
control, DSP and Simulink-to-hardware, the documentation is excellent, and in regulated
industries the validation pedigree matters. *Against*: cost, lock-in, and
⚠️ **proprietary dependencies are a reproducibility liability** (§14 → `sci-statistics-performance-and-reproducibility`). **Strongest where a
specific toolbox has no free equivalent; weakest as general-purpose numerics.**

**16.3 Should scientists be trained as software engineers?** *For*: §13 → `sci-statistics-performance-and-reproducibility` and §14 → `sci-statistics-performance-and-reproducibility`'s failure
modes are engineering failures, and the crisis is measurable. *Against*: research code is
often exploratory and genuinely throwaway, and full engineering rigour on a script that
runs once is waste. **⚠️ The synthesis most Research Software Engineering groups land on:
tiered rigour — throwaway analysis gets version control and a pinned environment; anything
others will use gets tests, docs, and review.**

**16.4 Are notebooks good or bad for science?** *For*: exploration, narrative, teaching,
and reproducible figures. *Against*: ⚠️ **hidden execution-order state, poor diffing, and
they encourage code that can't be tested or reused.** **The workable compromise: notebooks
for exploration and presentation, importable modules for anything that matters, and
`nbstripout`/Jupytext in version control.**

**16.5 Is scientific ML overhyped?** §7.3 → `sci-linear-algebra-differential-equations-and-optimization`. *For*: real wins on surrogates, inverse
problems, and closure modelling. *Against*: ⚠️ **for well-posed forward problems, classical
solvers are usually faster, more accurate, and come with error bounds** — and the
comparisons in papers frequently omit a well-tuned conventional baseline. **Live.**

**16.6 Fortran — legacy or still right?** *For*: it remains extremely fast for dense array
work, modern Fortran is much improved, and rewriting validated legacy code is a genuine
risk. *Against*: hiring, tooling, ecosystem. **⚠️ "It's old" is not an argument; "nobody
here can maintain it" is.**

---
