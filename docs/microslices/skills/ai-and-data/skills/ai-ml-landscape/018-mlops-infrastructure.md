---
id: skill-mlops-infrastructure-65bf7541d8
purpose: mlops infrastructure
source: src/vibey_tools/skills/plugins/ai-and-data/skills/ai-ml-landscape/SKILL.md
requires: ["skill-generative-ai-across-modalities-0275672725"]
links: ["skill-advanced-architectures-9d808ee3d6"]
---

## MLOps & Infrastructure

### Hardware
| Chip | Key spec | Notes |
|---|---|---|
| NVIDIA H100/H200 (Hopper) | 80GB/141GB HBM3 | Current production standard |
| B200/GB200 (Blackwell) | 192GB HBM3e at 8TB/s | ~2.5–3× H100 training; GB200 NVL72 trained Llama 3.1 405B in ~10 min on 5,120 GPUs (MLPerf) |
| AMD MI300X/MI325X/MI355X | 192–288GB HBM3 | More memory; CUDA/ROCm moat keeps NVIDIA at ~80%+ share |
| Google TPU v5/v6e | — | JAX/XLA affinity |
| Groq LPU | — | Deterministic high-throughput inference |

### Frameworks
- **PyTorch**: dominant (eager + torch.compile/Inductor)
- **JAX**: TPU/research
- **Hugging Face stack**: Transformers, Diffusers, PEFT, TRL, Datasets, Accelerate — the default
- **Experiment tracking**: W&B (research favorite), MLflow (open, ubiquitous)

### Observability & Monitoring
- **LLM serving/observability**: LangSmith, Langfuse, Arize Phoenix, Helicone, Braintrust, W&B Weave
- **Drift/monitoring**: Evidently, NannyML, Arize, WhyLabs, Fiddler; PSI/KS tests; distinguish covariate/label/concept shift
- **Explainability**: SHAP/LIME/Integrated Gradients (caution: attention weights ≠ explanations)

---
