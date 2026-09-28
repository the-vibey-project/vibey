---
id: skill-the-four-ai-memory-types-dd049fa661
purpose: the four ai memory types
source: src/vibey_tools/skills/plugins/ai-chatbot-strategy/skills/rag-architecture-business/SKILL.md
requires: ["skill-embeddings-explained-for-business-7822da01d8"]
links: ["skill-three-generations-of-rag-architecture-3e1541e503"]
---

## The Four AI Memory Types

Understanding RAG requires understanding how AI systems store and access knowledge:

| Memory Type | What It Is | RAG Relevance |
|---|---|---|
| **Parametric memory** | Knowledge baked into model weights during training | What standard LLMs use exclusively; fixed at training cutoff |
| **Non-parametric memory** | External knowledge bases retrieved at query time | What RAG adds; updatable without model retraining |
| **In-context memory** | Information provided in the prompt window | Conversation history, session state; limited by context window size |
| **Episodic memory** | Logs of prior interactions | Used for personalization and continuous improvement |

RAG's structural advantage is the combination: **parametric memory** (language capability and general reasoning from training) plus **non-parametric memory** (your current, proprietary, domain-specific knowledge). Neither alone is sufficient for high-stakes business deployments.

---
