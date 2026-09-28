---
id: skill-11-deep-learning-for-vision-4ba4602bbd
purpose: 11 deep learning for vision
source: src/vibey_tools/skills/plugins/graphics-and-vision/skills/gfx-deep-learning-neural-rendering-and-performance/SKILL.md
requires: []
links: ["skill-12-neural-rendering-where-the-fields-meet-ce54d7908d"]
---

## §11. Deep Learning for Vision

**⚠️ The general ML framework sits in an ML reference; here's what's vision-specific.**

**CNNs**: convolution as a learned filter bank with **weight sharing and translation
equivariance** — ⚠️ **the inductive bias that made vision learnable with limited data.**
Receptive field, stride, dilation, pooling. **ResNet's skip connections** solved the
degradation problem and made depth trainable.

**Vision Transformers**: image → patches → tokens → self-attention.
⚠️ **ViTs have weaker inductive bias than CNNs, so they need more data or stronger
augmentation — but they scale better and dominate at large scale.** Hierarchical variants
(Swin) reintroduce locality.

**Tasks and the standard architectures**: classification; **detection** (two-stage
R-CNN family, one-stage YOLO/SSD/RetinaNet, ⚠️ **DETR's set-prediction formulation removed
NMS and anchor design — a genuine simplification**); **segmentation** (semantic: U-Net,
DeepLab with atrous convolution; instance: Mask R-CNN; panoptic); depth estimation; pose
estimation; tracking; and generation (§16.2 → `gfx-reference` for the current model landscape).

**⚠️ The practical failure modes that matter more than architecture choice:**
- **Data quality and label noise dominate.** ⚠️ **Almost always worth more than a better
  model.**
- **Augmentation is where much of the performance lives** — and ⚠️ **an augmentation that
  breaks the task's invariance (horizontal flip on text or on left/right-labelled data)
  silently caps your ceiling.**
- **Class imbalance** — focal loss, resampling.
- **⚠️ Domain shift**: train on daylight, deploy at night. **Test-set performance is not
  deployment performance**, and the gap is where vision systems fail in the field.
- **⚠️ Shortcut learning** — the model keys on the watermark, the hospital's scanner, or
  the ruler in the frame. See a biomedical-engineering reference §4.3 for documented
  cases.

---
