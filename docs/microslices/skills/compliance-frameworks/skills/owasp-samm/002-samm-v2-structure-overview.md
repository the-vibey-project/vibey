---
id: skill-samm-v2-structure-overview-2b58c0b11c
purpose: samm v2 structure overview
source: src/vibey_tools/skills/plugins/compliance-frameworks/skills/owasp-samm/SKILL.md
requires: ["skill-what-this-skill-does-3d8c33b745"]
links: ["skill-business-function-1-governance-1ec3586e42"]
---

## SAMM v2 Structure Overview

OWASP SAMM v2 organizes software security into a three-tier hierarchy:

```
5 Business Functions
  └── 3 Security Practices per function = 15 Practices total
        └── 2 Streams per practice = 30 Streams total
              └── 3 Maturity Levels per stream (0 = not started, 1 = foundational, 2 = structured, 3 = optimized)
```

**Overall score:** Average maturity across all 15 practices, ranging 0.0–3.0.

**Typical scores:**
- 0.0–0.5: Security is informal or absent
- 0.5–1.0: Beginning to establish basic practices
- 1.0–1.5: Foundational practices in place; inconsistently applied
- 1.5–2.0: Structured practices; most teams follow them
- 2.0–2.5: Mature, consistent, measured security program
- 2.5–3.0: Optimizing; continuous improvement; industry-leading

---
