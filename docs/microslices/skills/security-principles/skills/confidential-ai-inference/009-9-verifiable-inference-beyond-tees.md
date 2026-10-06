---
id: skill-9-verifiable-inference-beyond-tees-6972b55a95
purpose: 9 verifiable inference beyond tees
source: src/vibey_tools/skills/plugins/security-principles/skills/confidential-ai-inference/SKILL.md
requires: ["skill-8-transparency-logs-reproducible-builds-and-binary-transparency-dadaab3f53"]
links: ["skill-10-engineering-the-system-ea23bd2dd7"]
---

## 9. Verifiable inference beyond TEEs

TEEs ask you to trust hardware vendors. The alternatives replace that with cryptography or redundancy, at a cost.

| Approach | What it proves | Confidentiality of the prompt | Practical status (October 2026) |
|---|---|---|---|
| **zkML** (SNARK/STARK proof of inference) | Output = model(committed weights, input) | No — the prover sees the input; weights *can* stay hidden from the verifier | Small models practical; LLM-scale proofs research-grade and orders of magnitude slower than inference ⚠️ verify |
| **Optimistic / fraud-proof** | Output is correct unless someone disputes in a window; bisection to a single step | No | Needs determinism and a challenge period; suited to on-chain or batch settings |
| **Redundant execution** | k independent providers agree | No — *k* parties now see the prompt | Simple; multiplies cost and data exposure unless each replica is itself a TEE |
| **Sampled spot-checks / activation fingerprints** | Statistical evidence the claimed model ran | No | Emerging (for example locality-sensitive hashes of activations) ⚠️ verify |
| **FHE / MPC** | Computation on encrypted data / secret shares | Yes, cryptographically | FHE far too slow for LLM-scale serving; MPC prototypes carry large communication overhead ⚠️ verify |

- **zkML detail:** tooling such as EZKL targets small models; *zkLLM* (ACM CCS 2024) reported proofs for 13B-parameter LLaMA-family inference in minutes per inference on large GPUs ⚠️ verify the figures. Fixed-point quantization for circuits changes numerics, so the proven model is not bit-identical to the served one unless you serve the quantized version.
- **Where each fits:** TEEs for interactive, confidential serving at scale; zkML for high-value, low-volume claims ("this credit score used the audited model"); optimistic and redundant schemes for decentralized compute markets where integrity matters more than secrecy.

### Deterministic inference

Every scheme that compares outputs needs reproducibility, and GPU inference is not deterministic by default: floating-point addition is not associative, kernels use atomics, and **batch composition changes reduction order**, so the same prompt can yield different tokens depending on server load. Thinking Machines' *Defeating Nondeterminism in LLM Inference* (September 2025) attributed much of this to lack of batch invariance ⚠️ verify. Mitigations: batch-invariant kernels, fixed seeds and greedy decoding for verification runs, pinned library and driver versions, identical GPU SKUs and parallelism layout, and tolerance-based (top-k or logit-distance) comparison rather than exact token equality.

---
