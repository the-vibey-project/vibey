---
id: skill-6-the-ecosystem-60b0974906
purpose: 6 the ecosystem
source: src/vibey_tools/skills/plugins/machine-learning/skills/ml-deep-learning-and-training/SKILL.md
requires: ["skill-5-architectures-fddc6c82c9"]
links: ["skill-7-training-at-scale-9b995b1d59"]
---

## §6. The Ecosystem

### 6.1 PyTorch

**[VERSIONED] PyTorch 2.13 is current (July 2026)**, with a roughly quarterly cadence.
The parts that matter:

**`torch.compile`** — the headline feature since 2.0. Traces your model (TorchDynamo),
lowers it (TorchInductor), and generates fused Triton (or now **CuTeDSL**) kernels.
**Typically a substantial speedup for free.** ⚠️ **Watch for graph breaks** — Python
constructs Dynamo can't trace force it to fall back, silently costing you the speedup;
`torch._dynamo.error_on_graph_break()` makes that loud rather than silent.
**Recompilation** on changing shapes is the other tax — mark dynamic dimensions explicitly.

**Other things worth knowing**: `torch.export` is the unified capture path (legacy
`torch.jit` and old ONNX flows are deprecated or removed); **`weights_only=True` is the
default for `torch.load` since 2.6** — a genuine security improvement, since pickle
deserialization is arbitrary code execution; **FlexAttention** for custom attention
patterns without writing kernels; **AOTInductor** for ahead-of-time compilation.

### 6.2 The rest of the stack

| Layer | Tools |
|---|---|
| **Frameworks** | **PyTorch** (dominant in research and increasingly production), **JAX** (functional, `jit`/`grad`/`vmap`/`pmap`, strong on TPU, favored for large-scale research), TensorFlow/Keras (legacy-heavy but alive), **MLX** (Apple Silicon) |
| **Training loops** | **Lightning**, **HF Accelerate**, **torchtune**, raw loops (fine, and often clearer) |
| **Models and data** | **Hugging Face** `transformers`, `datasets`, `tokenizers`, `peft`, `trl` — effectively the industry's default distribution channel |
| **Classical** | scikit-learn, XGBoost, LightGBM, CatBoost, statsmodels |
| **Numerics** | NumPy, pandas, **Polars** (faster, saner API, increasingly the default for new work), DuckDB, Arrow |
| **Kernels** | **Triton** (write GPU kernels in Python), CUDA, FlashAttention, **FlashInfer** |
| **Experiment tracking** | Weights & Biases, MLflow, TensorBoard, Aim |
| **Serving** | **vLLM**, **SGLang**, TensorRT-LLM, Triton Inference Server, Ray Serve, llama.cpp/Ollama (§11 → `ml-evaluation-serving-mlops-and-safety`) |
| **Orchestration** | Ray, Kubeflow, Airflow, Prefect, SLURM (still the HPC standard) |

**[DURABLE] Pin your versions and record them.** The ML stack breaks compatibility
constantly, and "it worked last month" is a real and frequent failure.

---
