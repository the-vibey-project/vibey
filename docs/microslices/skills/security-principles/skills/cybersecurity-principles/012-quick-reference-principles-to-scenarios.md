---
id: skill-quick-reference-principles-to-scenarios-4685eeb41d
purpose: quick reference principles to scenarios
source: src/vibey_tools/skills/plugins/security-principles/skills/cybersecurity-principles/SKILL.md
requires: ["skill-the-three-structural-realities-of-all-security-work-872f6a0961"]
links: []
---

## Quick-reference: principles to scenarios

| Scenario | Which principle applies |
|----------|------------------------|
| Service account has admin access "just in case" | Least Privilege violation |
| Firewall allows all traffic by default | Fail-Safe Defaults violation |
| Internal CA used to sign certificates with no public scrutiny | Open Design / Kerckhoffs violation |
| Single person can approve and deploy production changes | Separation of Privilege violation |
| Authorization checked only at login, not per-request | Complete Mediation violation |
| 400-line custom auth library written in-house | Economy of Mechanism violation |
| All tenants share the same Redis cache instance | Least Common Mechanism concern |
| MFA required for every API call, causing developers to hard-code tokens | Psychological Acceptability failure |
| Flat network: once inside, move anywhere | Defense in Depth missing |
| Network location determines trust level | Zero Trust violation |
| AI agent uses admin credentials "for convenience" | Least Privilege violation (non-human identity) |
| Board asks for security framework language | NIST CSF 2.0 (Govern function) |
| Team needs operational hardening guidance | CIS Controls v8.1 (IG1 → IG2 → IG3) |
| Using SMS push for MFA on admin accounts | Phishing-resistant MFA violation (use FIDO2/passkeys) |
| MFA prompt bombing succeeds | Psychological Acceptability + phishing-resistant MFA violation |
