---
id: skill-agentic-system-design-security-a3eeb4b322
purpose: agentic system design security
source: src/vibey_tools/skills/plugins/ai-and-data/skills/rag-and-agents/SKILL.md
requires: ["skill-multi-agent-systems-b0ac2ceacf"]
links: ["skill-emerging-patterns-893d12ab17"]
---

## Agentic System Design & Security

### Mandatory Production Controls
- Hard `max_iterations` limit
- Token and time budgets per run
- Explicit completion criteria
- Retry limits per tool
- Fallback/graceful degradation
- Human-in-the-loop via `interrupt()` / Foundry approvals

**The "AI cost snowball"** — runaway agents without limits is a documented incident class; hard limits are mandatory, not polish.

### Sandboxed Code Execution
**Azure Container Apps Dynamic Sessions** (GA): Hyper-V-isolated, per-session, millisecond startup. Python/Node/shell + custom container. Never run LLM-generated code in-process.

### Observability
- Trace every tool call, LLM call, decision, latency, and cost via OpenTelemetry
- Tools: LangSmith, Langfuse (open-source, Azure-deployable), Arize Phoenix, W&B Weave, Foundry Traces
- The APIM AI gateway pattern fronts agents with semantic caching, rate limiting, monitoring, and MCP tool governance

### Security Architecture
- Managed identity everywhere, private endpoints, CMK, VNet, regional data residency
- PII scrubbing before indexing
- Document-level ACL trimming
- Diagnostic/audit logging to Log Analytics
- Foundry XPIA/cross-prompt injection filters for indirect injection from retrieved content
- Defend against direct injection (user input) and indirect injection (poisoned retrieved docs)

---
