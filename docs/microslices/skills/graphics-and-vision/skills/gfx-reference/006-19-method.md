---
id: skill-19-method-e1e425b94c
purpose: 19 method
source: src/vibey_tools/skills/plugins/graphics-and-vision/skills/gfx-reference/SKILL.md
requires: ["skill-18-quick-reference-52d10697c1"]
links: []
---

## §19. Method

**§1–§15 → `gfx-transforms-rasterization-and-rendering`, `gfx-gpu-real-time-techniques-and-colour`, `gfx-image-formation-classical-vision-and-geometry`, `gfx-deep-learning-neural-rendering-and-performance` rest on permanent material** — projective geometry, **Kajiya's rendering equation
(1986)**, microfacet theory, epipolar geometry, and the classical CV algorithms — sourced
from the references in §17, chiefly **Real-Time Rendering**, **PBRT**, **Hartley &
Zisserman**, and **Szeliski**. ⚠️ **None of it needed web verification, and §19's whole
point is that the ratio of permanent to perishable in this field is very high — the
frontier moves fast, the foundations do not.**

**Two searches were run in August 2026**, confined to the two genuinely moving areas:
**neural rendering** and **vision foundation models.** ⚠️ **Both are quarantined in §16 so
the rest of the document doesn't rot around them.**

**Confidence.** **High** in §1–§15 → `gfx-transforms-rasterization-and-rendering`, `gfx-gpu-real-time-techniques-and-colour`, `gfx-image-formation-classical-vision-and-geometry`, `gfx-deep-learning-neural-rendering-and-performance`: standard mathematics and long-established technique,
with the subtleties (normal matrices, Hartley normalization, perspective-correct
interpolation, warp divergence, linear-vs-sRGB) stated because ⚠️ **those are precisely
where correct-looking implementations are silently wrong.**

**High** in **§12 → `gfx-deep-learning-neural-rendering-and-performance` and §16.1's technical content** — the 3DGS description traces to the
original SIGGRAPH 2023 paper and Inria's project page: **anisotropic covariance
optimization, interleaved density control, visibility-aware differentiable rasterization,
and SfM initialization** are all as the authors describe them. ⚠️ **The observation that
3DGS is explicit rather than neural, and descends from EWA splatting (2002), is my
framing, and I think it's the single most clarifying thing to understand about it.**

⚠️ **Three hedges, all flagged in place.** **The 3DGS-vs-NeRF performance figures come
from a commercial 3D-scanning site** — consistent with the literature, but marketing-
adjacent and hugely scene- and hardware-dependent. **The OpenUSD and glTF standardization
claims come from the same source** and I have marked the OpenUSD date as reported;
⚠️ **verify against Khronos and the OpenUSD project before relying on it.** And
**§16.2's model landscape leans on Roboflow's comparison posts and similar vendor blogs** —
current and competent, but commercially interested. **The SAM 3 capability claims trace to
the paper and to independent research papers using it, which is stronger evidence than the
rankings.**

**⚠️ One judgement I'll state plainly**: the framing in §16.2 that **recognition and
segmentation were substantially absorbed by foundation models while geometry was not** is
my assessment. **I think it's well-supported — the 2026 literature still runs SfM, bundle
adjustment and RANSAC underneath the learned components — but it is an interpretation,
not a citation.**
