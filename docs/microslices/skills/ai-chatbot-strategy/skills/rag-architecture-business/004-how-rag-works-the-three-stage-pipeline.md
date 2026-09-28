---
id: skill-how-rag-works-the-three-stage-pipeline-719c804a15
purpose: how rag works the three stage pipeline
source: src/vibey_tools/skills/plugins/ai-chatbot-strategy/skills/rag-architecture-business/SKILL.md
requires: ["skill-the-business-case-hallucination-reduction-49c7479c83"]
links: ["skill-vector-databases-explained-for-business-d108639c4a"]
---

## How RAG Works: The Three-Stage Pipeline

RAG operates through three sequential stages. Every stage matters. Failure at any stage produces a chatbot that fails the user.

### Stage 1: Indexing

Every piece of source material — PDFs, policy documents, support transcripts, product manuals, web pages, FAQs — is processed and loaded into the knowledge base.

The documents are broken into **chunks**: segments of text small enough to retrieve individually but large enough to carry meaningful context. Each chunk is then converted into a **vector** (a mathematical representation of its semantic content) using an embedding model.

The result is a structured, semantically searchable index. When a question arrives, the system navigates this index by *meaning*, not by scanning documents sequentially.

**Chunking decisions made here directly determine retrieval quality.** Cutting too small loses context. Cutting too large reduces precision. There is no post-hoc fix for a poorly structured knowledge base — this is an engineering decision, not a default setting.

### Stage 2: Retrieval

When a user asks a question, that question is also converted into a vector using the same embedding model. The system compares this query vector against the index and returns the document chunks with the highest **semantic similarity** — typically the top 3–5.

This is not keyword search. The query "what are my rights after a delayed flight" will retrieve content about passenger rights, carrier liability, and compensation regulations even if those documents never use the phrase "delayed flight" in those exact words. The system retrieves by meaning, not by string match.

In production systems, retrieved chunks are often **reranked** using a second model to ensure the most relevant content surfaces first — a step that meaningfully improves answer quality in complex document sets.

### Stage 3: Generation

The retrieved chunks are passed to the language model alongside the original question. The model generates a response drawing on both its general language capability and the specific content of the retrieved documents. The response is grounded in your sources — not generated from training memory alone.

Advanced RAG implementations add iterative loops: retrieve, generate a partial answer, identify gaps, retrieve again, and refine before producing a final response.

---
