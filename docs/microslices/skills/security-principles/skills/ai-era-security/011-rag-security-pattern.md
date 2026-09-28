---
id: skill-rag-security-pattern-d327e92958
purpose: rag security pattern
source: src/vibey_tools/skills/plugins/security-principles/skills/ai-era-security/SKILL.md
requires: ["skill-threat-modeling-reference-stride-applied-to-ai-agents-6b9d6c6fee"]
links: ["skill-eu-ai-act-compliance-checklist-cdc9bcd4c9"]
---

## RAG Security Pattern

1. Validate and provenance-tag all ingested content before indexing
2. Isolate untrusted external content from system instructions
3. Access-control the vector store per tenant — multi-tenant RAG is a common data leakage path
4. Check output groundedness — detect when the model departs from retrieved context
5. Treat all retrieved content as untrusted data, not trusted instructions
6. Monitor for false RAG entry injection (MITRE ATLAS Spring 2025)

---
