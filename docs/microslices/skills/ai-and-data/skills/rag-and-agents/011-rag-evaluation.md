---
id: skill-rag-evaluation-489316c9f0
purpose: rag evaluation
source: src/vibey_tools/skills/plugins/ai-and-data/skills/rag-and-agents/SKILL.md
requires: ["skill-advanced-rag-patterns-35d40777d0"]
links: ["skill-azure-ai-search-deep-dive-91a7480313"]
---

## RAG Evaluation

**Build a 50–200 QA golden dataset before launch (human-curated + LLM-synthesized then filtered). Run it on every change.**

### RAGAS Metrics (largely reference-free, LLM-as-judge)
| Metric | Definition |
|---|---|
| **Faithfulness** | Claims in answer supported by context ÷ total claims in answer |
| **Answer Relevancy** | Mean cosine similarity between the question and questions reverse-generated from the answer |
| **Context Precision** | Average precision@k over retrieved chunks (are relevant chunks ranked high?) |
| **Context Recall** | Reference claims supported by retrieved context ÷ total reference claims — **only metric needing ground truth** |

### Retrieval Metrics
- Hit Rate@k, MRR, NDCG, Precision@k

### Azure AI Foundry Evaluators (GA)
Groundedness, Groundedness Pro (Content-Safety-model-based), Relevance, Retrieval, Document Retrieval, Response Completeness, Coherence, Fluency. Continuous evaluation on sampled production traffic surfaced through Azure Monitor.

**Other frameworks**: DeepEval (pytest-style), TruLens (RAG triad: groundedness/answer-relevance/context-relevance), Arize Phoenix.

---
