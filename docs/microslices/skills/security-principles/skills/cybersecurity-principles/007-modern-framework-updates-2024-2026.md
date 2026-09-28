---
id: skill-modern-framework-updates-2024-2026-358ff98161
purpose: modern framework updates 2024 2026
source: src/vibey_tools/skills/plugins/security-principles/skills/cybersecurity-principles/SKILL.md
requires: ["skill-defense-in-depth-e93f580d0c"]
links: ["skill-financial-context-why-principles-violations-are-expensive-8a52bf8367"]
---

## Modern Framework Updates (2024–2026)

### NIST Cybersecurity Framework (CSF) 2.0 — February 2024

The first major revision since 2014. Headline change: a **sixth core function, Govern (GV)**, joining Identify, Protect, Detect, Respond, Recover.

- **Structure**: 6 functions, 22 categories, 106 subcategories
- **Govern contains 31 of the 106 subcategories (≈29%)** — six categories covering organizational context, risk strategy, roles, policy, oversight, and supply-chain risk management
- **CSF 2.0 doubled the supply-chain subcategories (GV.SC)** from five to ten (≈9.4% of all subcategories)
- **Scope expanded** from critical infrastructure to *all* organizations

**Why it matters**: governance and supply-chain risk are now first-class, board-level concerns. CSF 2.0 is the **lingua franca** that maps to ISO 27001, CIS Controls, and NIST SP 800-53. If someone asks what framework to use for board-level communication, the answer is CSF 2.0.

### CIS Controls v8.1 — June 2024

An iterative update to v8 that realigned to NIST CSF 2.0 by adding a **Governance** security function and a new **Documentation** asset class.

- **18 Controls, 153 Safeguards** across three Implementation Groups (IG1/IG2/IG3)
- Full implementation defends against **~86% of MITRE ATT&CK (sub-)techniques** per the CIS Community Defense Model
- **Best operational starting point** for hardening — more prescriptive than CSF 2.0

### ISO/IEC 27001:2022

The 2022 revision restructured Annex A into **4 themes** (Organizational, People, Physical, Technological) and **93 controls**, adding **11 new controls** including threat intelligence, cloud security, data leakage prevention, and secure coding. Organizations had a transition deadline — certifications against the 2013 version expired during the transition window ending in 2025. If someone is operating under ISO 27001, they should be on the 2022 version.

### Modern IAM gold standards

**Phishing-resistant MFA** is now the non-negotiable baseline:
- **FIDO2/WebAuthn** and **PKI (PIV/CAC)**: CISA's explicit "gold standard." The mechanism that matters is *origin binding* — the authenticator cryptographically refuses to respond to a spoofed domain.
- **Prompt bombing** appeared in **14% of incidents per Verizon 2025 DBIR** and over 20% of social-engineering breaches involving MFA bypass. SMS, OTP, and push notifications are all phishable.
- **NIST SP 800-63-4 (2025)** makes phishing-resistant authentication mandatory at AAL3 (hardware-bound, non-exportable keys). Syncable passkeys are not permitted at AAL3.
- **Passkeys** (device-bound for privileged/admin; synced for general workforce) are now natively supported across Apple/Google/Microsoft platforms.

**PAM (Privileged Access Management)**:
- Move to **zero standing privileges** with just-in-time, time-boxed elevation. Gold-standard vendor: CyberArk.
- Use **OAuth 2.0/PKCE** (authorization code flow); avoid implicit flow; short-lived scoped tokens.

### SASE (Secure Access Service Edge)

Convergence of SD-WAN + SWG + CASB + ZTNA + FWaaS. Per **Gartner's 2025 Magic Quadrant for SASE Platforms**, recognized leaders include:
- **Palo Alto Networks (Prisma SASE)**
- **Zscaler (Zero Trust Exchange)**
- **Netskope, Cato Networks, Cloudflare, Fortinet**

SASE is how Zero Trust architecture is operationally delivered for distributed workforces and hybrid environments.

### Incident response: NIST SP 800-61 Rev 3 (2025)

**Rev 3** reframes incident response around the CSF 2.0 functions (rather than the older standalone model).

**PICERL lifecycle** (SANS): Preparation, Identification, Containment, Eradication, Recovery, Lessons learned.

**3-2-1-1-0 backup rule for ransomware resilience**: 3 copies of data, 2 different media types, 1 offsite copy, 1 offline/immutable/air-gapped copy, 0 errors after verification.
