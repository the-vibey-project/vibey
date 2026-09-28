---
id: skill-section-1-modern-framework-updates-what-changed-2024-2025-6e9007474a
purpose: section 1 modern framework updates what changed 2024 2025
source: src/vibey_tools/skills/plugins/security-principles/skills/ai-era-security/SKILL.md
requires: ["skill-quick-reference-principle-efda402f1d"]
links: ["skill-section-2-ai-threat-landscape-aabc5d33bb"]
---

## SECTION 1 — Modern Framework Updates (What Changed 2024–2025)

### NIST CSF 2.0 (Feb 26, 2024)
First major revision since 2014. Headline change: sixth core function **Govern (GV)** added to Identify, Protect, Detect, Respond, Recover.

- 6 functions / 22 categories / 106 subcategories
- Govern (GV) contains 31 of 106 subcategories (~29%) covering organizational context, risk strategy, roles, policy, oversight, supply-chain risk management
- **Doubled supply-chain subcategories (GV.SC) from 5 to 10** (10 of 106, ~9.4%)
- Scope expanded from critical infrastructure to all organizations
- CSF 2.0 is now the lingua franca mapping to ISO 27001, CIS Controls, and NIST 800-53

**Why it matters:** Governance and C-SCRM are now first-class board-level concerns, not IT concerns.

### CIS Controls v8.1 (June 25, 2024)
Iterative update aligning to NIST CSF 2.0.

- 18 Controls, 153 Safeguards, 3 Implementation Groups (IG1/IG2/IG3)
- New **Governance** security function added
- New **Documentation** asset class added
- Per the CIS Community Defense Model, full implementation defends against ~86% of MITRE ATT&CK (sub-)techniques
- Best starting point for operational hardening — more prescriptive than CSF

### ISO/IEC 27001:2022
Restructured Annex A into 4 themes (Organizational, People, Physical, Technological) and 93 controls total, with 11 new controls including:
- Threat intelligence
- Cloud security
- Data leakage prevention (DLP)
- Secure coding

Transition deadline: certifications against the 2013 version expired during the transition window ending in 2025.

### Modern IAM Gold Standards
- **Phishing-resistant MFA gold standard: FIDO2/WebAuthn and PKI (PIV/CAC).** CISA explicitly names these as gold standard; SMS, OTP, and push are phishable.
- **Prompt bombing appeared in 14% of incidents** per Verizon 2025 DBIR, and was the most common MFA-bypass technique, appearing in >20% of social-engineering breaches involving MFA bypass.
- **NIST SP 800-63-4 (finalized 2025)** makes phishing-resistant authentication mandatory at AAL3 (hardware-bound, non-exportable keys; syncable passkeys are NOT permitted at AAL3). The mechanism: **origin binding** — the authenticator cryptographically refuses to respond to a spoofed domain.
- **Passkeys:** device-bound for privileged/admin; synced for general workforce. Natively supported across Apple/Google/Microsoft.
- **Zero standing privileges** with just-in-time, time-boxed elevation (JIT PAM). Gold-standard vendor: CyberArk.

### CNAPP Consolidation
CNAPP (Cloud-Native Application Protection Platform) unifies CSPM + CWPP + CIEM + DSPM + KSPM + IaC scanning.

Market leaders:
- **Wiz** (agentless, Security Graph; acquired by Google for ~$32B, closed 2026)
- **Palo Alto Prisma/Cortex Cloud**
- **CrowdStrike Falcon Cloud Security**
- **Microsoft Defender for Cloud**
- **Orca Security**

DSPM (Data Security Posture Management) discovers/classifies sensitive data (PII/PHI/PCI), maps data flows and exposure paths, and ties data risk to identity and infrastructure context.

### Software Supply Chain Security
The mature, vendor-neutral stack:
- **SLSA** (Supply-chain Levels for Software Artifacts, v1.0) — build provenance; target SLSA Level 3+
- **Sigstore** (Cosign for signing, Fulcio for keyless OIDC-based certs, Rekor transparency log) — artifact signing
- **SBOMs** (SPDX/CycloneDX) — component inventory
- **in-toto/DSSE** — attestation envelopes

Scale of threat: **Sonatype discovered 454,648 new malicious open-source packages in 2025** (cumulative: 877,522+ since 2019). Threats evolved from "spam and stunts" into "sustained, industrialized campaigns."

**Critical rule: pin dependencies by commit SHA, not tag.**

Watershed events: GhostAction GitHub Actions compromise, Ultralytics PyPI compromise.

### Ransomware Resilience
**3-2-1-1-0 backup rule:** 3 copies, 2 media types, 1 offsite, 1 offline/immutable/air-gapped, 0 errors after verification.

---
