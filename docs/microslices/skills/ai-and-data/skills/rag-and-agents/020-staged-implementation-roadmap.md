---
id: skill-staged-implementation-roadmap-5678f10d22
purpose: staged implementation roadmap
source: src/vibey_tools/skills/plugins/ai-and-data/skills/rag-and-agents/SKILL.md
requires: ["skill-anti-patterns-to-avoid-c3f0a25a8b"]
links: []
---

## Staged Implementation Roadmap

**Stage 1 — Baseline (weeks 1–2):** Stand up hybrid search + semantic reranking. Azure: AI Search Standard + integrated vectorization with text-embedding-3-large + `queryType: semantic`. Custom: Qdrant or pgvector (<10M vectors) + Cohere Rerank 3.5 or BGE-reranker. Build the 50–200 QA golden set now.

**Stage 2 — Chunking & context (weeks 3–4):** Add parent-child chunking (child 100–256 tokens, parent 512–2,048). Switch parsers to LlamaParse/Docling/Azure Document Intelligence Layout (Markdown output) if table/layout fidelity is failing. Add Contextual Retrieval if retrieval misses persist.

**Stage 3 — Advanced retrieval (month 2):** Add query decomposition/multi-query, or adopt Azure AI Search agentic retrieval / Foundry IQ for multi-intent queries. GraphRAG only if queries are genuinely multi-hop/thematic on large static corpus — start with LazyGraphRAG.

**Stage 4 — Agents (months 2–3):** If dynamic tool use/planning is needed: Foundry Agent Service + Foundry IQ for fastest enterprise time-to-production; LangGraph for full control; Microsoft Agent Framework 1.0 for open-source Azure-aligned path. Enforce termination contracts, sandbox code execution, trace everything.

**Migration deadlines:** Migrate "On Your Data" workloads to Foundry IQ before GPT-4o 2024-11-20 retires (2026-10-01). Migrate AzureML SDK v1 before June 30, 2026 end-of-support.
