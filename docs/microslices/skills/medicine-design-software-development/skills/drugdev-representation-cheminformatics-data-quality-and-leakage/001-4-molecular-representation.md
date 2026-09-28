---
id: skill-4-molecular-representation-4afd15eaca
purpose: 4 molecular representation
source: src/vibey_tools/skills/plugins/medicine-design-software-development/skills/drugdev-representation-cheminformatics-data-quality-and-leakage/SKILL.md
requires: []
links: ["skill-5-cheminformatics-toolkits-8954017c08"]
---

## §4. Molecular Representation

```
⚠️ SMILES  text. ⚠️ NON-CANONICAL by default — the same molecule has many
   valid strings, so ALWAYS canonicalize before deduplicating or joining
⚠️ InChI / InChIKey  ⚠️ canonical by construction; the right key for
   database joins. ⚠️ Note tautomer and stereochemistry layer subtleties
SELFIES  ⚠️ every string is a VALID molecule — useful for generative
   models because it removes invalid-output failure modes (§15)
⚠️ MOLECULAR GRAPHS  atoms as nodes, bonds as edges. ⚠️ The natural
   representation, and what GNNs consume
FINGERPRINTS  ⚠️ ECFP/Morgan (circular, the workhorse), MACCS,
   RDKit, Avalon. ⚠️ Fast, interpretable-ish, and still competitive
   with deep learning on many tasks (§13)
DESCRIPTORS  computed physicochemical properties (logP, TPSA, etc.)
3D CONFORMERS  ⚠️ molecules are FLEXIBLE — a single 3D structure is a
   choice, and conformer generation is its own problem
```
> **⚠️ GOTCHA — the representation problems that silently corrupt datasets:**
> ⚠️ **TAUTOMERS (the same compound written in different protomeric forms will not match),
> STEREOCHEMISTRY (frequently missing or wrong in public data, and enantiomers can differ
> by orders of magnitude in activity), SALTS AND SOLVATES (strip counterions), and
> PROTONATION STATE at physiological pH (which is often not what's in the file).**
> **⚠️ A standardization pipeline is not optional infrastructure — it is the first thing
> you build.**

---
