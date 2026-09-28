---
id: skill-multi-agent-systems-b0ac2ceacf
purpose: multi agent systems
source: src/vibey_tools/skills/plugins/ai-and-data/skills/rag-and-agents/SKILL.md
requires: ["skill-mcp-model-context-protocol-c7a2214409"]
links: ["skill-agentic-system-design-security-a3eeb4b322"]
---

## Multi-Agent Systems

**Justified by**: specialization, parallelism, redundancy, context-window scale.
**Costs**: coordination overhead, non-determinism, debugging difficulty, cost multiplication.

### Patterns
- Orchestrator-worker, supervisor (LangGraph), hierarchical
- Group-chat/round-table (AutoGen→MAF)
- Sequential chaining, parallel fan-out, debate, handoff, swarm

### Production Requirements
- Shared state vs message passing; checkpoint and ensure idempotency for retries
- Trust boundaries between agents; per-agent budget caps
- Validate inter-agent output before acting on it

---
