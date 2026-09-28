---
id: skill-key-new-requirements-in-pci-dss-v4-0-a080aded5a
purpose: key new requirements in pci dss v4 0
source: src/vibey_tools/skills/plugins/compliance-frameworks/skills/pci-dss-v4/SKILL.md
requires: ["skill-saq-selection-logic-77fc1baf16"]
links: ["skill-scoping-cde-connected-systems-out-of-scope-d5a4044985"]
---

## Key New Requirements in PCI DSS v4.0

### Customized Approach (New in v4.0)
Merchants may implement security controls differently from the defined requirements, provided they can demonstrate the objective is met. This is for mature organizations with strong risk management.

- Must document the customized implementation and perform a targeted risk analysis
- Must have controls reviewed by a QSA (not available for SAQ self-assessors)
- The defined approach (standard requirements) remains the default

### Targeted Risk Analysis (Multiple Requirements)
v4.0 introduces explicit requirements to perform a **Targeted Risk Analysis (TRA)** to justify the frequency of certain recurring activities (e.g., log review frequency, scan frequency, security control testing frequency). Organizations must document the analysis supporting their chosen intervals.

### 6.4.3 — Payment Page Script Integrity (Became mandatory April 2025)
For all payment pages that load scripts in the consumer's browser:
- Maintain an inventory of all scripts
- Have a method to confirm each script is authorized
- Have a method to confirm script integrity (e.g., Subresource Integrity hash, Content Security Policy)

**Who this affects most:** SAQ-A-EP merchants and any merchant with custom payment pages. This is a major new control targeting Magecart/formjacking attacks.

**Implementation approaches:**
- Subresource Integrity (SRI) tags on `<script>` elements
- Content Security Policy (CSP) header restricting script sources
- Runtime Application Self-Protection (RASP)
- Third-party script management tools

### 11.6.1 — Change and Tamper Detection for Payment Pages (Became mandatory April 2025)
- Deploy a mechanism to detect unauthorized modification of HTTP headers and payment page content
- Alert on changes to payment page scripts, forms, or redirects
- Review alerts at least weekly

**Implementation:** Tools like Reflectiz, Jscrambler, PerimeterX, or custom CSP violation reporting + monitoring.


### MFA Now Required for All CDE Access (Req 8.4.2)
v4.0 expanded MFA to require it for all access to the CDE — not just remote access. This includes:
- All non-console administrative access
- All access to the CDE from within a trusted network

### Password Requirements Updated (Req 8.3.6)
- Minimum password length increased from 7 to 12 characters
- Password change required if there is any suspicion of compromise

---
