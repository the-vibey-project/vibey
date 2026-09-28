---
id: skill-advanced-prompt-engineering-b07ad86f03
purpose: advanced prompt engineering
source: src/vibey_tools/skills/plugins/ai-and-data/skills/llm-cost-optimization/SKILL.md
requires: ["skill-semantic-caching-16745e0396"]
links: ["skill-tool-calling-cost-optimization-ac01b79fcd"]
---

## Advanced Prompt Engineering

### System Prompt Structure
```
[Role and objective]
[Constraints and rules — positive instructions ("always do X") outperform negative]
[Output format specification]
[Examples if needed]
```

### Reasoning Techniques (with cost trade-offs)
| Technique | Cost | When to use |
|---|---|---|
| Zero-shot CoT ("think step by step") | Moderate (adds output tokens) | Multi-step tasks on non-reasoning models |
| Few-shot CoT (3–8 exemplars) | Higher (adds input tokens) | Complex tasks needing demonstrated format |
| Self-consistency (sample N, vote) | N× cost | High-stakes decisions |
| Tree of Thoughts (branching) | Expensive | Deep search/planning problems |
| Dedicated reasoning model (o-series) | High but predictable | Genuine multi-step reasoning |

**Rule**: use dedicated reasoning models for genuine multi-step problems; use CoT-prompted standard models when you need to see/control the reasoning and cost matters.

### Structured Outputs
**Prefer Structured Outputs (JSON Schema, `strict: true`)** over legacy JSON mode — guarantees schema adherence, not just valid JSON.

Azure constraints:
- All fields must be `required` (emulate optional via `["type","null"]`)
- `additionalProperties: false`
- ≤100 properties, ≤5 nesting levels
- Not compatible with `parallel_tool_calls` (set to false) or On Your Data/Assistants
- Supported on: gpt-4o (2024-08-06+), gpt-4.1 family, o1/o3/o3-mini/o4-mini

### Sampling Parameters
- Temperature 0 + `seed` for deterministic/factual outputs
- Higher temperature/top-p for creative generation
- Always set `max_tokens` — no cap means unbounded cost exposure

### Dynamic Few-Shot
Retrieve similar examples via embedding search rather than hardcoding — enables more relevant examples without growing the static system prompt.

### Prompt-as-Code
- Git-version prompts
- Test against golden eval sets before deploying
- Store prompts in Azure App Configuration for runtime updates without redeploy
- A/B test prompt changes with proper statistical significance

---
