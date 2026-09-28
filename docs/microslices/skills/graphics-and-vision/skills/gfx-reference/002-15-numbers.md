---
id: skill-15-numbers-ed3426537d
purpose: 15 numbers
source: src/vibey_tools/skills/plugins/graphics-and-vision/skills/gfx-reference/SKILL.md
requires: ["skill-14-anti-patterns-589685f54e"]
links: ["skill-16-what-actually-moved-verified-august-2026-52866c42c4"]
---

## §15. Numbers

```
FRAME BUDGETS
60 fps = 16.6 ms · 120 fps = 8.3 ms · ⚠️ VR 90 Hz ≈ 11 ms per eye
GPU warp/wavefront: 32 (NVIDIA) · 32/64 (AMD)

MATH
Homogeneous: position w=1, direction w=0
⚠️ Normals: inverse transpose · Quaternion: q and −q are the same rotation
NDC depth: OpenGL [−1,1] · D3D/Vulkan/Metal [0,1]
Monte Carlo variance ~1/√N  ⚠️ (4× samples to halve noise)
SH: 9 coefficients ≈ diffuse environment lighting

PBR
Dielectric F0 ≈ 0.04 (4%) · Metals: no diffuse, tinted specular
GGX/Trowbridge-Reitz for D · Schlick for F · Smith for G

VISION
⚠️ Stereo depth error ∝ Z² · Z = f·B/d
Essential matrix: 5 DOF, t up to scale, 4 candidate decompositions
⚠️ Shot noise is Poisson — SNR ∝ √signal
Bayer: 2 green per 1 red, 1 blue

NEURAL RENDERING (§16.1 for verification)
NeRF ~5 fps, hours to train · 3DGS 100+ fps, minutes to train
Quality both ~25–33 dB PSNR
```

---
