---
id: skill-prompt-injection-llm01-2025-the-unfixable-risk-0bac2abfd2
purpose: prompt injection llm01 2025 the unfixable risk
source: src/vibey_tools/skills/plugins/security-principles/skills/ai-security-practices/SKILL.md
requires: ["skill-owasp-llm-top-10-2025-edition-6ec23902cb"]
links: ["skill-output-sanitization-llm05-2025-improper-output-handling-dbb59d9f40"]
---

## Prompt Injection (LLM01:2025) — The Unfixable Risk

### Why It Cannot Be Patched Away
LLMs process instructions and data in the same channel without clear separation. No input filter is fully reliable — adaptive attacks evade classifiers.

### Direct vs Indirect Injection
- **Direct:** "ignore previous instructions"
- **Indirect (harder):** malicious instructions embedded in a webpage, RAG document, email, or tool result the model later reads — NOT caught by input-only classifiers
- **Multimodal:** instructions hidden in images

### Defensible Architectural Patterns (More Robust Than Detection)
1. **Action-selector:** constrain the set of actions an LLM can take
2. **Plan-then-execute:** LLM produces a plan; deterministic code validates and executes it
3. **Dual-LLM** (Simon Willison): one privileged LLM for user instructions, one quarantined for external content
4. **CaMeL** (Google DeepMind, March 2025): privileged planner + quarantined LLM executor with enforced information-flow controls
5. **IsolateGPT** (NDSS 2025): sandboxed execution of external content

### Detection Tooling (Treat as One Layer, Not the Solution)
- **Meta Prompt-Guard / Llama Guard 3** (open-weight, 8B): outperforms GPT-4 on injection detection with ~1/3 the false-positive rate
- **NVIDIA NeMo** jailbreak heuristics
- **LLM Guard** (Protect AI): input scanners
- **DataSentinel**, **PIShield**

### Implementation
- **Python:** run Llama Guard via vLLM or LLM Guard input scanners before the model call; enforce a Pydantic output schema after
- **TypeScript:** validate model output with **Zod** before it touches SQL/HTML/shell; never pass raw LLM text to `dangerouslySetInnerHTML`

---
