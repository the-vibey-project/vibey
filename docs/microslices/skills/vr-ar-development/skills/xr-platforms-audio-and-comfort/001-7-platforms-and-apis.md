---
id: skill-7-platforms-and-apis-faf7e1b8ff
purpose: 7 platforms and apis
source: src/vibey_tools/skills/plugins/vr-ar-development/skills/xr-platforms-audio-and-comfort/SKILL.md
requires: []
links: ["skill-8-spatial-audio-fe755091ef"]
---

## §7. Platforms and APIs

**⚠️ OpenXR (Khronos) is the answer to the fragmentation question**: a royalty-free open
standard providing a unified API across headsets, acting as an abstraction layer so
**applications built against OpenXR run on any conformant headset without
modification.** ⚠️ **Both Unity and Unreal recommend OpenXR for cross-platform XR, and
maintaining separate SteamVR / Meta-native / MSMR code paths is significant avoidable
overhead.** **Any project targeting more than one platform should build on it** (§14 → `xr-reference`).

**Engines**: **Unity** (⚠️ **the most production-ready cross-platform option; XR
Interaction Toolkit; PolySpatial for visionOS**), **Unreal** (higher fidelity, heavier),
**Godot** (improving OpenXR support), and **native** (RealityKit/ARKit on Apple, Jetpack
XR on Android XR).
**Web**: **WebXR** — ⚠️ **one codebase across headsets and phone browsers; Three.js,
Babylon.js, A-Frame, React Three Fiber** (§14.2 → `xr-reference`).

**⚠️ Abstraction has a cost worth knowing about**: Unity's PolySpatial layer for visionOS
is reported at **15–25% worse rendering performance than native RealityKit**, with some
visionOS-specific features not reachable through it. **Cross-platform is a real trade,
not a free win.**

---
