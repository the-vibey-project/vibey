---
id: skill-safety-alignment-governance-f1d8565664
purpose: safety alignment governance
source: src/vibey_tools/skills/plugins/ai-and-data/skills/ai-ml-landscape/SKILL.md
requires: ["skill-advanced-architectures-9d808ee3d6"]
links: ["skill-durable-principles-outlast-model-names-d613d40a98"]
---

## Safety, Alignment & Governance

### Alignment Approaches
- **Constitutional AI / RLAIF** (Anthropic): AI self-critique for alignment
- **Mechanistic interpretability**: sparse autoencoders decompose superposed/polysemantic activations; circuit tracing with cross-layer transcoders lets researchers trace and intervene on causal pathways (Anthropic, open-sourced May 2025; MIT Tech Review 2026 Breakthrough Technology)
- Outer alignment (specification) vs inner alignment (goal generalization)
- Reward hacking and Goodhart's Law: recurring failure modes

### EU AI Act Timeline (Critical Deadlines)
| Date | What takes effect |
|---|---|
| Aug 1, 2024 | In force |
| Feb 2, 2025 | Prohibited practices + AI literacy obligations |
| Aug 2, 2025 | GPAI (General Purpose AI) obligations |
| **Aug 2, 2026** | **GPAI enforcement powers and fines; high-risk system obligations** |
| Aug 2, 2027 | Legacy-GPAI compliance deadline |

Fines: up to €35M or 7% of global turnover (prohibited practices) — higher ceiling than GDPR. The voluntary GPAI Code of Practice offers a "presumption of conformity" safe harbor.

**Action**: If you touch EU users, classify your system now against the AI Act risk tiers. If you fine-tune a GPAI model substantially, you may become a "provider" with heavier obligations.

### Fairness
Demographic parity vs equalized odds vs individual fairness are mutually incompatible (impossibility theorems). Tools: Fairlearn, AI Fairness 360.

### Privacy
Differential privacy, federated learning, and defenses against membership-inference/model-inversion/poisoning attacks.

### US Framework
NIST AI RMF (Govern/Map/Measure/Manage) is the US reference standard.

---
