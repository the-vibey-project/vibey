---
id: skill-17-method-0540b8bf79
purpose: 17 method
source: src/vibey_tools/skills/plugins/vr-ar-development/skills/xr-reference/SKILL.md
requires: ["skill-16-quick-reference-8f4dd9400c"]
links: []
---

## §17. Method

**§1–§11 → `xr-perceptual-constraints-displays-and-tracking`, `xr-rendering-input-and-spatial-understanding`, `xr-platforms-audio-and-comfort`, `xr-ux-design-and-performance-budgeting` rest on perceptual research and stable engineering practice** — **LaValle**,
**Jerald**, the platform best-practice documents, and the IEEE VR / ISMAR literature.
⚠️ **Human physiology does not version, which is why §1 → `xr-perceptual-constraints-displays-and-tracking` is the most durable part of this
document and the part I'd read first.**

**Scoped to complement**: rasterization, PBR and the rendering equation sit in a graphics
reference; SLAM, VIO and multi-view geometry in a computer-vision reference. ⚠️ **§3 → `xr-perceptual-constraints-displays-and-tracking` and
§6 → `xr-rendering-input-and-spatial-understanding` deliberately point at those rather than restating them.**

**Two searches were run in August 2026**: **the platform and hardware landscape**, and
**the perceptual thresholds** (motion-to-photon, cybersickness factors, VAC, foveated
rendering latency).

**Confidence.** **High** in §1 → `xr-perceptual-constraints-displays-and-tracking` — the 20 ms MTP consensus, the four primary cybersickness
contributors, the VAC consequence list, and the 42–91 ms foveated-rendering latency
tolerance all come from **peer-reviewed sources and are consistent across them.**
⚠️ **The §1.1 → `xr-perceptual-constraints-displays-and-tracking` point that gaze latency and head latency are different budgets by roughly 3×
is worth internalizing and is frequently conflated in practitioner writing.**
**High** in §2–§11 → `xr-perceptual-constraints-displays-and-tracking`, `xr-rendering-input-and-spatial-understanding`, `xr-platforms-audio-and-comfort`, `xr-ux-design-and-performance-budgeting`, which are established practice.

⚠️ **§14 is explicitly the weak section and is flagged as such in place.** The sourcing is
**XR trade press, vendor blogs, and development agencies who sell XR services** — several
of the comparison articles returned are marketing for consultancies. **The structural
claims are corroborated across independent sources** (OpenXR as the portability layer;
Android XR rising; Quest holding installed-base advantage; smart glasses growing faster
than headsets). ⚠️ **The specific figures — the 40% WebXR growth, the 38% coverage share,
the 15–25% PolySpatial overhead, prices and roadmap dates — are single-source or
vendor-adjacent, and I have attributed rather than asserted them.** **Verify before
committing budget.**

**§14.2 is the part I'd act on**: ⚠️ **the OpenXR argument holds regardless of which
hardware vendor wins, which is precisely what makes it the safe architectural bet.**
