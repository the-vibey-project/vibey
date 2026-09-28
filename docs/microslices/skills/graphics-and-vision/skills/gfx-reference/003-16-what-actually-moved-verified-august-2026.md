---
id: skill-16-what-actually-moved-verified-august-2026-52866c42c4
purpose: 16 what actually moved verified august 2026
source: src/vibey_tools/skills/plugins/graphics-and-vision/skills/gfx-reference/SKILL.md
requires: ["skill-15-numbers-ed3426537d"]
links: ["skill-17-books-9b10c11645"]
---

## §16. What Actually Moved — verified August 2026

**⚠️ Everything in §1–§11 → `gfx-transforms-rasterization-and-rendering`, `gfx-gpu-real-time-techniques-and-colour`, `gfx-image-formation-classical-vision-and-geometry`, `gfx-deep-learning-neural-rendering-and-performance` is stable. These two areas are not.**

### 16.1 Neural rendering: 3DGS has become the practical default
- **3DGS** was introduced by **Kerbl et al. at SIGGRAPH 2023** (ACM TOG 42(4)), and
  **demonstrated state-of-the-art quality matching or exceeding Mip-NeRF 360** on
  Tanks and Temples and the synthetic NeRF dataset.
- **⚠️ Reported comparison against NeRF: ~100+ fps versus roughly 5 fps, training in
  minutes rather than hours, at equal or better quality (~25–33 dB PSNR).**
- **As of early 2026 it is described as one of the dominant paradigms in 3D scene
  representation, increasingly displacing NeRF-based approaches**, with commercial
  adoption across VR/AR, VFX, real estate and autonomous driving, and consumer capture via
  Luma AI, Polycam and similar.
- **⚠️ The standardization signal is the strongest evidence it's durable**: adoption into
  **OpenUSD (reported April 2026)** and **Khronos glTF via a `KHR_gaussian_splatting`
  extension.** ⚠️ **A representation getting into the interchange standards is what
  separates a technique from a research result.**
- **Active research directions**: compression and pruning (⚠️ **memory is the main
  practical constraint — LightGaussian reports ~15× reduction with 200+ fps; RadSplat
  reports 900+ fps**), reflections and specular handling, mesh extraction, semantics
  (LERF, GARField), robotics and driving applications, and ray-traced Gaussians.

> **⚠️ GOTCHA — two cautions on the numbers above.** **The fps and PSNR comparisons come
> from a commercial 3D-scanning site**, and while they are consistent with the original
> paper's claims and the broad literature, ⚠️ **they are marketing-adjacent and vary
> enormously with scene, resolution and hardware. Treat them as order-of-magnitude.**
> **And "3DGS replaced NeRF" is too strong**: ⚠️ **NeRF-family methods remain competitive
> where the scene is small and quality matters more than speed, and much 3DGS research
> still benchmarks against Mip-NeRF 360.** **The right claim is that 3DGS won the
> real-time and production niche decisively.**

### 16.2 Vision foundation models
**⚠️ The structural change: task-specific models trained on narrow datasets have been
substantially displaced by large pretrained backbones you prompt, adapt, or distil.**

**The current landscape (August 2026):**
- **SAM 3** (Meta, late 2025) — ⚠️ **the significant step is from geometry to concepts.**
  SAM 1 (2023) segmented from clicks and boxes on images; SAM 2 (2024) added video
  tracking; **SAM 3 introduces Promptable Concept Segmentation — a short noun phrase
  ("yellow school bus") or an image exemplar finds and segments *all* instances across an
  image or video.** ⚠️ **It's open-vocabulary rather than a fixed taxonomy.**
- **DINOv3** — self-supervised backbone; ⚠️ **the choice when you need strong features
  with limited labels**, with distilled variants (ViT-S/B/L, ConvNeXt) for edge deployment.
- **Grounding DINO** — text-prompted bounding boxes; **YOLO-World** — fast open-vocabulary
  detection without masks; **RF-DETR** and **YOLO26** for task-specific speed;
  **CLIP / SigLIP 2** for embeddings and zero-shot; **Florence-2** (compact multi-task);
  **Qwen3-VL** (broader visual reasoning, VQA, documents); **Depth Anything 3**.
- **⚠️ The dominant production pattern is composition, not a single model**: e.g. text
  prompt → Grounding DINO detection → SAM segmentation (**Grounded-SAM**), or
  open-vocabulary detection → promptable segmentation and tracking → self-supervised
  embedding → a small task head.
- **⚠️ And the deployment pattern is distil-then-ship**: use the foundation model to
  generate labels or as a teacher, then run a small task-specific student in production.
  A 2026 paper distils **SAM 3's 446M-parameter Perception Encoder into a 40.66M student**,
  reporting **~7.8× parameter reduction and ~3× lower peak VRAM for ~1.7 points of MOTA** —
  ⚠️ **which is the shape of the whole trend: foundation models for labels and prototyping,
  compact models for deployment.**

**⚠️ What this does NOT mean.** **Classical CV (§9 → `gfx-image-formation-classical-vision-and-geometry`) and multiple view geometry (§10 → `gfx-image-formation-classical-vision-and-geometry`) are
not obsolete** — ⚠️ **calibration, epipolar geometry, RANSAC, bundle adjustment and
optical flow remain the correct tools, and a foundation model does not give you metric
3D.** **The honest framing is that recognition and segmentation were substantially
absorbed by foundation models; geometry was not.**

⚠️ **Sourcing caveat**: much of the model-landscape detail above comes from **Roboflow's
comparison posts and similar vendor blogs**, which are competent and current but are
commercially interested in the tooling ecosystem. **The SAM 3 architecture claims trace to
the paper and to independent research using it**; the model rankings should be read as
orientation, not evaluation.

---
