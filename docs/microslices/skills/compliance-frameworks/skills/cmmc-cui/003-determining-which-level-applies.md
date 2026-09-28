---
id: skill-determining-which-level-applies-6f5fabfa5e
purpose: determining which level applies
source: src/vibey_tools/skills/plugins/compliance-frameworks/skills/cmmc-cui/SKILL.md
requires: ["skill-cmmc-2-0-model-overview-64693050f9"]
links: ["skill-cui-identification-and-handling-4cebfae025"]
---

## Determining Which Level Applies

### Step 1: Do you have a DoD prime or subcontract?
- No → CMMC likely does not apply (check for other federal contracts via FAR)
- Yes → Continue

### Step 2: Does the contract involve FCI?
**Federal Contract Information (FCI)** = information provided by or generated for the government under a contract to develop or deliver a product or service to the government, not intended for public release.

If you have any DoD contract for goods or services, you almost certainly have FCI. → **Level 1 minimum**

### Step 3: Does the contract involve CUI?
**Controlled Unclassified Information (CUI)** = information the government creates or possesses (or that an entity creates or possesses on behalf of the government) that requires safeguarding per law, regulation, or government policy.

Check your contract for:
- DFARS 252.204-7012 clause (CUI handling and cyber incident reporting)
- The phrase "Controlled Unclassified Information" or "CUI" in the Statement of Work
- Data types like: technical drawings, specifications, export-controlled data (ITAR/EAR), sensitive program information, research data

If CUI is present → **Level 2 minimum**

### Step 4: Is this a critical program?
If the DoD Program Office has designated the acquisition as requiring Level 3, the contract will specify. This is rare and applies to highly sensitive defense programs.

---
