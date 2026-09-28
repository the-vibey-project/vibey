---
id: skill-cui-identification-and-handling-4cebfae025
purpose: cui identification and handling
source: src/vibey_tools/skills/plugins/compliance-frameworks/skills/cmmc-cui/SKILL.md
requires: ["skill-determining-which-level-applies-6f5fabfa5e"]
links: ["skill-key-dfars-clauses-c2008028b0"]
---

## CUI Identification and Handling

### What Is CUI?
CUI is defined by Executive Order 13556 and managed by the National Archives (NARA) CUI Registry (https://www.archives.gov/cui). It is NOT classified information — it is sensitive unclassified information.

**Common CUI Categories in the Defense Industrial Base:**
- **CTI** (Controlled Technical Information): Technical documents, engineering drawings, specifications
- **ITAR/EAR**: Export-controlled technology and data (International Traffic in Arms Regulations / Export Administration Regulations)
- **Privacy/PII**: Personally Identifiable Information related to DoD personnel
- **Naval Nuclear Propulsion**: Highly sensitive nuclear information
- **Critical Infrastructure**: Information about critical facilities or systems
- **Law Enforcement**: Sensitive law enforcement information

### CUI Marking Requirements
CUI must be marked with the appropriate designation. At minimum, documents should include:
- "CUI" banner marking at top and bottom of each page
- The CUI category designation (e.g., "CUI//CTI")
- Distribution/dissemination controls if applicable (e.g., "FEDCON" — distribute only to federal employees and contractors)

**Digital files:** Should be labeled in metadata, file names, or document headers where possible.
**Email:** Subject line or body should include CUI marking when transmitting CUI.

### CUI Handling Requirements
- Store only in systems that meet NIST 800-171 requirements
- Encrypt CUI at rest and in transit
- Limit access to individuals with need-to-know
- Do not store CUI on personal devices unless device meets security requirements
- Destroy CUI per NIST 800-88 (media sanitization) when no longer needed
- Report unauthorized disclosure immediately (see incident reporting below)


---
