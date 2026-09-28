---
id: skill-section-5-documented-real-world-agentic-incidents-2025-2026-aecc3404b8
purpose: section 5 documented real world agentic incidents 2025 2026
source: src/vibey_tools/skills/plugins/security-principles/skills/ai-era-security/SKILL.md
requires: ["skill-section-4-owasp-agentic-top-10-december-2025-f698dac083"]
links: ["skill-section-6-controls-for-agentic-systems-4eacbc54c6"]
---

## SECTION 5 — Documented Real-World Agentic Incidents (2025–2026)

### EchoLeak (CVE-2025-32711, CVSS 9.3)
- **What:** First "zero-click" indirect prompt injection in Microsoft 365 Copilot enabling automatic data exfiltration via a single crafted email
- **Disclosed by:** Aim Labs to MSRC
- **Mechanism:** Malicious instructions in an email body caused Copilot to exfiltrate sensitive data to an attacker-controlled destination without any user action; Aim Labs termed it an "LLM Scope Violation"
- **Status:** Patched server-side; no confirmed in-the-wild exploitation
- **OWASP mapping:** ASI01 (Agent Goal Hijack), LLM01 (Prompt Injection)

### Morris II (March 2024)
- **What:** First self-replicating GenAI worm using an adversarial self-replicating prompt for zero-click propagation across email assistants
- **Researchers:** Cohen (Technion), Nassi (Cornell Tech), Bitton (Intuit)
- **Status:** Proof-of-concept; no in-the-wild exploitation confirmed
- **Significance:** Demonstrated autonomous AI-to-AI attack propagation without human interaction

### Agent Session Smuggling (October/November 2025)
- **What:** A malicious agent exploits a stateful Agent2Agent (A2A) session to inject covert instructions across turns
- **Disclosed by:** Palo Alto Networks Unit 42
- **Demonstrated:** Unauthorized stock trades proof-of-concept
- **Status:** Research PoC
- **OWASP mapping:** ASI07 (Insecure Inter-Agent Communication), ASI03 (Identity & Privilege Abuse)

### ServiceNow "BodySnatcher" (CVE-2025-12420, CVSS 9.3)
- **What:** Broken-auth flaw in ServiceNow Virtual Agent / Now Assist allowing an unauthenticated attacker to impersonate any user and drive privileged agentic workflows, bypassing MFA/SSO
- **Disclosed by:** Aaron Costello (AppOmni)
- **Status:** Patched; no confirmed exploitation
- **OWASP mapping:** ASI03 (Identity & Privilege Abuse), ASI09 (Human-Agent Trust Exploitation)

### MCP Ecosystem Vulnerabilities (2025)
- **CVE-2025-49596** — Anthropic MCP Inspector RCE, CVSS 9.4 (fixed in version 0.14.1)
- **Empirical study (2025):** 5.5% of 1,899 open-source MCP servers exhibited tool-poisoning vulnerabilities
- **Invariant Labs demo (April 2025):** WhatsApp MCP tool-poisoning data exfiltration
- **NSA MCP Security guidance** published May 2026 ("MCP: Security Design Considerations")
- **OWASP mapping:** ASI04 (Agentic Supply Chain), ASI02 (Tool Misuse)

---
