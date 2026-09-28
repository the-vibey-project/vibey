---
id: skill-rag-security-llm08-2025-f3c5605bc9
purpose: rag security llm08 2025
source: src/vibey_tools/skills/plugins/security-principles/skills/ai-security-practices/SKILL.md
requires: ["skill-guardrail-architectures-ddc15ef222"]
links: ["skill-agentic-ai-security-llm06-2025-owasp-asi-top-10-5e21a166f3"]
---

## RAG Security (LLM08:2025)

### Attack Vectors
- **PoisonedRAG** (USENIX Security 2025): 5 malicious documents → 90%+ attack success rate on databases with millions of entries (97% on NQ, 99% on HotpotQA, 91% on MS-MARCO in black-box settings)
- **Embedding-inversion attacks:** recover 50–70% of source text from stolen vectors (ALGEN 2025: ~1,000 samples, transfers across black-box encoders)
- **Cross-tenant leakage** through shared vector stores
- **Hidden-text injection:** white-on-white resume text ingested as legitimate content

### Defense-in-Depth Across Ingest / Retrieve / Generate
**Ingest:**
- Validate and authenticate all document sources
- Strip hidden/zero-width text and ignore formatting on ingestion
- Detect and reject suspicious instruction patterns in documents

**Store:**
- Per-tenant physical isolation or DB-layer namespace filtering (not app-layer)
- Treat the vector DB as a sensitive data store: encrypt, access-control
- Embedding anomaly detection

**Retrieve/Generate:**
- Retrieval rails
- Per OWASP/Snyk LLM Security Verification Standard (Aug 2025): full verification checklist

---
