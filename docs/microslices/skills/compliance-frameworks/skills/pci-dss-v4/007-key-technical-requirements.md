---
id: skill-key-technical-requirements-9878ff16ea
purpose: key technical requirements
source: src/vibey_tools/skills/plugins/compliance-frameworks/skills/pci-dss-v4/SKILL.md
requires: ["skill-scoping-cde-connected-systems-out-of-scope-d5a4044985"]
links: ["skill-assessment-types-qsa-vs-isa-vs-self-assessment-522027cc2e"]
---

## Key Technical Requirements

### TLS Minimum Version (Req 4.2.1)
- TLS 1.2 is the minimum; TLS 1.3 preferred
- SSL and TLS 1.0 are prohibited
- TLS 1.1 was deprecated — confirm removal
- Test with: `nmap --script ssl-enum-ciphers -p 443 <host>` or SSL Labs

### Multi-Factor Authentication (Req 8.4)
- Required for all non-console admin access into CDE
- Required for all remote access to CDE
- Required for all access into CDE from untrusted networks
- Acceptable methods: TOTP, hardware tokens, push-based (Duo), biometric

### WAF Requirement (Req 6.4.2)
- Web Application Firewall required for all public-facing web applications
- Must be active (blocking mode) or under active monitoring
- Must be updated to address new threats
- Options: AWS WAF, Cloudflare WAF, Imperva, Akamai Kona, F5 AWAF

### Logging and Monitoring (Req 10)
- Audit trails required for all CDE systems
- Must capture: user ID, event type, date/time, success/failure, origination, affected component
- Logs must be protected from modification (write-once storage or SIEM)
- Daily log review required (can be automated)
- Retain logs minimum 12 months; 3 months immediately available

### Vulnerability Scanning (Req 11.3)
- Quarterly internal vulnerability scans
- Quarterly external scans by an ASV (Approved Scanning Vendor)
- After significant changes, rescan
- High/critical vulnerabilities must be remediated; rescan to confirm

### Penetration Testing (Req 11.4)
- Annual external penetration test of CDE
- Annual internal penetration test of CDE
- After significant changes or infrastructure upgrades
- Must follow industry-accepted methodology (PTES, OWASP, NIST)
- Segmentation controls must be tested at least every 6 months


---
