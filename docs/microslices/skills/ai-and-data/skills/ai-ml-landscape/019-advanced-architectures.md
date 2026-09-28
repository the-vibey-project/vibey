---
id: skill-advanced-architectures-9d808ee3d6
purpose: advanced architectures
source: src/vibey_tools/skills/plugins/ai-and-data/skills/ai-ml-landscape/SKILL.md
requires: ["skill-mlops-infrastructure-65bf7541d8"]
links: ["skill-safety-alignment-governance-f1d8565664"]
---

## Advanced Architectures

### State-Space Models (SSMs)
- **Mamba** (selective state spaces, Mamba-2): linear complexity, ~5× throughput
- **Critical weakness**: pure SSMs fail at retrieval/in-context copying — removing attention layers drops retrieval accuracy to near-zero
- **Hybrids win in production**: Jamba (AI21), Zamba2, NVIDIA Nemotron-H, IBM Granite 4.0 — small fraction of attention layers interleaved with Mamba blocks

### Long Context
- 1M+ token windows are table stakes across flagships
- "Lost in the middle" and needle-in-haystack failures persist
- RAG vs long-context is a cost/freshness/auditability decision, not a pure capability one

### Reasoning Research
- Test-time compute scaling via PRMs
- MCTS for reasoning
- Self-consistency voting
- Formal-verification systems (AlphaProof/AlphaGeometry 2)

---
