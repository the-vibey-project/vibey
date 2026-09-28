---
id: skill-9-classical-computer-vision-35e5debbe6
purpose: 9 classical computer vision
source: src/vibey_tools/skills/plugins/graphics-and-vision/skills/gfx-image-formation-classical-vision-and-geometry/SKILL.md
requires: ["skill-8-image-formation-and-calibration-ea1be9776e"]
links: ["skill-10-multiple-view-geometry-e360b169a5"]
---

## §9. Classical Computer Vision

**⚠️ Still the right answer for many problems, and cheaper and more debuggable than a
network.**

**Filtering**: convolution, Gaussian blur (⚠️ **separable — `O(n)` per pixel instead of
`O(n²)`**), median (edge-preserving, good for salt-and-pepper), bilateral (edge-preserving
smoothing), morphological (erode, dilate, open, close).

**Edges**: Sobel/Scharr gradients, **Canny** (⚠️ **gradient → non-maximum suppression →
hysteresis thresholding — the double threshold is what makes it robust**), Laplacian of
Gaussian.

**Features**: **Harris** corners (⚠️ **the structure tensor's eigenvalues distinguish flat,
edge and corner**), **SIFT** (⚠️ **scale and rotation invariant; the benchmark for two
decades and now patent-free**), SURF, **ORB** (⚠️ **fast, binary descriptor, free — the
default for real-time SLAM**), AKAZE, and learned features (SuperPoint, DISK)
with **learned matching (SuperGlue, LightGlue)** — ⚠️ **which substantially outperform
nearest-neighbour matching on hard pairs.**

**Matching and robustness**: ratio test (Lowe), and **RANSAC** — ⚠️ **the workhorse:
randomly sample a minimal set, fit, count inliers, repeat. Everything in §10 depends on it,
because feature matches always contain outliers.** MAGSAC++ is the modern variant.

**Other classical**: Hough transform, template matching, optical flow (**Lucas-Kanade**
sparse, **Farnebäck** dense, ⚠️ **RAFT and successors for learned flow**), background
subtraction, watershed and graph-cut segmentation.

---
