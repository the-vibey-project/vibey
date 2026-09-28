---
id: skill-mcp-model-context-protocol-c7a2214409
purpose: mcp model context protocol
source: src/vibey_tools/skills/plugins/ai-and-data/skills/rag-and-agents/SKILL.md
requires: ["skill-agent-frameworks-c7f465a44d"]
links: ["skill-multi-agent-systems-b0ac2ceacf"]
---

## MCP (Model Context Protocol)

**Standardizes LLM↔tool/data connections.** Anthropic Nov 2024; donated to Linux Foundation (Agentic AI Foundation) Dec 9, 2025; adopted by OpenAI, Google, Microsoft, Amazon. Over 97M monthly SDK downloads, 10,000 active servers at donation.

**Architecture**: Host/client/server roles. Transports: stdio (local), HTTP+SSE/streamable HTTP (remote), WebSocket.

**Primitives**: Resources (readable data), Tools (callable functions), Prompts (templates), Sampling (server requests completion). OAuth 2.0 for remote servers.

**Build with**: FastMCP (Python decorators) or official SDKs.

**Azure MCP servers**: Azure DevOps, ARM, Bing, Azure SQL, Blob, Monitor. Deploy custom servers on Azure Container Apps or Azure Functions (`/runtime/webhooks/mcp`).

**A2A** (Google, 2025): complementary agent-to-agent protocol.

**Security risks**: prompt injection via malicious servers, confused-deputy attacks. Restrict capabilities, sandbox, validate.

---
