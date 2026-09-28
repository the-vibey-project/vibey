---
id: skill-agent-stack-mcp-ed82f9638f
purpose: agent stack mcp
source: src/vibey_tools/skills/plugins/ai-and-data/skills/ai-ml-landscape/SKILL.md
requires: ["skill-rag-fundamentals-quick-reference-e009d8b375"]
links: ["skill-generative-ai-across-modalities-0275672725"]
---

## Agent Stack & MCP

**Model Context Protocol (MCP)**: Anthropic, Nov 2024; donated to Linux Foundation Dec 2025; adopted by OpenAI, Google, Microsoft, Amazon. "USB-C for AI tools." Over 97M monthly SDK downloads and 10,000 active servers at donation time.

**Production failure modes**: runaway loops, unbounded retries, silent context truncation. Iteration limits, cost ceilings, and termination conditions are mandatory, not polish.

**Single-agent suffices for ~80% of cases.** Multi-agent adds cost and non-determinism.

**Framework selection:**
- **LangGraph**: production default for regulated/auditable workflows; graph state machines with checkpointing
- **CrewAI**: fastest role-based multi-agent prototyping
- **Pydantic AI**: typed, minimal boilerplate

---
