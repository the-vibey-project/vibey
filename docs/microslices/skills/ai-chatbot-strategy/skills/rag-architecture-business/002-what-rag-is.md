---
id: skill-what-rag-is-d7d256ff04
purpose: what rag is
source: src/vibey_tools/skills/plugins/ai-chatbot-strategy/skills/rag-architecture-business/SKILL.md
requires: ["skill-the-core-problem-rag-solves-fc47fee80d"]
links: ["skill-the-business-case-hallucination-reduction-49c7479c83"]
---

## What RAG Is

**Retrieval-Augmented Generation (RAG)** is an architectural technique introduced in a 2020 paper by Patrick Lewis and colleagues at Facebook AI Research. It combines two separate functions:

1. **Retrieval** — finding relevant information from an external, updatable knowledge base at the moment a question is asked
2. **Generation** — producing a coherent response using both the model's language capability and the specific content retrieved

The core insight: a language model does not need to have all knowledge encoded in its training weights. It only needs to be able to *use* knowledge retrieved on demand.

**The open-book exam analogy.** A standard LLM is a closed-book exam — the student answers from memory alone. RAG makes it open-book — the student can consult current, authoritative sources before answering. The open-book student is more reliable, not because they are smarter, but because they are answering from evidence rather than from recall.

**What changes with RAG:**
- The model still provides language and reasoning capability
- A separate, independently-updatable knowledge base provides current, accurate, domain-specific content
- At query time, the system retrieves from your knowledge base before generating any response

---
