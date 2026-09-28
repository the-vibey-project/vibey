---
id: skill-mcp-security-new-under-secured-layer-baec8d2947
purpose: mcp security new under secured layer
source: src/vibey_tools/skills/plugins/security-principles/skills/ai-security-practices/SKILL.md
requires: ["skill-agentic-ai-security-llm06-2025-owasp-asi-top-10-5e21a166f3"]
links: ["skill-secrets-management-for-ai-services-7902448662"]
---

## MCP Security (New, Under-Secured Layer)

**Current state (Bitsight Research, December 2025):** ~1,000 MCP servers exposed on the public internet with no authorization controls — some allowing Kubernetes cluster command execution, CRM access, and arbitrary shell commands.

### Documented Threats
- **Tool poisoning:** malicious MCP server returns harmful tool definitions
- **Rug pulls:** tool behavior changes after trust is established
- **Tool/ghost shadowing:** malicious tool impersonates legitimate one
- **Command injection:** CVE-2025-49596 (MCP-Inspector, fixed in 0.14.1)
- **Confused-deputy attacks**
- First malicious MCP package appeared September 2025

### Controls
- OAuth-enhanced tool definitions + policy-based access control (ETDI)
- Gateway/proxy with authentication
- Audit logging of all tool calls
- Secret management for MCP server credentials
- Human-in-the-loop for tool calls accessing sensitive systems
- References: NSA MCP guidance (May 2026), OWASP MCP Top 10, CISA joint guidance (May 22, 2025)

---
