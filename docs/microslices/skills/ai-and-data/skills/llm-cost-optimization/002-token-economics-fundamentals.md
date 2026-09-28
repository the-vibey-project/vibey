---
id: skill-token-economics-fundamentals-84afd10b30
purpose: token economics fundamentals
source: src/vibey_tools/skills/plugins/ai-and-data/skills/llm-cost-optimization/SKILL.md
requires: ["skill-the-three-core-levers-in-roi-order-1637123157"]
links: ["skill-azure-pricing-models-ecbfa2d9cf"]
---

## Token Economics Fundamentals

### Tokenization
- **`o200k_base`** (GPT-4o, o-series, GPT-4.1+): 200K-token vocabulary; ~10% fewer tokens for English than `cl100k_base`; 20–40% fewer tokens for non-Latin scripts (Chinese, Japanese, Arabic)
- **`cl100k_base`** (GPT-4/3.5/ada-002): 100K-token vocabulary
- Always resolve encodings with `tiktoken.encoding_for_model()` — never hardcode. Tokenizer drift across model generations can silently inflate per-request cost by up to ~35% at unchanged per-token prices.
- The only ground truth for billing is the API's `usage` object (includes `cached_tokens` and `reasoning_tokens` breakdowns)

### Input/Output Pricing Asymmetry — **Architectural Implication**
- Input (prefill): one parallel forward pass over all tokens
- Output (decode): one sequential forward pass **per token** → output costs 3–8× input
- Azure GPT-4o example: input $2.50/1M vs output $10/1M (4×)
- **Design implication**: minimize output length for cost-sensitive paths; be explicit about output length in the prompt

### Reasoning Tokens
- Billed at **output rates** (expensive)
- Invisible in the response body; surfaced in `output_tokens_details.reasoning_tokens`
- Do NOT persist across turns
- Consume the `max_tokens` budget — a complex task can burn 8,000+ reasoning tokens before a 300-token answer
- **Anti-pattern trap**: setting `max_tokens` too low yields `finish_reason: "length"` with empty content because reasoning consumed the entire budget
- **Rule**: set `max_tokens` to ≥4× expected visible output for reasoning models
- Track reasoning tokens as a first-class metric
- Worth it for genuine multi-step reasoning (math, code, legal analysis); wasteful on pipelines expecting short outputs

---
