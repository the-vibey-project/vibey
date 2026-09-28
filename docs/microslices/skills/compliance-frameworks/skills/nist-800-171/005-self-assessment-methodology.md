---
id: skill-self-assessment-methodology-8c70848f7c
purpose: self assessment methodology
source: src/vibey_tools/skills/plugins/compliance-frameworks/skills/nist-800-171/SKILL.md
requires: ["skill-sprs-score-system-2a42f8675e"]
links: ["skill-poa-m-structure-33060b98cc"]
---

## Self-Assessment Methodology

### Step 1: Define System Boundary
- Identify all systems, networks, devices, and cloud services that process, store, or transmit CUI
- Document enclave boundary (what's in scope vs. out of scope)
- Map data flows for CUI: where does it enter, move, rest, and exit?
- Include all connected systems that could impact CUI confidentiality

### Step 2: Develop the System Security Plan (SSP)
- Document system name, purpose, boundary, and environment
- For each of the 110 controls: state MET, NOT MET, or NOT APPLICABLE with justification
- Describe how each met control is implemented (with specifics, not boilerplate)
- Required by 3.12.4; also required for DoD review under DFARS 252.204-7020

### Step 3: Collect Evidence
For each control, gather one or more of:
- **Examine:** Policies, procedures, configuration screenshots, system logs, network diagrams
- **Interview:** System owners, admins, security personnel (document responses)
- **Test:** Run scans, attempt access, verify configurations functionally

### Step 4: Gap Analysis
- List all NOT MET controls
- Categorize by family and by effort to remediate (quick win vs. major project)
- Calculate current SPRS score
- Identify highest-deduction gaps to prioritize

### Step 5: Build the POA&M
For each gap:
- Control ID and description
- Current weakness/deficiency
- Planned remediation action
- Milestones with target completion dates
- Responsible party
- Resources required (cost estimate)

### Step 6: Submit and Maintain
- Submit SPRS score reflecting current state (not target state)
- Update SSP and POA&M as controls are implemented
- Resubmit SPRS score after significant changes

---
