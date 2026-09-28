---
id: skill-prompt-context-compression-provider-agnostic-608d6a96ce
purpose: prompt context compression provider agnostic
source: src/vibey_tools/skills/plugins/ai-and-data/skills/llm-cost-optimization/SKILL.md
requires: ["skill-context-window-engineering-d9607b02e3"]
links: ["skill-model-routing-cascades-d39b8daf17"]
---

## Prompt & Context Compression (Provider-Agnostic)

Caching and routing beat any prompt-rewriting trick — apply this section only after the structural levers above. Measure **tokens-per-completed-task**: over-compression triggers retries and clarifications that cost more than they save.

### The Counterintuitive Research Consensus
**Extractive compression — selecting whole sentences — often outperforms fancier token-pruning and enables up to ~10× compression with minimal accuracy loss** (UC Berkeley, "Characterizing Prompt Compression Methods for Long Context Inference," arXiv 2407.08892, ICML 2024 Es-FoMo). Reach for perplexity-based pruning (LLMLingua) only when query-aware long-context demands it.

### Compression Libraries
- **LLMLingua / LongLLMLingua / LLMLingua-2** — see the LLMLingua subsection above. `pip install llmlingua`; stacks with caching (cache the compressed prompt).
- **RECOMP** (arXiv 2310.04408): "Retrieve, Compress, Prepend" for RAG. Extractive + abstractive compressors to **~6%** of original; emits an empty summary on irrelevant docs (selective augmentation). Can over-compress on multi-hop queries.
- **Selective Context** (EMNLP 2023): self-information pruning via a base LM; process 2× more content, save 40% memory/GPU. `pip install selective-context`.
- **Soft-prompt / learned** (need fine-tuning + weight access): Gist tokens (up to 26×, NeurIPS 2023), AutoCompressor (~30:1), ICAE (512→32/64/128 memory tokens).
- **PCToolkit** bundles Selective Context, LLMLingua, LongLLMLingua, SCRL, KiS as plug-and-play.

### Caveman / Telegraphic Prompting — Oversold
Stripping articles, prepositions, pleasantries, and filler claims up to 75% savings; independent benchmarks land at **14–21%** on real coding tasks (Guzik: Sonnet 14%, Opus 21%; ncvgl SWE-bench Pro ~14%) because input/context dominates the bill there, with quality staying 100%. Best for output-heavy interactive sessions. The middle ground — "Be concise, no filler, skip pleasantries" — captures most savings without unreadable telegraph. Politeness tokens are pure cost.

### Serialization Format Choice (20–80% Token Swing)
Roughly **TOON < Markdown < YAML < compact JSON < pretty JSON < XML**. XML needs ~80% more tokens than Markdown for the same nested data; YAML ~36% cheaper than JSON per record; TOON ~30–50% savings on uniform tabular arrays (weak on nested/irregular data). **But** use XML *tags* for prompt structure (semantic clarity, per Anthropic) and avoid forcing JSON output on reasoning — it can degrade quality 10–15%.

### Output Verbosity Control
- **Concise CoT** (arXiv 2401.05618): −48.70% response length, −22.67% per-token cost; watch a −27.69% accuracy hit on GPT-3.5 math.
- **Chain-of-Draft** (~5 words/step, arXiv 2502.18600): as little as **7.6% of CoT tokens** while matching/beating accuracy; on Claude 3.5 Sonnet's sports task, 189.4→14.3 output tokens (−92.4%) with accuracy rising 93.2%→97.3%.
- **Structured output does NOT save tokens** — JSON adds ~40% over free text; constrained decoding adds schema tokens + 10–30% latency. It guards weak models (Qwen2.5-Coder-7B 0%→75%) but degrades strong ones (GPT-5 extraction 86.9%→70% on complex schemas). For reasoning: two-step (free-form think → constrained format). See Structured Outputs below for the Azure API specifics.

---
