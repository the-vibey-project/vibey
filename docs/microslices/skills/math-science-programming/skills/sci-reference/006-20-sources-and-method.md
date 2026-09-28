---
id: skill-20-sources-and-method-8f64c281a2
purpose: 20 sources and method
source: src/vibey_tools/skills/plugins/math-science-programming/skills/sci-reference/SKILL.md
requires: ["skill-19-quick-reference-3613ba3c78"]
links: []
---

## §20. Sources and Method

**Method.** Narrative review, written as practice guidance for engineers doing numerical
work. **The overwhelming majority of this document — §1 → `sci-floating-point-and-numerical-foundations`, §2 → `sci-floating-point-and-numerical-foundations`, §3 → `sci-floating-point-and-numerical-foundations`, §5–§13 → `sci-tooling-and-symbolic-computation`, `sci-linear-algebra-differential-equations-and-optimization`, `sci-statistics-performance-and-reproducibility`, §15 — is
numerical analysis and long-settled engineering practice**, resting on the standard
literature (Higham, Trefethen & Bau, Golub & Van Loan, Nocedal & Wright, Hairer et al.,
Roache) rather than on anything searched. **IEEE 754 is from 1985 and the algorithms are
mostly older than that**; §17 says so explicitly rather than manufacturing currency.
Three targeted searches were run in **August 2026** on the parts that genuinely move:
the language landscape, the Python array ecosystem, and the state of reproducibility
practice.

**Search log** (August 2026): Julia adoption, the two-language problem, and the MATLAB
comparison · NumPy 2 / SciPy / Array API standard and GPU interoperability · scientific
software reproducibility, verification and validation.

**Primary and near-primary sources consulted (selected):**
- **NumPy Enhancement Proposals** (NEP 47, NEP 56, and the roadmap) and the **Array API
  standard** documentation for the interoperability story; **Quansight Labs' and
  Quansight's engineering blogs** for the adoption state and benchmark figures;
  **CuPy's v14 release announcement**; scikit-learn's Array API documentation for the
  `numpy.linalg`/`scipy.linalg` dispatch subtlety
- **arXiv 2410.10908**, *"The State of Julia for Scientific Machine Learning"*, for the
  critical assessment — ⚠️ **I've quoted its conclusion because the enthusiastic case is
  much easier to find than the sceptical one**; TIOBE/JuliaHub figures via 2026 ecosystem
  write-ups; Hacker News practitioner discussion for the AOT-compilation critique
- **Reproducibility**: arXiv 2512.00651 for the >70% figure and the artifact-badge
  research; a 2026 review post citing **Nature's 2026 reproducibility special issue** and
  the Begley & Ellis / Ioannidis replication estimates; a **Frontiers (2025)** paper on
  scientific software in the AI era for the EU AI Act timing; ScienceDirect's
  reproducibility overview for the MKL conditional-reproducibility mechanism

**Confidence statement.** **Very high confidence** in §1 → `sci-floating-point-and-numerical-foundations`, §2 → `sci-floating-point-and-numerical-foundations`, §3 → `sci-floating-point-and-numerical-foundations`, §5–§13 → `sci-tooling-and-symbolic-computation`, `sci-linear-algebra-differential-equations-and-optimization`, `sci-statistics-performance-and-reproducibility` and §15 — this is
settled numerical analysis, consistently presented across the standard texts for decades,
and my confidence rests on that literature rather than on web sources. **High confidence in
the Array API material** (§17), which comes from NumPy's own NEPs and the implementing
teams' engineering blogs — ⚠️ **though the specific speedup multipliers (52×, 50×, 49×) are
benchmark-and-hardware-specific figures published by parties invested in the standard's
success, and should be read as "GPU dispatch can be transformative for the right workload"
rather than as a general expectation.**

⚠️ **Moderate confidence, and deliberately hedged, on §4.2 → `sci-tooling-and-symbolic-computation` and §16.1's Julia assessment.**
This is a domain with strong partisans on both sides; I have quoted a peer-reviewed
critical assessment alongside the adoption figures **specifically because the promotional
case is far easier to find**, and the download/package/TIOBE numbers come from ecosystem
write-ups rather than audited sources. **The reproducibility figures in §14 → `sci-statistics-performance-and-reproducibility` and §17 vary
substantially between studies and disciplines** — the 10–25% and ~50% estimates measure
different things in different fields and should not be combined or treated as a single
number; I have attributed each rather than averaging them. §16 is opinion labelled as such.
