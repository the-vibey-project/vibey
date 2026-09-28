---
id: skill-19-quick-reference-aef714759f
purpose: 19 quick reference
source: src/vibey_tools/skills/plugins/machine-learning/skills/ml-reference/SKILL.md
requires: ["skill-18-the-canon-68b71760fe"]
links: ["skill-20-sources-and-method-f33a0dcc89"]
---

## §19. Quick Reference

### 19.1 Numbers
- **fp32 Adam training ≈ 16 bytes/parameter** before activations.
- Gradient checkpointing: **~30% more compute** for large activation memory savings.
- **Cross-entropy at init on k balanced classes ≈ ln(k)** — check this.
- **bf16 needs no loss scaling; fp16 does.**
- INT4 quantization: **~4× memory reduction**, small quality cost.
- Attention is **O(n²)** in sequence length.
- **H100 80 GB · H200 141 GB · B200 192 GB.**
- Self-hosting vs. API break-even: **cloud wins under ~8 hrs/day utilization.**

### 19.2 New-project checklist
- [ ] Is ML actually the right tool? (§1.1 → `ml-framing-data-and-classical`)
- [ ] Baseline defined and measured **first**
- [ ] Metric chosen from the decision it informs; threshold treated as tunable
- [ ] Split strategy correct for the data's structure (time? groups?)
- [ ] Preprocessing inside a `Pipeline`, fit on train only
- [ ] Leakage checklist walked (§2.1 → `ml-framing-data-and-classical`)
- [ ] Deployment constraints known **before** modeling (latency, memory, cost)
- [ ] For tabular: GBDT tried before anything deep
- [ ] Multiple seeds; variance reported
- [ ] Metrics sliced by relevant subgroups
- [ ] 50 errors read by a human
- [ ] Versions and data versioned and logged
- [ ] Monitoring and rollback in place before launch

### 19.3 Triage
| Symptom | First look |
|---|---|
| Too good to be true | **Leakage** (§2.1 → `ml-framing-data-and-classical`). Assume it until disproven |
| Great offline, bad in production | Distribution shift, or training/serving skew (§12.2 → `ml-evaluation-serving-mlops-and-safety`) |
| Loss NaN | LR, fp16 overflow (**use bf16**), log(0), bad data |
| Loss flat | LR too low, frozen params, disconnected graph |
| Can't overfit one batch | **You have a bug**, not a tuning problem (§10 → `ml-evaluation-serving-mlops-and-safety`) |
| GPU underutilized | Dataloader-bound; check batch size and workers |
| OOM | Optimizer state → 8-bit/fused; activations → checkpointing; §7.3 → `ml-deep-learning-and-training` |
| Slower after `torch.compile` | Graph breaks or recompilation on dynamic shapes (§6.1 → `ml-deep-learning-and-training`) |
| Model degraded over months | Expected — drift. Retrain (§12.3 → `ml-evaluation-serving-mlops-and-safety`) |

---
