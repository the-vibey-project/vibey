---
id: skill-15-biostatistics-afbf74cfb6
purpose: 15 biostatistics
source: src/vibey_tools/skills/plugins/biomedical-engineering-technical/skills/biomed-biomechanics-devices-and-biostatistics/SKILL.md
requires: ["skill-14-lab-automation-and-instrumentation-841743ba70"]
links: []
---

## §15. Biostatistics

**⚠️ Study designs and what they can support**: RCT (causal), cohort, case-control
(⚠️ **efficient for rare outcomes; cannot estimate incidence**), cross-sectional,
crossover (⚠️ **within-subject, so it removes between-subject variance — powerful when
carryover can be excluded**).

**Survival analysis** — because **censoring** makes ordinary regression invalid:
**Kaplan–Meier** estimator, **log-rank test**, **Cox proportional hazards**
`h(t|X) = h₀(t)·exp(βᵀX)`. ⚠️ **Test the proportional hazards assumption (Schoenfeld
residuals) — it is routinely assumed and rarely checked, and crossing survival curves
invalidate it.**

**Mixed-effects models** — ⚠️ **the correct default for repeated measures and clustered
data**, which describes most biomedical data. `y = Xβ + Zu + ε`. **Treating repeated
measures as independent inflates the effective N and manufactures significance.**

**Multiple comparisons**: Bonferroni (conservative), ⚠️ **Benjamini–Hochberg FDR — the
standard in genomics, where you test 20,000 genes and controlling FWER would leave you
nothing.**

**⚠️ Effect size over p-values.** Report confidence intervals, and distinguish
**statistical from clinical significance** — with large N, trivial differences are
significant. **MCID (minimal clinically important difference)** is the relevant benchmark.

**Diagnostic accuracy**: sensitivity, specificity, **likelihood ratios**
(⚠️ **LR+ = Sens/(1−Spec); prevalence-independent and directly usable in Bayesian updating
of pre-test odds**), ROC and AUC, **and §4.1 → `biomed-clinical-data-ml-and-bioinformatics`'s prevalence dependence for PPV/NPV.**

**⚠️ Agreement is not correlation.** For method comparison use **Bland–Altman**
(difference vs mean, with limits of agreement), not `r` — ⚠️ **two methods can correlate at
r = 0.99 while one reads systematically double the other.** For categorical raters, use
**Cohen's/Fleiss' κ**; for continuous, **ICC**.
