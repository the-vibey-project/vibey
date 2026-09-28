---
id: skill-29-method-1cefc60924
purpose: 29 method
source: src/vibey_tools/skills/plugins/medicine-design-software-development/skills/drugdev-reference/SKILL.md
requires: ["skill-28-quick-reference-633c11751a"]
links: []
---

## §29. Method

**§1–§23 → `drugdev-pipeline-targets-and-drug-likeness`, `drugdev-representation-cheminformatics-data-quality-and-leakage`, `drugdev-protein-structure-docking-and-molecular-dynamics`, `drugdev-qsar-admet-generative-models-and-validation`, `drugdev-pipeline-engineering-compute-and-regulated-software` rests on established cheminformatics, structural biology, computational chemistry
and regulated-software practice** — **molecular representation, force fields and free
energy theory, QSAR methodology, and the GxP/GAMP/21 CFR Part 11 framework.** ⚠️ **The
split-leakage problem and the docking scoring limitation have both been documented
consistently for many years and needed no verification.**

**Two searches were run in August 2026**, on **AI drug discovery clinical evidence** and
**the FDA regulatory framework** — ⚠️ **the first because the field's central empirical
claim is now being tested, the second because it changes how these systems must be built.**

**Confidence.** **High** in §7 → `drugdev-representation-cheminformatics-data-quality-and-leakage` and §17 → `drugdev-qsar-admet-generative-models-and-validation`, which are the sections I'd most want read.
⚠️ **Random splitting on clustered chemical data is the field's defining methodological
failure, and the repeated independent finding that a random forest on ECFP fingerprints
matches elaborate architectures once splits are fixed is the single most useful sanity
check available.** **§6 → `drugdev-representation-cheminformatics-data-quality-and-leakage`'s noise-floor point is the companion: a model reporting error below
the experimental measurement error is fitting something other than chemistry.**

**High** in §10 → `drugdev-protein-structure-docking-and-molecular-dynamics`'s docking assessment and §12 → `drugdev-protein-structure-docking-and-molecular-dynamics`'s FEP framing — ⚠️ **both are long-standing,
well-characterized limitations that vendors consistently understate.**

**Moderate-to-high** on §24.1. ⚠️ **The structural facts — roughly 173–175 AI-originated
programmes in trials, zero approvals, ~90% overall clinical attrition — are consistent
across every source including the peer-reviewed reviews.** ⚠️ **The 80–90% Phase 1 figure
appears widely but rests on a small sample (one source traces it to 24 molecules through
December 2023), and the comparison baseline varies between sources (~40–65% vs ~52%),
which alone should induce caution.** **⚠️ I've given the selection-bias objection prominence
because it is the strongest argument in the debate and comes from the more sceptical
sources, and because the enthusiastic coverage is dominated by vendors and trade outlets
with obvious interests.** **⚠️ My own read is that the Phase 1 advantage is plausible on
mechanism — molecular design quality should help with safety in healthy volunteers — and
that Phase 2 is where the claim actually gets tested.**

**High** on §24.2's framework, which traces to FDA's own published guidance and is
corroborated by multiple independent law-firm and industry analyses. ⚠️ **The seven steps,
the context-of-use concept, the model-influence × decision-consequence risk matrix, and
the credibility assessment plan and report are all from primary or near-primary sources.**
⚠️ **The Q2 2026 finalization date and the January 2026 FDA–EMA joint principles are
reported rather than confirmed by me against a primary document, and the guidance remains
a DRAFT — so I'd verify current status before relying on specifics.** **⚠️ The engineering
implications I've drawn in the gotcha box are my inference from the documentation
requirements, not language quoted from the guidance.**
