---
id: skill-21-plm-version-control-for-atoms-7c800c9e20
purpose: 21 plm version control for atoms
source: src/vibey_tools/skills/plugins/manufacturing-mechanical-engineering-for-software-devs/skills/mfg-dfm-metrology-plm-npi-and-what-transfers/SKILL.md
requires: ["skill-20-cad-cae-and-simulation-e1fad5f2a0"]
links: ["skill-22-physical-supply-chain-bf1127fc91"]
---

## §21. ⚠️ PLM — Version Control for Atoms

> **⚠️ The section software people find most immediately legible, and the comparison is
> instructive in both directions.**
```
⚠️ PART NUMBERS  ⚠️ the immutable identifier. A part number identifies
   a specific, fully-specified thing
⚠️ REVISIONS  ⚠️ Rev A, B, C. ⚠️ THE RULE: if the change makes the new
   part NON-INTERCHANGEABLE with the old, it needs a NEW PART NUMBER,
   not a revision. ⚠️ This is semantic versioning with real consequences,
   because the old part physically exists in warehouses and in the field
⚠️ BOM (Bill of Materials)  ⚠️ the dependency tree. Multi-level,
   with quantities. ⚠️ EBOM (as designed) vs MBOM (as manufactured)
   vs ⚠️ AS-BUILT (what THIS serial number actually contains)
⚠️ ECO / ECN (Engineering Change Order/Notice)  ⚠️ the formal change
   process: what changes, why, effectivity date, disposition of
   existing stock, and approvals
⚠️ EFFECTIVITY  ⚠️ from which serial number or date the change applies.
   ⚠️ There is no "deploy to all users" — the old version stays in
   the field for its entire service life
```
**⚠️ Where the software analogy holds**: **version control, dependency trees, semantic
versioning, change review, release management.**
> **⚠️ GOTCHA — where it BREAKS, and this is the important half.**
> ⚠️ **You cannot roll back atoms.** **⚠️ Every previous revision physically exists — in
> inventory, in transit, in customers' hands — potentially for decades.** **⚠️ A change must
> therefore specify what happens to existing stock (use up, rework, scrap) and whether
> field units need retrofit.**
> **⚠️ There is no "everyone's on the latest version." Spares must be supportable for the
> product's whole service life, which is why part numbering discipline is treated as
> seriously as it is.**

---
