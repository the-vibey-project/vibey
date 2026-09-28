---
id: skill-the-three-core-truths-170fd88f9f
purpose: the three core truths
source: src/vibey_tools/skills/plugins/security-principles/skills/ai-security-practices/SKILL.md
requires: []
links: ["skill-owasp-llm-top-10-2025-edition-6ec23902cb"]
---

## The Three Core Truths

1. **Treat the LLM as an untrusted, internet-connected user.** Defense-in-depth (input validation + output sanitization at every boundary, least-privilege tool access, human-in-the-loop for high-impact actions) is the only viable posture, because prompt injection cannot be fully patched away.
2. **The biggest 2025–2026 attack-surface shifts are agentic AI and the framework deserialization layer.** The Next.js/React Server Components RCE (CVE-2025-55182 / CVE-2025-66478, CVSS 10.0, actively exploited within days) and the middleware auth-bypass (CVE-2025-29927, CVSS 9.1) show that "secure-by-default" frameworks still require continuous patching.
3. **AI-generated code is shipping security debt at scale.** Veracode (July 2025): 45% of AI-generated code samples failed security tests; XSS failing 86%, log injection 88%. Apiiro: 10,000+ new security findings/month (10× spike), privilege-escalation paths up 322%. GitGuardian: AI-assisted commits leak secrets at 3.2% vs 1.5% baseline.

---
