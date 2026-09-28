---
id: skill-15-anti-patterns-6ccbadc07e
purpose: 15 anti patterns
source: src/vibey_tools/skills/plugins/machine-learning/skills/ml-reference/SKILL.md
requires: []
links: ["skill-16-contested-questions-ade82d56c5"]
---

## §15. Anti-Patterns

| Anti-pattern | Why | Instead |
|---|---|---|
| Using ML where rules work | Unmaintainable, undebuggable, drifts | Write the rules (§1.1 → `ml-framing-data-and-classical`) |
| No baseline | You can't tell if the model helps | Majority class / mean / linear / existing heuristic (§1.2 → `ml-framing-data-and-classical`) |
| Preprocessing before splitting | **Leakage** | Fit on train only; use a `Pipeline` (§2.1 → `ml-framing-data-and-classical`) |
| Random-splitting time series | The model sees the future | Split by time (§2.1 → `ml-framing-data-and-classical`) |
| Ignoring group structure in splits | Same entity in train and test | Grouped splits (§2.1 → `ml-framing-data-and-classical`) |
| Repeatedly evaluating on the test set | Slow-motion leakage | One final look (§2.1 → `ml-framing-data-and-classical`, §9.2 → `ml-evaluation-serving-mlops-and-safety`) |
| Celebrating a suspiciously good result | It's almost always leakage | **Go looking for the bug** (§2.1 → `ml-framing-data-and-classical`) |
| Reaching for deep learning on tabular data | GBDTs are the stronger default | XGBoost/LightGBM/CatBoost (§3.1 → `ml-framing-data-and-classical`) |
| Using accuracy on imbalanced data | 99% accuracy can be useless | PR-AUC, F1, confusion matrix (§9.1 → `ml-evaluation-serving-mlops-and-safety`) |
| Leaving the threshold at 0.5 | It's a free parameter matched to your costs | Tune it (§9.1 → `ml-evaluation-serving-mlops-and-safety`) |
| Using uncalibrated probabilities in a decision | Probabilities are meaningfully wrong | Calibrate (§3.2 → `ml-framing-data-and-classical`) |
| Reporting a single run | Much of it is seed noise | Multiple seeds + variance (§9.2 → `ml-evaluation-serving-mlops-and-safety`) |
| Comparing against an untuned baseline | Not a comparison | Tune both equally (§9.2 → `ml-evaluation-serving-mlops-and-safety`) |
| Only aggregate metrics | Hides systematic subgroup failure | Slice everything (§9.2 → `ml-evaluation-serving-mlops-and-safety`, §14.2 → `ml-evaluation-serving-mlops-and-safety`) |
| Never reading the model's errors | Highest-value diagnostic, skipped | Read 50 mistakes (§9.2 → `ml-evaluation-serving-mlops-and-safety`) |
| Trusting public benchmark scores | **Contamination is pervasive** | Build a private eval set (§9.3 → `ml-evaluation-serving-mlops-and-safety`) |
| Adam with weight decay | Not equivalent to true weight decay | **AdamW** (§4.2 → `ml-deep-learning-and-training`) |
| Tuning architecture before learning rate | LR dominates | Sweep LR first (§4.2 → `ml-deep-learning-and-training`) |
| Debugging without overfitting one batch | You're guessing | Overfit 2–10 examples first (§10 → `ml-evaluation-serving-mlops-and-safety`) |
| Using fp16 without loss scaling | Gradient underflow → NaN | **bf16** (§7.2 → `ml-deep-learning-and-training`) |
| Fine-tuning to add knowledge | Teaches behaviour well, facts poorly | **Retrieve** (§8 → `ml-deep-learning-and-training`) |
| Fine-tuning without checking for forgetting | Narrow gains, broad losses | Evaluate untrained capabilities (§8 → `ml-deep-learning-and-training`) |
| Computing features in two codepaths | **Training/serving skew** | Feature store or one shared path (§12.2 → `ml-evaluation-serving-mlops-and-safety`) |
| Deploying without monitoring | Silent degradation | Monitor predictions and inputs (§12.3 → `ml-evaluation-serving-mlops-and-safety`) |
| No rollback path | A bad model is an outage | Instant rollback (§12.3 → `ml-evaluation-serving-mlops-and-safety`) |
| Scaling hardware before profiling | Most jobs are dataloader-bound | Profile first (§13 → `ml-evaluation-serving-mlops-and-safety`) |
| Assuming quantization is free | Degradation concentrates in hard cases | Evaluate quantized on **your** task (§11.3 → `ml-evaluation-serving-mlops-and-safety`) |
| Reading t-SNE/UMAP distances as meaningful | They aren't | Visualization only (§3.2 → `ml-framing-data-and-classical`) |
| Treating feature importance as causal | It describes the model, not the world | Causal methods, or don't claim it (§14.1 → `ml-evaluation-serving-mlops-and-safety`) |
| Treating attention as explanation | Well-known negative result | Other methods (§14.1 → `ml-evaluation-serving-mlops-and-safety`) |
| Loading pickled checkpoints from strangers | Arbitrary code execution | **safetensors** (§14.3 → `ml-evaluation-serving-mlops-and-safety`) |
| Ignoring `torch.compile` graph breaks | Silently loses the speedup | `error_on_graph_break()` (§6.1 → `ml-deep-learning-and-training`) |

---
