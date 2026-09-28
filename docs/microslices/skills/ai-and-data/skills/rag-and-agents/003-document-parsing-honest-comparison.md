---
id: skill-document-parsing-honest-comparison-b0d0c2ee35
purpose: document parsing honest comparison
source: src/vibey_tools/skills/plugins/ai-and-data/skills/rag-and-agents/SKILL.md
requires: ["skill-rag-fundamentals-6f3492eac5"]
links: ["skill-chunking-the-highest-roi-lever-ce059dcf62"]
---

## Document Parsing — Honest Comparison

| Parser | F1 (benchmark) | Best for | Cost | Notes |
|---|---|---|---|---|
| **LlamaParse** | ~92% | Complex layouts | ~$0.10/page (top tier), API-only | Multimodal LLM-based; highest accuracy |
| **Azure Document Intelligence** | ~90% structured, ~75% free-form | Azure workloads; standardized forms | ~$1.50/1K pages (prebuilt) | Layout model outputs Markdown; natively callable as AI Search skill |
| **Docling** (IBM, MIT) | ~88%, ~45 pages/sec GPU | Self-hosted; MCP server available | Free | Best open-source; fully local for sensitive data |
| **PyMuPDF4LLM** | — | Digital text; speed/lightness | Free | Fully local |
| **Unstructured** | — | 30+ formats with built-in chunking | Free/paid | Broad format support |

**For RAG**: Markdown output beats JSON — chunks cleanly while preserving hierarchy.

**Azure Document Intelligence Layout model**: produces Markdown (`MarkdownOutputFormat`), extracts tables/selection-marks, cross-page tables (since Ignite 2025); the cheaper `Read` model handles OCR/handwriting only.

**Pre-processing checklist:** Unicode normalization, header/footer/boilerplate removal, language detection, PII scrubbing (Azure AI Language / Presidio / Content Safety), quality filtering, dedup (exact + near-duplicate via MinHash/SimHash).

---
