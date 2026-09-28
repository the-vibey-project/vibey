---
id: skill-part-2-the-four-functional-layers-f8328be3f9
purpose: part 2 the four functional layers
source: src/vibey_tools/skills/plugins/ai-chatbot-strategy/skills/chatbot-build-and-deploy/SKILL.md
requires: ["skill-part-1-before-a-line-of-code-is-written-a4cdeaa038"]
links: ["skill-part-3-data-foundation-and-the-knowledge-base-step-5-4324e589cf"]
---

## Part 2: The Four Functional Layers

A custom chatbot is not one technology. It is a stack of at least five distinct systems—a language model, an embedding model, a vector database, an orchestration framework, and a deployment environment—each of which can fail independently. Most chatbot failures are **integration failures**, not model failures. The language model is rarely the weak link. What breaks is the connection between layers.

### Layer 1: The Language Layer

The language layer handles user input comprehension and response generation. It includes:

- **Large language model (LLM)**: GPT-4/GPT-4o (OpenAI), Mixtral-8x7B (Mistral AI), Gemini 1.5 (Google), or open-weight alternatives like LLaMA. The model choice matters less than the retrieval architecture it operates within.
- **Embedding model**: Converts text into numerical vectors for semantic comparison. Options include OpenAI's text-embedding-ada-002, all-MiniLM-L6-v2, or BERT-based variants. The choice of embedding model determines how accurately the system matches a user's question to source documents.

The LLM and embedding model are often selected together because their dimensional representations must be compatible.

**Input sub-layer responsibilities**: Receiving and parsing user messages, handling multi-turn context, managing session state.

**Understanding sub-layer responsibilities**: Intent detection—is this a complaint, a question, a transaction request, or a request for escalation?

### Layer 2: The Retrieval Layer

The retrieval layer stores the knowledge base and answers: which documents are relevant to this query?

**Vector databases** store document embeddings and execute approximate nearest-neighbor search at query time:
- **Pinecone**: Cloud-native, optimized for high-scale production
- **Weaviate**: Open-source, ML-first with built-in modules
- **Chroma**: Lightweight, suited for prototyping
- **Qdrant / Milvus**: Versatile production deployments
- **FAISS**: Facebook-developed, self-hosted deployments

This layer is most often treated as a commodity and most often responsible for production failures. A language model cannot compensate for a retrieval layer that returns the wrong chunks.

Document ingestion tooling (PyPDF2, Apache Tika, BeautifulSoup for web content) feeds this layer, and its quality is entirely dependent on the cleanliness and structure of source documents.

**Action sub-layer**: Queries the retrieval system, looks up CRM data, books a time, processes a transaction. For RAG-based systems, the action layer embeds the query, retrieves relevant document chunks, and passes them to the generation layer.

### Layer 3: The Orchestration Layer

The orchestration layer connects retrieval to language and manages the complete query cycle: receive input → generate embedding → query vector database → retrieve relevant chunks → construct prompt → call LLM → return response.

**Dominant frameworks**:
- **LangChain** and **Haystack**: Provide modular connectors for most combinations of vector stores and LLMs
- **LlamaIndex**: Strong integration between document ingestion and retrieval pipelines
- **Custom builds** using Hugging Face Transformers and PyTorch: Used in teams requiring fine-grained pipeline control or reduced third-party dependency

Adjacent infrastructure:
- **Task queues**: Celery, Redis (asynchronous jobs)
- **Relational databases**: PostgreSQL (session persistence)

**Response sub-layer**: Generating a reply that is accurate, appropriately toned, and consistent with the brand.

### Layer 4: The Deployment Layer

The deployment layer is where the system runs in production.

**Cloud infrastructure**:
- AWS (SageMaker for model hosting, Bedrock for managed AI)
- Google Cloud (Vertex AI)
- Azure (Azure AI Services)

**Container orchestration**: Docker and Kubernetes handle containerization and horizontal scaling.

**Observability** (not optional for production): Prometheus for metrics, ELK Stack for log aggregation. Observability is the mechanism by which integration failures become detectable rather than invisible.

**Frontend delivery** for public-facing chatbots:
- Web applications: React and Next.js, TypeScript for type safety
- UI: Tailwind CSS, ShadCN or Radix UI component libraries
- Edge deployment: Vercel or Cloudflare Pages
- Backend communication: REST or GraphQL via Fetch or Axios

**Key trade-offs**:

| Decision | Open-Source / Self-Hosted | Proprietary / Cloud |
|---|---|---|
| Data control | Higher; no third-party exposure | Lower; data routes through vendor |
| Deployment speed | Slower; more engineering overhead | Faster; managed infrastructure |
| Long-term cost | Lower for sustained high volume | Higher at scale |
| Compliance fit | Preferred for HIPAA, attorney-client privilege | Requires careful vendor vetting |

---
