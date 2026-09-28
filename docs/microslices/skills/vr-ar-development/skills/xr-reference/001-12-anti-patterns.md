---
id: skill-12-anti-patterns-1b9eb809f2
purpose: 12 anti patterns
source: src/vibey_tools/skills/plugins/vr-ar-development/skills/xr-reference/SKILL.md
requires: []
links: ["skill-13-numbers-bb47899ed0"]
---

## §12. Anti-Patterns

| Anti-pattern | Why |
|---|---|
| Testing comfort only on yourself | ⚠️ **You acclimated. Fresh users are the test** (§1.2 → `xr-perceptual-constraints-displays-and-tracking`) |
| Taking camera control from the user | ⚠️ **Reliable nausea** (§1.2 → `xr-perceptual-constraints-displays-and-tracking`, §10 → `xr-ux-design-and-performance-budgeting`) |
| Smooth locomotion with no comfort options | First-session sickness (§5.4 → `xr-rendering-input-and-spatial-understanding`) |
| Smooth turning as the default | ⚠️ **Yaw rotation is the worst axis. Snap turn** (§5.4 → `xr-rendering-input-and-spatial-understanding`) |
| Relying on ASW/reprojection to hit frame rate | ⚠️ **It's a safety net, not a budget** (§4.2 → `xr-rendering-input-and-spatial-understanding`) |
| Frame rate as the thing you sacrifice | ⚠️ **Drop render scale instead** (§11 → `xr-ux-design-and-performance-budgeting`) |
| Profiling for 20 seconds on a mobile SoC | Thermal throttling changes everything (§11 → `xr-ux-design-and-performance-budgeting`) |
| Optimizing to average frame time | ⚠️ **A 1% spike is a visible hitch** (§11 → `xr-ux-design-and-performance-budgeting`) |
| Rendering the scene twice, naively | Single-pass/multiview exists (§4.1 → `xr-rendering-input-and-spatial-understanding`) |
| TAA in XR | ⚠️ **Ghosting is far worse in stereo. Prefer MSAA** (§4.4 → `xr-rendering-input-and-spatial-understanding`) |
| Rendering at exactly display resolution | ⚠️ **Distortion resampling eats centre detail** (§2 → `xr-perceptual-constraints-displays-and-tracking`, §4.4 → `xr-rendering-input-and-spatial-understanding`) |
| Head-locked UI panels | Uncomfortable, breaks presence (§10 → `xr-ux-design-and-performance-budgeting`) |
| Desktop-sized text | ⚠️ **PPD is not monitor PPI. Test on device** (§10 → `xr-ux-design-and-performance-budgeting`) |
| Content anchored to world origin in AR | ⚠️ **Origin drifts as SLAM refines. Use anchors** (§6 → `xr-rendering-input-and-spatial-understanding`) |
| Shipping AR without occlusion or contact shadows | ⚠️ **Objects float; the illusion never forms** (§6 → `xr-rendering-input-and-spatial-understanding`) |
| Expecting real-world occlusion on optical see-through | ⚠️ **Physically impossible — additive light only** (§2 → `xr-perceptual-constraints-displays-and-tracking`) |
| Untracked audio | Destroys presence instantly (§8 → `xr-platforms-audio-and-comfort`) |
| Complex hand gestures as core input | ⚠️ **Pinch is reliable; little else is** (§5 → `xr-rendering-input-and-spatial-understanding`) |
| Interaction requiring extended arms | ⚠️ **Gorilla arm within minutes** (§5.3 → `xr-rendering-input-and-spatial-understanding`) |
| Depth as the only channel for critical info | Not everyone fuses stereo (§9 → `xr-platforms-audio-and-comfort`) |
| No boundary/guardian consideration | People hit walls and each other (§9 → `xr-platforms-audio-and-comfort`) |
| Assuming inside-out tracking always works | ⚠️ **Mirrors, low light, moving vehicles** (§3 → `xr-perceptual-constraints-displays-and-tracking`) |
| Single-platform native SDK for a multi-platform product | ⚠️ **OpenXR exists for this** (§7 → `xr-platforms-audio-and-comfort`) |
| Treating eye-tracking data casually | It's biometric (§5 → `xr-rendering-input-and-spatial-understanding`) |

---
