---
id: skill-22-gxp-validation-and-the-regulated-context-6768e4834f
purpose: 22 gxp validation and the regulated context
source: src/vibey_tools/skills/plugins/medicine-design-software-development/skills/drugdev-pipeline-engineering-compute-and-regulated-software/SKILL.md
requires: ["skill-21-reproducibility-41703d4009"]
links: ["skill-23-software-as-a-medical-device-5346c65f41"]
---

## §22. ⚠️ GxP, Validation and the Regulated Context

> **⚠️ The mindset shift that catches software engineers: in a GxP environment, if it
> isn't documented, it didn't happen.**
```
⚠️ GxP  GLP (lab), GCP (clinical), GMP (manufacturing).
   ⚠️ Discovery research is usually NOT GxP; ⚠️ the moment output
   supports a regulatory submission, everything changes
⚠️ CSV / CSA  Computer System Validation — ⚠️ and FDA's Computer
   Software Assurance guidance deliberately shifts effort from
   exhaustive documentation toward RISK-BASED critical thinking
   and more actual testing
⚠️ GAMP 5 (2nd ed.)  the industry framework; ⚠️ software categories
   by risk; ⚠️ explicitly accommodates Agile and supplier leverage
⚠️ 21 CFR PART 11  electronic records and signatures. ⚠️ In practice:
   AUDIT TRAILS (who changed what, when, why — and they must not be
   disableable), access control, ⚠️ DATA INTEGRITY
⚠️ ALCOA+  Attributable, Legible, Contemporaneous, Original, Accurate
   (+ Complete, Consistent, Enduring, Available). ⚠️ The data
   integrity standard, and a genuinely good checklist for ANY
   scientific data system
```
**⚠️ What this means for how you build**: ⚠️ **requirements traceability from user
requirement through design to test; ⚠️ change control; ⚠️ IQ/OQ/PQ qualification;
periodic review; and supplier assessment for anything you didn't write.**
**⚠️ The honest engineering advice**: ⚠️ **decide EARLY whether a system will ever be GxP,
because retrofitting audit trails and traceability onto a research codebase is far more
expensive than building them in.** **⚠️ And keep the GxP boundary as small as you can —
validate the system that produces the submitted number, not the entire research
platform.**

---
