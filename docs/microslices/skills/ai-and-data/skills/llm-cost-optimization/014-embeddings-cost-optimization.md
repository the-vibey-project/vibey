---
id: skill-embeddings-cost-optimization-476dec2c3e
purpose: embeddings cost optimization
source: src/vibey_tools/skills/plugins/ai-and-data/skills/llm-cost-optimization/SKILL.md
requires: ["skill-fine-tuning-for-cost-distillation-pattern-649f1c9380"]
links: ["skill-rate-limiting-429-handling-e5f510eca5"]
---

## Embeddings Cost Optimization

| Model | Dimensions | Price/1M | MTEB | Notes |
|---|---|---|---|---|
| `text-embedding-3-small` | 1,536 | ~$0.02 | 62.3 | OpenAI-ecosystem default; 5× cheaper than ada-002 |
| `text-embedding-3-large` | 3,072 | ~$0.13 | 64.6 | ~2.3 MTEB points better; Matryoshka-truncatable |
| `ada-002` | 1,536 | ~$0.10 | 61.0 | Legacy; replace with 3-small |

**Matryoshka**: store full-dim once; truncate per index (768 dims halves storage). Standard in modern models.

**Cost reduction rules:**
- Cache static-document embeddings by content hash — never re-embed unchanged docs
- Cache common-query embeddings
- Quantize stored vectors (fp32→fp16/int8)
- Batch embedding requests to respect rate limits
- Use ANN over exact search at scale

---
