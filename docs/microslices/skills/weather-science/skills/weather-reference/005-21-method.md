---
id: skill-21-method-1524cfa121
purpose: 21 method
source: src/vibey_tools/skills/plugins/weather-science/skills/weather-reference/SKILL.md
requires: ["skill-20-quick-reference-da80c0ac31"]
links: []
---

## §21. Method

**§1–§14 → `weather-atmosphere-radiation-thermodynamics-and-moisture`, `weather-dynamics-circulation-and-synoptic`, `weather-severe-storms-cyclones-and-boundary-layer`, `weather-observation-nwp-verification-and-machine-learning` and §16–§18 → `weather-observation-nwp-verification-and-machine-learning` rest on settled atmospheric physics** — hydrostatic and geostrophic
balance, thermodynamics, cloud microphysics, baroclinic instability, and **Lorenz
(1963)** — sourced from the references in §19, chiefly **Wallace & Hobbs**, **Holton &
Hakim**, **Markowski & Richardson**, and **Kalnay** for §12 → `weather-observation-nwp-verification-and-machine-learning` and §14 → `weather-observation-nwp-verification-and-machine-learning`. ⚠️ **None of that
needed verification; it has been stable for decades.**

**Two searches were run in August 2026**, both on §15 → `weather-observation-nwp-verification-and-machine-learning` — **the state of ML weather
prediction** and **its documented limitations.**

**Confidence.** **High** in §1–§14 → `weather-atmosphere-radiation-thermodynamics-and-moisture`, `weather-dynamics-circulation-and-synoptic`, `weather-severe-storms-cyclones-and-boundary-layer`, `weather-observation-nwp-verification-and-machine-learning` and §16–§18 → `weather-observation-nwp-verification-and-machine-learning`. **High** in §15 → `weather-observation-nwp-verification-and-machine-learning`'s factual claims, which
came out unusually well-sourced for a fast-moving area: **peer-reviewed primary literature**
(**Nature** for GenCast, **Science Advances** for the extremes result, **Geoscientific
Model Development** for AIFS, **npj Artificial Intelligence** for the assimilation review),
plus **ECMWF's own publications** and multiple **arXiv** evaluations.

⚠️ **What I want to flag is not uncertainty but a genuine disagreement in the field, and
I've deliberately given both sides rather than resolving it.** **The headline result — ML
ensembles surpassing ECMWF's ENS at a fraction of the cost — is real and comes from
peer-reviewed work.** **The counter-result — physics-based HRES still winning on
record-breaking extremes, with a proposed mechanism (an implicit ceiling from the training
distribution) — is also real and also peer-reviewed.** ⚠️ **One assessment I found put it
sharply: the accuracy headline contradicts the extremes evidence, and both camps know it.**

**⚠️ §15.3 → `weather-observation-nwp-verification-and-machine-learning` is my own synthesis of why they can both be right**, and I think it's the most
useful thing in the section: **RMSE structurally rewards smoothing (§13 → `weather-observation-nwp-verification-and-machine-learning`'s double-penalty
problem), so a model optimized against it can be genuinely better on average and
genuinely worse in the tail.** **That is not a contradiction; it's a consequence of the
objective function.** ⚠️ **The existence of work on fair extremes comparison — weighted
potential CRPS — is the field acknowledging the same thing.**

**One sourcing caution**: ⚠️ **claims like "AI outperforms on 90% of metrics" come from
vendor-adjacent and popular sources, and §15.3 → `weather-observation-nwp-verification-and-machine-learning` is the reason to distrust that framing.**
**The peer-reviewed claims are narrower and better specified, and I have used those.**
**The single most checkable fact in §15 → `weather-observation-nwp-verification-and-machine-learning`, and the one I'd anchor on: as of 2026 no major
meteorological agency has decommissioned its NWP system.**
