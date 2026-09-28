---
id: skill-section-4-owasp-agentic-top-10-december-2025-f698dac083
purpose: section 4 owasp agentic top 10 december 2025
source: src/vibey_tools/skills/plugins/security-principles/skills/ai-era-security/SKILL.md
requires: ["skill-section-3-ai-security-frameworks-2024-2026-canon-d88b25468b"]
links: ["skill-section-5-documented-real-world-agentic-incidents-2025-2026-aecc3404b8"]
---

## SECTION 4 — OWASP Agentic Top 10 (December 2025)

Released December 9, 2025. Developed with 100+ security researchers; review board includes NIST, Microsoft AI Red Team, AWS, Oracle.

| ID | Risk | Real-World Example |
|----|------|--------------------|
| ASI01 | Agent Goal Hijack | EchoLeak (CVE-2025-32711) |
| ASI02 | Tool Misuse | Amazon Q |
| ASI03 | Identity & Privilege Abuse | — |
| ASI04 | Agentic Supply Chain Vulnerabilities | GitHub MCP exploit |
| ASI05 | Unexpected Code Execution | AutoGPT RCE |
| ASI06 | Memory & Context Poisoning | Gemini memory attack |
| ASI07 | Insecure Inter-Agent Communication | — |
| ASI08 | Cascading Failures | — |
| ASI09 | Human-Agent Trust Exploitation | — |
| ASI10 | Rogue Agents | Replit meltdown |

### ASI01 — Agent Goal Hijack
The agentic analog of prompt injection. An attacker redirects an agent's objective at runtime. EchoLeak (CVE-2025-32711) is the canonical example: a crafted email caused M365 Copilot to exfiltrate data automatically, with no user interaction.

### ASI02 — Tool Misuse
An agent invokes tools beyond their intended scope. Amazon Q incident demonstrated an agent using cloud-management tools it shouldn't have accessed. Defense: strict tool allowlisting, not blocklisting.

### ASI03 — Identity and Privilege Abuse
Agents inheriting excessive permissions, or attackers impersonating agents. Treat every agent as a non-human identity; apply same rigor as human privileged accounts.

### ASI04 — Agentic Supply Chain Vulnerabilities
Compromised MCP servers, plugins, or orchestration frameworks introduce malicious behavior. The GitHub MCP exploit demonstrated supply-chain compromise in an agentic context.

### ASI05 — Unexpected Code Execution
Agents that can write and execute code are vulnerable to unintended RCE. AutoGPT RCE is the documented example. Defense: sandbox all code execution environments.

### ASI06 — Memory and Context Poisoning
Attacking an agent's persistent memory to alter future behavior. The Gemini memory attack demonstrated poisoning that persisted across sessions. Defense: validate/bound agent memory; treat stored memory as untrusted input.

### ASI07 — Insecure Inter-Agent Communication
In multi-agent architectures, messages between agents lack authentication or integrity protection. Currently, both A2A and MCP protocols lack enforced token expiration and central verification.

### ASI08 — Cascading Failures
One agent's failure or compromise propagates to dependent agents. In multi-agent pipelines, a blast radius can span the entire system. Defense: circuit breakers, timeouts, and independent failure domains.

### ASI09 — Human-Agent Trust Exploitation
Social-engineering tactics adapted for AI agents — manipulating users into trusting malicious agent outputs, or agents into trusting manipulated human instructions.

### ASI10 — Rogue Agents
Agents that deviate from their intended objectives, whether due to manipulation or emergent behavior. The Replit meltdown is the documented example of runaway agent behavior.

---
