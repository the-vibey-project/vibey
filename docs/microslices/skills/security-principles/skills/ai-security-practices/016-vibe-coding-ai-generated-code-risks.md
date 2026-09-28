---
id: skill-vibe-coding-ai-generated-code-risks-29ad309f77
purpose: vibe coding ai generated code risks
source: src/vibey_tools/skills/plugins/security-principles/skills/ai-security-practices/SKILL.md
requires: ["skill-supply-chain-security-sbom-sigstore-provenance-cfd3213d9f"]
links: ["skill-ai-threat-modeling-frameworks-6d52cddeff"]
---

## Vibe Coding / AI-Generated Code Risks

**The data (multiple independent sources, 2025–2026):**
- **Veracode (July 2025):** 45% failure rate on security tests; XSS failing 86%, log injection 88%; rate "virtually identical to where it stood two years ago" as of Spring 2026
- **Apiiro (Sept 2025):** 10× spike in security findings (10,000+/month by June 2025); 3–4× more commits; privilege-escalation paths +322%, architectural design flaws +153%
- **CodeRabbit:** AI-co-authored PRs had ~1.7× more major issues, 2.74× more security flaws
- **Tenzai (Dec 2025):** 5/5 AI agents introduced SSRF; 0/15 apps had CSRF protection or security headers
- **IEEE-ISTAS:** +37.6% critical vulns after 5 rounds of AI refinement (iteration compounds flaws)
- **Slopsquatting:** attackers pre-register hallucinated package names

### Mitigations
1. Mandatory human review gates for AI-generated PRs
2. Strict AI "rule files" (ban `eval`, require env vars + parameterized queries)
3. Secret-scanning pre-commit hooks
4. Enforce security at the infra layer (WAF/Zero Trust gateway) — SAST alone is insufficient
5. AI code review as a quality gate on AI-generated code (CodeRabbit, Greptile, etc.)

---
