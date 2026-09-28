---
id: skill-embedding-models-2026-fe4d373f9b
purpose: embedding models 2026
source: src/vibey_tools/skills/plugins/ai-and-data/skills/rag-and-agents/SKILL.md
requires: ["skill-chunking-the-highest-roi-lever-ce059dcf62"]
links: ["skill-vector-databases-honest-selection-guide-c0719ac20d"]
---

## Embedding Models (2026)

**MTEB leaderboard is directional only — always test on your own data.**

| Model | Dimensions | Price/1M tokens | Notes |
|---|---|---|---|
| **text-embedding-3-large** | 3,072 (Matryoshka) | ~$0.13 | Safe OpenAI default; truncatable to 256/512/1024 |
| **text-embedding-3-small** | 1,536 (Matryoshka) | ~$0.02 | 5× cheaper; adequate for most workloads |
| **Cohere embed-v4** | 1,024 | ~$0.01 | Multilingual 100+ languages |
| **Voyage voyage-3-large / voyage-4** | — | — | Domain leader for code/legal/medical; +4–6 MTEB points on domain retrieval |
| **BGE-M3** | — | Self-hosted | Open; self-hostable |

**Matryoshka Representation Learning**: truncate dimensions (3,072→256/512/1,024) without retraining for graceful quality/storage trade-offs. Now standard.

**Asymmetric search**: E5-instruct task prefixes align query vs document intent — important for asymmetric query/passage retrieval.

---
