---
id: skill-context-assembly-generation-21b8339a4d
purpose: context assembly generation
source: src/vibey_tools/skills/plugins/ai-and-data/skills/rag-and-agents/SKILL.md
requires: ["skill-reranking-e2ac188267"]
links: ["skill-advanced-rag-patterns-35d40777d0"]
---

## Context Assembly & Generation

**Fight "lost in the middle"**: place best material at the beginning or end of the context window.

**System prompt structure for RAG:**
```
[role/instruction]
[document format description]
[citation rules]
[anti-hallucination instruction: "Answer only from the provided context; if the answer is not in the documents, say you don't know."]
```

- Deduplicate and stitch adjacent chunks before passing to LLM
- Handle no-answer cases explicitly with a fallback instruction
- Stream responses for UX; prompt for clarifying questions when context is insufficient

---
