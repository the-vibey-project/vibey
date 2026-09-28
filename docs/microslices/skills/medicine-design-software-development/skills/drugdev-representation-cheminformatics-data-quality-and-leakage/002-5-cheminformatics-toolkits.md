---
id: skill-5-cheminformatics-toolkits-8954017c08
purpose: 5 cheminformatics toolkits
source: src/vibey_tools/skills/plugins/medicine-design-software-development/skills/drugdev-representation-cheminformatics-data-quality-and-leakage/SKILL.md
requires: ["skill-4-molecular-representation-4afd15eaca"]
links: ["skill-6-data-sources-and-their-quality-3f8edd33f7"]
---

## §5. Cheminformatics Toolkits

**⚠️ RDKit is the default and effectively the field's standard library** — **open source,
Python and C++, covering parsing, standardization, descriptors, fingerprints, substructure
search, conformer generation, reaction handling and visualization.**
**⚠️ Others**: **OpenBabel (format conversion), CDK (Java), ChemAxon and OpenEye
(commercial, strong in specific areas), Datamol (RDKit ergonomics).**
**⚠️ Substructure and similarity search**: ⚠️ **SMARTS for pattern matching; Tanimoto
similarity on fingerprints; ⚠️ and the crucial caveat that "similar" by Tanimoto does not
mean similar in activity** (§13 → `drugdev-qsar-admet-generative-models-and-validation`'s activity cliffs).
**⚠️ Practical engineering notes**: ⚠️ **RDKit is not thread-safe in all operations, mol
objects don't pickle trivially across versions, and ⚠️ RDKit version changes can alter
descriptor values — so pin the version and record it** (§21 → `drugdev-pipeline-engineering-compute-and-regulated-software`).

---
