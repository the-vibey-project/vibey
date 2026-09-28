---
id: skill-10-images-and-video-ba9cf5a77e
purpose: 10 images and video
source: src/vibey_tools/skills/plugins/signal-processing/skills/dsp-audio-rf-and-images/SKILL.md
requires: ["skill-9-rf-and-communications-44d4f48b46"]
links: []
---

## §10. Images and Video

**[DURABLE] 2D signal processing, and the concepts transfer directly.**
**2D convolution** for blur, sharpen, and edge detection (Sobel, Laplacian);
**separable kernels** (⚠️ **a 2D Gaussian is two 1D passes — O(n) instead of O(n²) per
pixel, and this is why Gaussian blur is cheap**); **2D FFT** for frequency-domain
filtering; **the DCT** as JPEG's core.

**⚠️ Aliasing appears here as moiré patterns** — and image downsampling without
pre-filtering is exactly §1.1 → `dsp-sampling-frequency-domain-and-filters`'s error in two dimensions. **Anti-aliasing in rendering is
the same problem approached from the synthesis side.**

**Also**: **image pyramids** (Gaussian, Laplacian) for multi-scale processing;
**bilateral and non-local means** filters (⚠️ **edge-preserving — linear filters can't do
this**); **optical flow** for motion; **video codecs** as motion-compensated transform
coding (H.264/AVC, H.265/HEVC, AV1, and H.266/VVC).
