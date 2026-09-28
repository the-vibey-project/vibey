---
id: skill-llm-training-post-training-9c06115b4d
purpose: llm training post training
source: src/vibey_tools/skills/plugins/ai-and-data/skills/ai-ml-landscape/SKILL.md
requires: ["skill-the-transformer-attention-395a2de8eb"]
links: ["skill-llm-inference-optimization-467ffd72e7"]
---

## LLM Training & Post-Training

### Tokenization
- BPE/WordPiece/SentencePiece/tiktoken; larger vocabulary = shorter sequences but larger embedding tables
- **Chinchilla scaling** (~20:1 tokens:params) guided compute-optimal training; inference-cost economics now push toward "overtrain a smaller model"

### Pre-training Infrastructure
- Curated/deduplicated/quality-filtered corpora + heavy synthetic data (Phi "textbooks" thesis)
- Tensor/pipeline/data parallelism; ZeRO/DeepSpeed; FSDP; Megatron-LM

### Alignment Pipeline
1. **SFT** (Supervised Fine-Tuning): high-quality instruction examples; "LIMA / Less is More" — a few thousand high-quality examples often beat massive noisy sets
2. **DPO** (Direct Preference Optimization): reference-model based, no explicit reward model; simple default
3. **GRPO**: critic-free, group-relative, RLVR; dominates reasoning post-training

### PEFT (Parameter-Efficient Fine-Tuning)
- **LoRA**: low-rank adapters; workhorses of production fine-tuning
- **QLoRA**: 4-bit NF4 base + LoRA; enables fine-tuning large models on consumer hardware
- DoRA/VeRA: refinements of LoRA

---
