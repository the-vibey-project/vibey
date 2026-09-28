---
id: skill-evaluation-benchmark-skepticism-4c1574b63b
purpose: evaluation benchmark skepticism
source: src/vibey_tools/skills/plugins/ai-and-data/skills/ai-ml-landscape/SKILL.md
requires: ["skill-llm-inference-optimization-467ffd72e7"]
links: ["skill-rag-fundamentals-quick-reference-e009d8b375"]
---

## Evaluation & Benchmark Skepticism

**The contamination problem is severe.** A single model can swing 17–35 points between SWE-bench Verified and the standardized-scaffold Pro leaderboard — scaffold and harness move scores more than model swaps.

**Key benchmarks:**
- MMLU(-Pro), GPQA Diamond: knowledge/reasoning
- HumanEval/MBPP, SWE-bench Verified/Pro: coding
- GSM8K/MATH: math reasoning
- MMMU: multimodal
- LiveBench/LiveCodeBench: contamination-resistant
- Chatbot Arena Elo: human preference
- RULER/HELMET: long-context
- TruthfulQA/FActScore: factuality
- RAGAS: RAG evaluation

**Decision rule for benchmarks:**
- Never select on a single leaderboard number
- Build a 50–200 case internal eval of your real workflows
- Weight SWE-bench Pro (standardized scaffold) over Verified for coding
- When a benchmark and your production results diverge sharply, trust contamination/scaffold effects over the leaderboard
- LLM-as-judge is widespread but carries position/verbosity/self-preference biases

---
