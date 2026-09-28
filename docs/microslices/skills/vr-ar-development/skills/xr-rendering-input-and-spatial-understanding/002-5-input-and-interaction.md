---
id: skill-5-input-and-interaction-17085c4c8b
purpose: 5 input and interaction
source: src/vibey_tools/skills/plugins/vr-ar-development/skills/xr-rendering-input-and-spatial-understanding/SKILL.md
requires: ["skill-4-the-xr-rendering-pipeline-ca2256c541"]
links: ["skill-6-ar-spatial-understanding-94f6c56e47"]
---

## §5. Input and Interaction

**Controllers** — ⚠️ **still the most precise and lowest-fatigue input, with haptics and
unambiguous button state.** Don't dismiss them.

**Hand tracking** — ⚠️ **natural and requires no hardware, and it is genuinely worse for
precision work**: no haptic feedback, occlusion when hands overlap or leave the camera
frustum, and **fatigue** (§5.3). **Pinch is the reliable gesture; complex gestures are
not.**

**Eye tracking** — foveated rendering (§4.3), **gaze-based selection** (⚠️ **"gaze and
pinch" is visionOS's core interaction and it works well**), social presence via avatar
eyes, and analytics. ⚠️ **Eye data is biometric and privacy-sensitive — treat it
accordingly.**

**Others**: voice, body/face tracking, haptic gloves and vests, treadmills, **and
passthrough-based real-world input.**

### 5.3 ⚠️ Gorilla arm and interaction ergonomics
**Holding arms extended is exhausting within minutes.** **Design for hands resting near
the body**: ⚠️ **short pinch gestures over big arm movements, interaction targets below
eye level and within a comfortable cone, and no sustained holding.** **visionOS's
gaze-targets-and-hand-confirms model exists precisely to avoid this**, and it's worth
copying regardless of platform.

### 5.4 Locomotion — the highest-risk design decision
| Method | Comfort | ⚠️ Notes |
|---|---|---|
| **Room-scale physical** | ⚠️ **Best** | No conflict at all; limited by play space |
| **Teleport** | ⚠️ **Very high** | No optic flow; breaks immersion, and that's an acceptable trade |
| **Dash / blink** | High | Very fast movement reads as instant |
| **Smooth locomotion + vignette** | Moderate | ⚠️ **Offer, don't impose; always with comfort options** |
| **Smooth locomotion, no mitigation** | ⚠️ **Worst** | Common cause of first-session nausea |
| **Snap turn** | High | ⚠️ **Avoid smooth turning — rotation is worse than translation** |
| **Redirected walking** | High | Needs a large tracked space |

**⚠️ Rotation is more nauseating than translation, and yaw is the worst axis.** **Snap
turn should be the default and smooth turn opt-in.**

---
