---
id: skill-the-technology-stack-in-summary-b072f57b98
purpose: the technology stack in summary
source: src/vibey_tools/skills/plugins/ai-chatbot-strategy/skills/rag-architecture-business/SKILL.md
requires: ["skill-the-cost-spectrum-b4e6a208ff"]
links: ["skill-evaluation-framework-for-rag-quality-b0f323c244"]
---

## The Technology Stack in Summary

For technical evaluators, the production RAG stack:

| Layer | Components |
|---|---|
| **Language / NLU** | Pretrained transformer models (GPT-4, Claude, Gemini, LLaMA) for intent detection and generation |
| **Embedding** | OpenAI text-embedding-ada-002, all-MiniLM-L6-v2, Sentence-BERT, or BERT-based variants |
| **Retrieval / Vector DB** | Pinecone, Weaviate, Chroma, Milvus, Qdrant, or FAISS (self-hosted) |
| **Orchestration** | LangChain or LlamaIndex for retrieval-to-generation pipeline; Haystack as alternative |
| **Dialogue Management** | Session state management, conversation flow control |
| **Deployment** | Docker + Kubernetes on AWS / Google Cloud / Azure; SageMaker, Vertex AI, or Bedrock for managed model hosting |
| **Frontend** | React + Next.js + TypeScript; Tailwind CSS + ShadCN/Radix UI components; Vercel or Cloudflare Pages |
| **Observability** | Prometheus for metrics, ELK Stack for log aggregation — not optional for production |
| **Document Ingestion** | PyPDF2, Apache Tika, BeautifulSoup for web content |

### Key Trade-Offs

| Decision | Options | Trade-Off |
|---|---|---|
| Open-source vs. proprietary | Llama / Weaviate / Chroma vs. GPT-4o / Pinecone | Open-source: control and privacy. Proprietary: faster integration, higher cost, potential security concerns |
| Self-hosted vs. cloud | On-premises infrastructure vs. AWS/GCP/Azure | Self-hosted: lower long-term cost, better privacy. Cloud: faster to deploy, more scalable |
| Speed vs. accuracy | Smaller/cheaper models vs. frontier models | High-accuracy LLMs are expensive and compute-heavy; smaller models miss nuance |
| Real-time vs. batch processing | Synchronous RAG vs. pre-computed results | Real-time feels immediate; may require throttling or rate limits at scale |

---
