---
id: skill-20-method-49a09fe19f
purpose: 20 method
source: src/vibey_tools/skills/plugins/biomedical-engineering-technical/skills/biomed-reference/SKILL.md
requires: ["skill-19-quick-reference-18fbc49110"]
links: []
---

## §20. Method

**This is the technical layer only.** Regulatory pathways, quality management, and software
lifecycle process were deliberately excluded on request — they are a large separate subject
and would have displaced the engineering content.

**Sources.** §1–§15 → `biomed-signals-and-medical-imaging`, `biomed-clinical-data-ml-and-bioinformatics`, `biomed-structural-systems-biology-and-pharmacology`, `biomed-biomechanics-devices-and-biostatistics` rest on the standard textbook and primary literature listed in §18 —
**Guyton & Hall, Sörnmo & Laguna, Prince & Links, Durbin et al., Alon, Rowland & Tozer,
Keener & Sneyd, Fung, Ratner, Harrell** — plus foundational primary results
(**Hodgkin & Huxley 1952, Pan & Tompkins 1985, Michaelis & Menten 1913, Bland & Altman
1986, Cox 1972**). **None of this has a currency dependency and none was web-verified**;
the physics, physiology and mathematics are settled and the textbooks are the authority.

**Confidence.** **High** throughout §1–§15 → `biomed-signals-and-medical-imaging`, `biomed-clinical-data-ml-and-bioinformatics`, `biomed-structural-systems-biology-and-pharmacology`, `biomed-biomechanics-devices-and-biostatistics`. The equations are standard and stated with
their assumptions; the numerical ranges in §17 are **representative physiological and
engineering values, not specifications** — normal ranges vary by lab, population and
method, and should be taken as orientation rather than reference intervals.

⚠️ **Two areas carry real caveats.** **Tool recommendations in §19.2** (nnU-Net, BWA-MEM,
DESeq2, minimap2) reflect what has been the durable default for several years, but
**bioinformatics tooling turns over faster than the rest of this document** — verify
against current best-practice guides before committing a pipeline. And **§4.3 → `biomed-clinical-data-ml-and-bioinformatics`'s documented
failure cases** (shortcut features, the spending-as-need proxy) are drawn from the
published literature on model failure; **I have described the mechanisms, which generalize,
rather than adjudicating any specific system's current behaviour.**

**⚠️ Nothing here is clinical guidance.** The dosing, interval and physiological figures
are engineering orientation for people building systems, not a basis for patient care.
