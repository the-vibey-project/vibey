---
id: skill-agentic-ai-security-llm06-2025-owasp-asi-top-10-5e21a166f3
purpose: agentic ai security llm06 2025 owasp asi top 10
source: src/vibey_tools/skills/plugins/security-principles/skills/ai-security-practices/SKILL.md
requires: ["skill-rag-security-llm08-2025-f3c5605bc9"]
links: ["skill-mcp-security-new-under-secured-layer-baec8d2947"]
---

## Agentic AI Security (LLM06:2025 + OWASP ASI Top 10)

### Threat Classes
- Tool misuse, identity/privilege abuse, rogue agents
- Unexpected code execution (ASI05)
- Memory poisoning, resource overload, cascading hallucination
- Real CVEs: Claude Code data exfiltration via DNS (CVE-2025-55284); Cursor "AgentFlayer" via malicious Jira ticket

### Mandated Controls
1. **Least-privilege tool scoping** — the planner often needs no tools; scope each tool to only what it needs
2. **Sandboxing** — OWASP ASI: "Never execute agent-generated code without strict sandboxing, input validation, and allowlisting"
   - **Firecracker microVMs:** strongest isolation
   - **gVisor:** syscall-level isolation
   - **V8 isolates:** JS, latency-critical
3. **Default-deny reads** of `.env`/secrets
4. **Egress allow-lists** — not egress defaults
5. **Human approval gates** for high-stakes or irreversible actions
6. **Emergency kill switches** and circuit breakers
7. **Continuous behavioral monitoring**

**Note:** CVE-2025-59528 (CVSS 10.0) and the Google Antigravity sandbox escape confirm that app-level controls fail without isolated execution.

### Frameworks
- Progent (programmable privilege control)
- Microsoft Agent Governance Toolkit (April 2026)

---
