---
id: skill-retrieval-strategies-21e8cb5c41
purpose: retrieval strategies
source: src/vibey_tools/skills/plugins/ai-and-data/skills/rag-and-agents/SKILL.md
requires: ["skill-vector-databases-honest-selection-guide-c0719ac20d"]
links: ["skill-reranking-e2ac188267"]
---

## Retrieval Strategies

### Sparse vs Dense vs Hybrid
- **Sparse (BM25/TF-IDF/SPLADE)**: wins for exact keywords, product codes, acronyms, statute numbers
- **Dense bi-encoder**: handles semantics, synonyms, paraphrase
- **Hybrid almost always beats either alone**: fuse with Reciprocal Rank Fusion (RRF) — Azure AI Search's default

### Query Processing Techniques
| Technique | What it does |
|---|---|
| **HyDE** | Generate a hypothetical answer, embed it as the query |
| **Step-back prompting** | Rephrase to a more general question |
| **Multi-query** | Generate multiple phrasings; union results |
| **Decomposition** | Break complex question into sub-questions; synthesize |
| **Routing** | Classify query type → pick retrieval strategy |

---
