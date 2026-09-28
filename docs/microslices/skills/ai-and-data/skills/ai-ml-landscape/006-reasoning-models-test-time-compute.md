---
id: skill-reasoning-models-test-time-compute-68e64b76c1
purpose: reasoning models test time compute
source: src/vibey_tools/skills/plugins/ai-and-data/skills/ai-ml-landscape/SKILL.md
requires: ["skill-build-pattern-for-llm-applications-0189a87f68"]
links: ["skill-classical-ml-tabular-data-44244ce7bd"]
---

## Reasoning Models & Test-Time Compute

The o1/o3/R1 paradigm: spending more inference compute on chain-of-thought "thinking tokens" is a complementary scaling axis to parameters/data.

**Process Reward Models (PRMs)**: score intermediate reasoning steps; outperform outcome-only rewards on math (GenPRM: 1.5B model beats GPT-4o on ProcessBench via test-time scaling).

**GRPO** (Group Relative Policy Optimization): critic-free, group-relative RL with verifiable rewards (RLVR). Dominant post-training method for reasoning. Spawned variants DAPO, Dr. GRPO, GSPO, GMPO.

**When reasoning tokens are worth it**: genuine multi-step reasoning (math, code generation, legal analysis). Wasteful when wired into pipelines expecting short outputs.

---
