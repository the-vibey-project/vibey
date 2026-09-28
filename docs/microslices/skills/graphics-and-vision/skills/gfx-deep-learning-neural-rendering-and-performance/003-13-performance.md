---
id: skill-13-performance-cc5061d73d
purpose: 13 performance
source: src/vibey_tools/skills/plugins/graphics-and-vision/skills/gfx-deep-learning-neural-rendering-and-performance/SKILL.md
requires: ["skill-12-neural-rendering-where-the-fields-meet-ce54d7908d"]
links: []
---

## §13. Performance

**Graphics**: ⚠️ **profile before optimizing, and identify which stage is the bottleneck**
— vertex, fragment, memory bandwidth, or CPU submission. **Tools**: RenderDoc, Nsight
Graphics, PIX, Xcode's frame debugger, RGP.
**Common wins**: reduce draw calls (instancing, batching, ⚠️ **indirect and bindless
rendering**), LOD, culling, ⚠️ **overdraw reduction via depth prepass or front-to-back
sorting**, texture compression and mipmaps, and shader complexity in that order.
**⚠️ The frame budget is brutal**: 16.6 ms at 60 fps, 8.3 ms at 120, ~11 ms per eye at 90
for VR — **and VR's cost of a dropped frame is nausea, not a stutter.**

**Vision**: ⚠️ **the biggest wins are usually resolution and preprocessing, not model
architecture.** Then quantization (INT8), pruning, distillation, batching, and the right
runtime (TensorRT, ONNX Runtime, OpenVINO, Core ML, TFLite). **⚠️ Measure end-to-end
including decode, resize and colour conversion** — on many pipelines the model is not the
bottleneck.
