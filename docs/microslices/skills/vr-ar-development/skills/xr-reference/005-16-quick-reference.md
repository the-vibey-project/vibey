---
id: skill-16-quick-reference-8f4dd9400c
purpose: 16 quick reference
source: src/vibey_tools/skills/plugins/vr-ar-development/skills/xr-reference/SKILL.md
requires: ["skill-15-resources-30822dfa67"]
links: ["skill-17-method-0540b8bf79"]
---

## §16. Quick Reference

### 16.1 Picker
| Need | Use |
|---|---|
| Multi-platform target | ⚠️ **OpenXR + Unity or Unreal** (§7 → `xr-platforms-audio-and-comfort`, §14.2) |
| Widest reach, one codebase, lowest cost | **WebXR** (§14.2) |
| Comfortable locomotion | ⚠️ **Teleport + snap turn as defaults** (§5.4 → `xr-rendering-input-and-spatial-understanding`) |
| Precise interaction | **Controllers** — don't default to hands (§5 → `xr-rendering-input-and-spatial-understanding`) |
| Low-fatigue interaction | ⚠️ **Gaze + pinch; hands near the body** (§5.3 → `xr-rendering-input-and-spatial-understanding`) |
| Free GPU headroom | ⚠️ **Fixed foveated rendering** (§4.3 → `xr-rendering-input-and-spatial-understanding`) |
| Halve CPU draw overhead | **Single-pass/multiview stereo** (§4.1 → `xr-rendering-input-and-spatial-understanding`) |
| Antialiasing in XR | ⚠️ **MSAA, not TAA** (§4.4 → `xr-rendering-input-and-spatial-understanding`) |
| AR content that stays put | ⚠️ **Anchors, never world coordinates** (§6 → `xr-rendering-input-and-spatial-understanding`) |
| Make AR objects look real | ⚠️ **Occlusion + contact shadows** (§6 → `xr-rendering-input-and-spatial-understanding`) |
| Presence per unit effort | ⚠️ **Head-tracked spatial audio** (§8 → `xr-platforms-audio-and-comfort`) |

### 16.2 Ship checklist
- [ ] Native frame rate hit without relying on reprojection? (§4.2 → `xr-rendering-input-and-spatial-understanding`)
- [ ] Frame-time histogram clean — no 1% spikes? (§11 → `xr-ux-design-and-performance-budgeting`)
- [ ] Profiled on device, thermally soaked 20+ minutes? (§11 → `xr-ux-design-and-performance-budgeting`)
- [ ] Tested with users who have never used XR? (§1.2 → `xr-perceptual-constraints-displays-and-tracking`)
- [ ] Comfort options: vignette, snap turn, teleport, seated mode, height? (§9 → `xr-platforms-audio-and-comfort`)
- [ ] Camera never moves without user input? (§1.2 → `xr-perceptual-constraints-displays-and-tracking`, §10 → `xr-ux-design-and-performance-budgeting`)
- [ ] Text legible on device, not just in the editor? (§10 → `xr-ux-design-and-performance-budgeting`)
- [ ] UI body-locked or diegetic, not head-locked? (§10 → `xr-ux-design-and-performance-budgeting`)
- [ ] Audio head-tracked? (§8 → `xr-platforms-audio-and-comfort`)
- [ ] Tracking-loss and relocalization failure handled gracefully? (§3 → `xr-perceptual-constraints-displays-and-tracking`, §6 → `xr-rendering-input-and-spatial-understanding`)
- [ ] AR: anchors used, occlusion and contact shadows present? (§6 → `xr-rendering-input-and-spatial-understanding`)
- [ ] Accessibility: seated, one-handed, subtitles, non-stereo fallback? (§9 → `xr-platforms-audio-and-comfort`)
- [ ] Guardian/boundary interaction sane? (§9 → `xr-platforms-audio-and-comfort`)

---
