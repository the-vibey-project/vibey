---
id: skill-18-quick-reference-52d10697c1
purpose: 18 quick reference
source: src/vibey_tools/skills/plugins/graphics-and-vision/skills/gfx-reference/SKILL.md
requires: ["skill-17-books-9b10c11645"]
links: ["skill-19-method-e1e425b94c"]
---

## §18. Quick Reference

### 18.1 Picker
| Need | Use |
|---|---|
| Rotation storage and interpolation | ⚠️ **Quaternions** (§1 → `gfx-transforms-rasterization-and-rendering`) |
| Rotation optimization | ⚠️ **Lie algebra (SO(3)/SE(3))** (§1 → `gfx-transforms-rasterization-and-rendering`) |
| Many dynamic lights | Deferred or clustered forward (§6 → `gfx-gpu-real-time-techniques-and-colour`) |
| Geometric edge antialiasing only | MSAA (§6 → `gfx-gpu-real-time-techniques-and-colour`) |
| Modern AA + upscaling | ⚠️ **TAA-based (DLSS/FSR/XeSS)** (§6 → `gfx-gpu-real-time-techniques-and-colour`) |
| Ground-truth quality, offline | Path tracing (§4 → `gfx-transforms-rasterization-and-rendering`) |
| Cheap ambient occlusion | GTAO (§6 → `gfx-gpu-real-time-techniques-and-colour`) |
| Reflections including off-screen | ⚠️ **Not SSR — needs RT or probes** (§6 → `gfx-gpu-real-time-techniques-and-colour`) |
| Learn a modern graphics API first | ⚠️ **WebGPU** (§5 → `gfx-gpu-real-time-techniques-and-colour`) |
| Camera pose from a known 3D model | **PnP + RANSAC** (§9 → `gfx-image-formation-classical-vision-and-geometry`, §10 → `gfx-image-formation-classical-vision-and-geometry`) |
| Two-view geometry, calibrated | **5-point essential matrix** (§10 → `gfx-image-formation-classical-vision-and-geometry`) |
| Refine a whole reconstruction | ⚠️ **Bundle adjustment (Ceres/g2o)** (§10 → `gfx-image-formation-classical-vision-and-geometry`) |
| Real-time camera tracking | ORB-SLAM3, or ⚠️ **VIO if you have an IMU** (§10 → `gfx-image-formation-classical-vision-and-geometry`) |
| Metric scale from one camera | ⚠️ **Impossible without a prior — add IMU/stereo/known size** (§10 → `gfx-image-formation-classical-vision-and-geometry`) |
| Photorealistic capture → real-time render | ⚠️ **3DGS** (§12 → `gfx-deep-learning-neural-rendering-and-performance`, §16.1) |
| Segment anything by text prompt | **SAM 3**, or Grounded-SAM (§16.2) |
| Strong features, few labels | **DINOv3** (§16.2) |
| Fast open-vocab detection, no masks | YOLO-World (§16.2) |
| Ship on edge hardware | ⚠️ **Distil a foundation model into a small student** (§16.2) |

### 18.2 Debug checklist
- [ ] Everything black? → check transform order, winding/culling, near/far planes
- [ ] Lighting looks flat or washed out? → ⚠️ **linear vs sRGB (§7 → `gfx-gpu-real-time-techniques-and-colour`)**
- [ ] Lighting wrong under non-uniform scale? → ⚠️ **normal matrix (§1 → `gfx-transforms-rasterization-and-rendering`)**
- [ ] Textures warp toward edges? → perspective-correct interpolation (§2 → `gfx-transforms-rasterization-and-rendering`)
- [ ] Flickering surfaces at distance? → ⚠️ **push the near plane out; reversed-Z (§2 → `gfx-transforms-rasterization-and-rendering`)**
- [ ] Shadow acne or floating shadows? → normal-offset bias (§6 → `gfx-gpu-real-time-techniques-and-colour`)
- [ ] Ghosting on motion? → TAA history rejection (§6 → `gfx-gpu-real-time-techniques-and-colour`)
- [ ] Corruption on one GPU vendor only? → ⚠️ **barriers. Run validation layers (§5 → `gfx-gpu-real-time-techniques-and-colour`)**
- [ ] Reconstruction drifts or scale is wrong? → ⚠️ **monocular scale ambiguity (§10 → `gfx-image-formation-classical-vision-and-geometry`)**
- [ ] Calibration reprojection error high? → board tilt and corner coverage (§8 → `gfx-image-formation-classical-vision-and-geometry`)
- [ ] Model great in test, bad in field? → ⚠️ **domain shift, or a shortcut feature (§11 → `gfx-deep-learning-neural-rendering-and-performance`)**

---
