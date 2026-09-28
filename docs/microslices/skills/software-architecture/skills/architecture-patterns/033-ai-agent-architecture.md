---
id: skill-ai-agent-architecture-1214916310
purpose: ai agent architecture
source: src/vibey_tools/skills/plugins/software-architecture/skills/architecture-patterns/SKILL.md
requires: ["skill-apim-ai-gateway-front-all-llm-traffic-from-day-one-fef2d50c99"]
links: ["skill-ml-training-inference-d7782b0f95"]
---

## AI Agent Architecture

### Microsoft Agent Framework (Successor to Semantic Kernel + AutoGen)
- **RC 1.0: February 19, 2026; GA targeted end of Q1 2026**
- Both Semantic Kernel and AutoGen are now in maintenance mode
- Unifies AutoGen's multi-agent abstractions with Semantic Kernel's enterprise features (session state, middleware, telemetry)
- Graph-based workflows: sequential, concurrent, handoff, group-chat with checkpointing and human-in-the-loop
- Built on Microsoft.Extensions.AI; supports MCP/A2A/AG-UI; `UseOpenTelemetry()` built in

### Azure AI Foundry Agent Service (GA, May 2025)
- Connected Agents (point-to-point) and multi-agent Workflows
- 1,400+ Logic Apps connectors as tools
- SharePoint/Fabric/Bing knowledge; MCP and A2A tools
- BYO-VNet private networking with no public egress (next-gen GA)

### Agent Memory Patterns
- In-context (history window)
- External vector store (Cosmos DB / Redis / AI Search) for semantic retrieval
- Episodic memory for cross-session state
- **Foundry managed Memory** (preview)

**Host agent loops on ACA or AKS. Durable Functions** can host deterministic, fault-tolerant agent orchestrations that survive restarts and pause for human input at zero compute cost.
