---
id: skill-evaluation-framework-for-rag-quality-b0f323c244
purpose: evaluation framework for rag quality
source: src/vibey_tools/skills/plugins/ai-chatbot-strategy/skills/rag-architecture-business/SKILL.md
requires: ["skill-the-technology-stack-in-summary-b072f57b98"]
links: ["skill-what-cannot-be-solved-by-model-upgrades-2e63a7440b"]
---

## Evaluation Framework for RAG Quality

**RAGAS** (Retrieval-Augmented Generation Assessment) provides structured metrics for evaluating RAG pipeline performance:

- **Context Relevance** — did the system retrieve the right content for the query?
- **Faithfulness** — does the generated response accurately reflect the retrieved content without adding invented information?
- **Answer Relevance** — does the response address what the user actually asked?

Key metrics for production monitoring:
- Intent recognition accuracy
- Retrieval precision (are the right chunks being surfaced?)
- Response accuracy against ground-truth answers
- Latency under load (target below 200ms for well-structured modular deployments)
- Resolution rate (did the user get a satisfactory answer without escalation?)
- Escalation rate (what percentage of queries exceed the chatbot's capability?)

---
