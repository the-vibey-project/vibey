---
id: skill-section-8-10-point-agentic-security-design-checklist-9a315ee0f1
purpose: section 8 10 point agentic security design checklist
source: src/vibey_tools/skills/plugins/security-principles/skills/ai-era-security/SKILL.md
requires: ["skill-section-7-post-quantum-cryptography-pqc-401de13328"]
links: ["skill-threat-modeling-reference-stride-applied-to-ai-agents-6b9d6c6fee"]
---

## SECTION 8 — 10-Point Agentic Security Design Checklist

Apply this checklist to every agentic system before production deployment.

**1. Non-human identity with human sponsor**
Every agent has a registered identity (Entra Agent ID or equivalent), a named human sponsor who owns accountability, and scoped short-lived credentials — no standing broad permissions.

**2. Least privilege + complete mediation**
Validate every tool call against policy in a deterministic layer outside the LLM. Allowlist permitted tools and egress domains. Apply Saltzer & Schroeder's Complete Mediation principle: every access, every time.

**3. Treat prompt as hostile, output as untrusted**
Apply input filtering before the LLM and output validation after. Check groundedness. Never trust that the model will enforce security constraints itself.

**4. Blast-radius containment**
Sandbox all tool execution in isolated environments. Segment agent permissions so one compromised agent cannot pivot. Cap spend and request rate to defend against Denial of Wallet (LLM10: Unbounded Consumption).

**5. Human-in-the-loop for irreversible/high-stakes actions**
Define which actions require human confirmation before execution. Automate the reversible; gate the irreversible. This is the highest-leverage single control against runaway agent behavior (ASI10).

**6. XPIA defense across all data ingestion paths**
Treat every document, email, web page, database row, and tool output as potentially adversarial. Do not blindly pass retrieved content into the agent context as instructions. Validate, sanitize, and isolate untrusted external content from instructions.

**7. Memory protection**
Validate and bound agent memory at read and write. Protect against context poisoning (ASI06) — stored memory is an attack surface, not a trusted source. Treat retrieved memory as untrusted input requiring the same scrutiny as external data.

**8. Inter-agent authentication and trust boundaries**
Sign inter-agent messages. Enforce mutual authentication between agents. Define explicit trust boundaries. Use time-boxed tokens. Do not assume messages from other agents are trustworthy by virtue of origin.

**9. Audit logging and observability for all agent actions**
Log all prompts (or prompt hashes), tool calls, parameters, responses, and decisions. This is non-negotiable for incident response and for detecting drift or rogue behavior. LLM observability platforms (Langfuse, Helicone, etc.) or native platform logging.

**10. Regular threat modeling with MAESTRO and MITRE ATLAS**
Run a CSA MAESTRO layered analysis at design time. Map attacks to MITRE ATLAS techniques. Re-run threat models when agent capabilities, tools, or integrations change. Purple-team agentic scenarios.

---
