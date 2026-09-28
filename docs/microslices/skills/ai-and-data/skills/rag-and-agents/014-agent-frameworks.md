---
id: skill-agent-frameworks-c7f465a44d
purpose: agent frameworks
source: src/vibey_tools/skills/plugins/ai-and-data/skills/rag-and-agents/SKILL.md
requires: ["skill-ai-agent-fundamentals-b3879d5844"]
links: ["skill-mcp-model-context-protocol-c7a2214409"]
---

## Agent Frameworks

### LangGraph (Production Default)
- Stateful graph orchestration: nodes/edges/typed state
- Checkpointing: MemorySaver / AsyncPostgresSaver / RedisSaver — **use Postgres/Redis, not SQLite, for distributed**
- `interrupt()` for human-in-the-loop
- Streaming, subgraphs, time-travel debugging
- **Best for**: regulated/auditable, conditional, stateful multi-turn, HITL workflows

### LlamaIndex
- Data-heavy RAG: loaders, node parsers (Simple/Sentence/Markdown/Hierarchical)
- Index types: Vector/Summary/DocumentSummary/KnowledgeGraph/SQL
- RouterQueryEngine, SubQuestionQueryEngine, event-driven Workflows
- `AzureAISearchVectorStore` with hybrid + semantic reranker
- LlamaHub: 100+ integrations

### LangChain
- Large ecosystem; criticized for over-abstraction and version churn
- LCEL composition; 100+ loaders; all major splitters; vector store integrations including `AzureSearch`
- Use for prototyping; prefer LangGraph for production agents

### Other Frameworks
- **CrewAI**: fastest role-based multi-agent prototyping
- **Pydantic AI**: typed, Pythonic, minimal boilerplate, Logfire integration
- **Smolagents** (HuggingFace): minimal CodeAgent (writes/executes Python — **needs sandboxing**)

### Microsoft Agent Framework 1.0 (GA April 3, 2026)
- Open-source successor to Semantic Kernel + AutoGen (both now in maintenance mode)
- Built on Microsoft.Extensions.AI; .NET + Python parity
- Stable 1.0 surface: single-agent abstraction + connectors, middleware, agent memory/context providers, graph-based workflows with checkpointing
- Orchestration patterns: sequential/concurrent/handoff/group-chat/Magentic
- Native MCP + A2A; `UseOpenTelemetry()` built in; YAML declarative agents

### Azure AI Foundry Agent Service (GA March 16, 2026)
- Architecture: Threads (context), Messages (turns), Runs (execution), Run Steps (tool calls/generation)
- Built-in tools: file_search, code_interpreter, azure_ai_search/Foundry IQ, function tools, Logic Apps connectors (1,400+), MCP tools, A2A
- **Connected Agents** = agent-calls-agent; **Foundry Workflows** = visual/YAML multi-agent
- Private networking: no public egress, VNet/subnet injection
- GA REST API: `/openai/v1/`

**Managed (Foundry) vs self-built (LangGraph):**
- Managed: no infra, SOC2, built-in storage/memory, faster to production
- Self-built: full control, portability, custom checkpointing, no lock-in

---
