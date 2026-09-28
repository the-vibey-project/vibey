---
id: skill-cybersecurity-incident-disclosure-framework-674b15fdab
purpose: cybersecurity incident disclosure framework
source: src/vibey_tools/skills/plugins/compliance-frameworks/skills/cmmc-cui/SKILL.md
requires: ["skill-sprs-score-submission-e7ddd5f015"]
links: ["skill-scoping-system-boundaries-for-cui-149f73e955"]
---

## Cybersecurity Incident Disclosure Framework

### What Triggers Reporting (DFARS 252.204-7012)
A cybersecurity incident must be reported when a contractor discovers an incident that:
- Affected or is reasonably suspected to affect a covered contractor information system (any system with CDI/CUI)
- Involves a compromise or potential compromise of CUI
- Includes exfiltration, manipulation, or destruction of CDI
- Affects ability to provide operationally critical support

**Reporting is required even if:**
- You are not certain a breach occurred (suspected incidents count)
- The incident was contained quickly
- No data was confirmed exfiltrated

### 72-Hour Reporting Requirement
From the moment of **discovery** (not confirmation), the contractor has **72 hours** to report to DoD.

**Where to report:** DoD Cyber Crime Center (DC3) via https://dibnet.dod.mil
**What to include in the report:**
- Company name, point of contact, and contract numbers affected
- Description of the incident (when, what systems, what data potentially affected)
- Indication whether the incident is ongoing
- Type of compromise (malware, unauthorized access, data exfiltration, etc.)
- Unique identifier of reported incident for tracking

**After reporting:**
- Preserve forensic images of compromised systems for 90 days
- Submit malware samples to DC3
- Provide damage assessment to prime contractor and contracting officer
- Continue to investigate and update report as findings develop


### Cybersecurity Disclosure Decision Tree

```
Did a security event occur on a system that has CUI or CDI?
├── No → Not a DFARS reportable incident (may still be internal IR)
└── Yes →
    Was the event a: malware infection, unauthorized access, data modification,
    exfiltration, or destruction affecting that system?
    ├── No (e.g., probe/scan that was blocked, no compromise) → Log internally;
    │   document why no compromise occurred; consider voluntary report
    └── Yes (or cannot confirm it DIDN'T happen) →
        ↳ REPORT WITHIN 72 HOURS to DC3 via DIBNet
        ↳ Preserve system images for 90 days
        ↳ Submit malware samples if applicable
        ↳ Notify prime contractor (if subcontractor)
        ↳ Notify contracting officer

Was a specific amount or type of CUI confirmed exfiltrated or compromised?
├── Unknown → Still report; describe what is known; update as investigation proceeds
└── Yes → Include data types and estimated scope in report; conduct damage assessment
```

### When NOT to Report (Common Misconceptions)
- A phishing email received but not clicked → Not required (no system compromise)
- A port scan from external IP that was blocked by firewall → Not required
- A user accidentally sent an email to wrong address with non-CUI content → Not required
- A failed login attempt (brute force blocked) → Not required unless account was compromised

**When in doubt: report.** Over-reporting is far preferable to under-reporting. False Claims Act risk applies to knowing failure to report, not to good-faith over-reporting.

---
