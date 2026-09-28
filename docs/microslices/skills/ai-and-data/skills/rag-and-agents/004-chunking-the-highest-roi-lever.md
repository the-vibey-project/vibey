---
id: skill-chunking-the-highest-roi-lever-ce059dcf62
purpose: chunking the highest roi lever
source: src/vibey_tools/skills/plugins/ai-and-data/skills/rag-and-agents/SKILL.md
requires: ["skill-document-parsing-honest-comparison-b0d0c2ee35"]
links: ["skill-embedding-models-2026-fe4d373f9b"]
---

## Chunking — The Highest-ROI Lever

### Standard Strategies
| Strategy | How | When to use |
|---|---|---|
| **Recursive character splitting** | Split by newlines, spaces, chars | Standard baseline; default in LangChain |
| **Markdown/HTML header splitters** | Split at header boundaries | When document structure matters |
| **Semantic chunking** | Embedding-similarity breakpoints | When topics vary within a document |

### Parent-Child (Hierarchical) — **Single Highest-ROI Production Pattern**
- Embed small child chunks (100–500 tokens, often 100–200) for retrieval precision
- Return larger parent (500–2,000 tokens) to the LLM for generation context
- Children are "searchable atoms"; parents are "answer-ready context"

### Advanced Chunking
| Method | Description | Best for |
|---|---|---|
| **Sentence-window** | Retrieve a sentence, expand ±k neighbors | Conversational/factoid |
| **Late chunking** (Jina, 2024) | Embed full doc first, pool per-chunk so chunk embeddings retain document context | Any domain with long documents |
| **Contextual Retrieval** (Anthropic, Sept 2024) | Prepend LLM-generated chunk-specific context summary before embedding/indexing | General — see numbers below |

**Contextual Retrieval verified numbers (Anthropic, Sept 2024):**
- Contextual Embeddings alone: 35% failure reduction (5.7% → 3.7%)
- + Contextual BM25: 49% failure reduction (→ 2.9%)
- + Reranking: 67% failure reduction (→ 1.9%)
- One-time cost: ~$1.02 per million document tokens using prompt caching
- Caveat: gains vary by domain — large on fiction, near-zero on arXiv papers at top-20

**Size guidance by use case:**
- FAQ: ~512 tokens
- Technical docs: ~1,024 tokens
- Legal/contracts: ~2,048 tokens
- Code: at function/class boundaries (AST-aware)

---
