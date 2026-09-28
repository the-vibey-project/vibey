---
id: skill-8-fine-tuning-and-adaptation-fc6de13deb
purpose: 8 fine tuning and adaptation
source: src/vibey_tools/skills/plugins/machine-learning/skills/ml-deep-learning-and-training/SKILL.md
requires: ["skill-7-training-at-scale-9b995b1d59"]
links: []
---

## §8. Fine-Tuning and Adaptation

**[DURABLE] The order to try things, cheapest first:**
```
1. Prompting / few-shot                  ← no training. Try this first, seriously
2. Retrieval (RAG)                       ← when the problem is missing knowledge
3. PEFT / LoRA                           ← when the problem is behaviour or format
4. Full fine-tuning                      ← when you have real data and real budget
5. Continued pretraining                 ← new domain, large corpus
6. Training from scratch                 ← almost never the right answer
```
**⚠️ The most common expensive mistake is fine-tuning to fix a knowledge problem.**
Fine-tuning teaches *behaviour, style, and format* reliably; it teaches *facts* poorly and
expensively. **If the model doesn't know something, retrieve it.**

**LoRA** — freeze the base, train low-rank adapters (`W + BA`). Tiny memory footprint,
swappable adapters, near-full-fine-tuning quality on most tasks. **QLoRA** adds 4-bit
quantization of the frozen base, putting single-GPU fine-tuning of large models within
reach. Other PEFT: prefix tuning, prompt tuning, IA³, DoRA.

**Post-training / alignment**: **SFT** (supervised fine-tuning on demonstrations), then
preference optimization — **RLHF/PPO** (powerful, complex, unstable), **DPO** (much
simpler, no reward model, now the common default), and GRPO and relatives for reasoning
work. **[DURABLE] Data quality dominates method choice here** — a small, carefully curated
SFT set routinely beats a large noisy one.

**⚠️ Catastrophic forgetting is real.** Fine-tuning on a narrow task degrades general
capability. Mix in general data, use lower learning rates, prefer PEFT, and **evaluate on
capabilities you didn't train on** — not just the target task.
