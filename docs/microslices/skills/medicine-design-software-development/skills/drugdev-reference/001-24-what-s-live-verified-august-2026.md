---
id: skill-24-what-s-live-verified-august-2026-1fd225292a
purpose: 24 what s live verified august 2026
source: src/vibey_tools/skills/plugins/medicine-design-software-development/skills/drugdev-reference/SKILL.md
requires: []
links: ["skill-25-misconceptions-96b1a13ef9"]
---

## §24. What's Live — verified August 2026

### 24.1 ⚠️ AI drug discovery meets clinical reality
**⚠️ 2026 is the year the evidence starts arriving, and the honest position is "promising
early, unproven where it counts."**

- **⚠️ The scale of the bet**: **reported ~$60B invested in the sector since 2019 (with
  broader life-science AI investment cited above $100B), ⚠️ around 173–175 AI-originated
  drug programmes have entered human trials, and ⚠️ NONE has yet received FDA approval.**
  ⚠️ **Industry estimates suggest 15–20 of those programmes could enter pivotal Phase III
  trials during 2026.**
- **⚠️ The encouraging number**: **published analyses report ⚠️ 80–90% Phase 1 success for
  AI-discovered molecules, against a historical industry average variously cited at
  ~40–65% or ~52%.** ⚠️ **Phase 2 success is reported around 40% — "based on a limited
  sample and broadly comparable to historical industry performance."**
- **⚠️ Timelines do appear compressed**: **reported candidates reaching human trials in
  under 18 months, versus a typical multi-year discovery phase.**

> **⚠️ GOTCHA — the selection-bias objection is strong and should be stated before the
> optimistic reading.** ⚠️ **The sample sizes are small and likely skewed, and early AI
> programmes may simply have selected EASIER TARGETS** — **a pattern one analysis notes
> is familiar from early monoclonal antibody development, "when initial success rates
> reflected careful target selection rather than technological superiority."**
> ⚠️ **The open question is whether the early-stage advantage COMPOUNDS or merely
> FRONT-LOADS the same attrition.** **⚠️ Phase 1 tests safety in healthy volunteers;
> good molecular design plausibly helps there. Phase 2 tests whether the biology was
> right, and design quality helps far less.**
> **⚠️ As one summary put it: biology does not care how cleverly you found your molecule.**

**⚠️ The current consensus position, stated carefully**: ⚠️ **"the evidence does not yet
show that AI materially changes the probability of surviving Phase 2 and Phase 3 testing."**
⚠️ **Clinical attrition remains around 90%, and Derek Lowe's observation is quoted across
sources — most failures still result from efficacy or safety issues that emerge only in
humans** (§1 → `drugdev-pipeline-targets-and-drug-likeness`). ⚠️ **A plausible outcome flagged by commentators is "accelerated timelines
without improved efficacy — commercially valuable but scientifically underwhelming."**
**⚠️ Sourcing caution: much of the enthusiastic coverage comes from vendors, consultancies
and AI-in-pharma trade outlets; the peer-reviewed narrative reviews are notably more
measured, and I've weighted toward those.**

### 24.2 ⚠️ The regulatory framework for AI arrived
**⚠️ This is the section that changes how you should BUILD, not just what you should
believe.**

- **⚠️ FDA published draft guidance on 6 January 2025** — ***Considerations for the Use of
  Artificial Intelligence To Support Regulatory Decision-Making for Drug and Biological
  Products*** — **establishing ⚠️ a risk-based CREDIBILITY ASSESSMENT FRAMEWORK.**
  ⚠️ **The comment period closed 7 April 2025 (reported extended), and final guidance is
  reported as expected in Q2 2026.**
- **⚠️ The central concept is CONTEXT OF USE (COU)**: ⚠️ **credibility is defined as
  "trust in the performance of an AI model for a particular context of use."** **⚠️ There
  is no such thing as a validated model in the abstract — only a model credible for a
  stated role in a stated decision.**
- **⚠️ The 7-step framework**, **as reported across sources:**
```
⚠️ 1. Define the QUESTION OF INTEREST — the specific regulatory question
⚠️ 2. Define the CONTEXT OF USE — the model's precise role and how its
      outputs influence decisions
⚠️ 3. Assess MODEL RISK — ⚠️ from MODEL INFLUENCE × DECISION CONSEQUENCE
      (a risk matrix; risk rises as either increases)
   4. Develop a CREDIBILITY ASSESSMENT PLAN proportionate to that risk
   5. Execute the plan
   6. Document results in a CREDIBILITY ASSESSMENT REPORT
⚠️ 7. Determine ADEQUACY for the context of use
```
- **⚠️ The critical scoping distinction for discovery teams**: ⚠️ **if AI is used to
  DISCOVER a drug but traditional validation confirms safety and efficacy, extensive AI
  documentation may not be required** — **the guidance targets AI that DIRECTLY SUPPORTS
  REGULATORY DECISION-MAKING.** **⚠️ So a generative model that proposed a molecule later
  validated conventionally is in a very different position from a model whose output
  substitutes for an experiment.**
- **⚠️ International alignment moved**: ⚠️ **on 14 January 2026 the FDA and EMA jointly
  published *Guiding Principles of Good Machine Learning Practice for Drug Development* —
  reported as ten high-level principles complementing the credibility framework.**
  **EMA's September 2024 Reflection Paper on AI in medicines runs in parallel.**
  ⚠️ **FDA also announced an AI-Enabled Optimization of Early-Phase Clinical Trials pilot,
  with an RFI published 29 April 2026.**

> **⚠️ GOTCHA — the engineering implications are concrete and they land on §19 → `drugdev-pipeline-engineering-compute-and-regulated-software`, §21 → `drugdev-pipeline-engineering-compute-and-regulated-software` and
> §22 → `drugdev-pipeline-engineering-compute-and-regulated-software`.** ⚠️ **A credibility assessment plan must describe model design, DATA STRATEGY,
> training methodology, performance metrics and evaluation methodology — and be
> submitted early, within a submission or on request during inspection.**
> **⚠️ That means: data provenance and versioning are regulatory artefacts, not
> engineering hygiene; ⚠️ the split strategy (§7 → `drugdev-representation-cheminformatics-data-quality-and-leakage`) is a documented decision you must
> defend; ⚠️ model versioning and the ability to reproduce a specific historical
> prediction are requirements; and ⚠️ "we retrained it and it's better now" is a change
> control event.**
> **⚠️ Sponsors are also expected to define a threshold or risk matrix for when a
> technology counts as AI under FDA's definition versus a complex decision tree —
> which is a governance question most teams have not answered.**

**⚠️ The honest caveat on all of this**: ⚠️ **the draft is a draft, a critical peer-reviewed
review of it exists in the literature, and the US policy environment around AI shifted
with the January 2025 executive order — so implementation detail is genuinely in motion.**
**⚠️ The DIRECTION, however, is stable and internationally converging: risk-proportionate,
context-of-use-anchored, documentation-heavy.** **⚠️ Build for that.**

---
