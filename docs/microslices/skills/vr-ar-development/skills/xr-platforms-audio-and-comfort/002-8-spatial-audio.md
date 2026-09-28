---
id: skill-8-spatial-audio-fe755091ef
purpose: 8 spatial audio
source: src/vibey_tools/skills/plugins/vr-ar-development/skills/xr-platforms-audio-and-comfort/SKILL.md
requires: ["skill-7-platforms-and-apis-faf7e1b8ff"]
links: ["skill-9-comfort-safety-accessibility-8dc168e9f4"]
---

## §8. Spatial Audio

**⚠️ Audio contributes more to presence per unit of engineering effort than almost
anything in graphics, and it is chronically neglected.**

**HRTF (head-related transfer function)** — how your head, ears and torso filter sound by
direction. Convolving with an HRTF produces convincing 3D localization over headphones.
⚠️ **HRTFs are individual; generic ones work adequately but front-back confusion is
common, and small head movements resolve it — which is why head-tracked audio matters
more than HRTF quality.**

**Ambisonics** for scene-based audio, **room acoustics** (early reflections, reverb,
**occlusion and obstruction** by geometry), and **distance attenuation with air
absorption.**
**⚠️ Head-tracked audio is non-negotiable**: the soundfield must stay fixed in world space
as the head turns. **Untracked audio destroys presence immediately.**

---
