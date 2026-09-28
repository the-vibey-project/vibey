---
id: skill-1-the-perceptual-constraints-c277bfa210
purpose: 1 the perceptual constraints
source: src/vibey_tools/skills/plugins/vr-ar-development/skills/xr-perceptual-constraints-displays-and-tracking/SKILL.md
requires: ["skill-0-routing-7eba785dfa"]
links: ["skill-2-displays-and-optics-f374770dd2"]
---

## §1. The Perceptual Constraints

**⚠️ Read this section before writing any XR code. Everything else is downstream of it.**

### 1.1 Motion-to-photon latency
**The time from a head movement to the corresponding photons reaching the eye.**
```
sense IMU → fuse → predict → simulate → render → composite → scanout → photons
```
**⚠️ Consensus is the "20 millisecond rule": end-to-end MTP should stay below ~20 ms** to
be generally imperceptible and give a comfortable experience. **Above it, the world feels
attached to your head with elastic**, and ⚠️ **latency is a documented cause of
cybersickness and a documented reducer of presence.**

**⚠️ You cannot hit 20 ms honestly by rendering fast alone** — the pipeline is too long.
**The trick that makes XR viable is prediction plus reprojection** (§4.2 → `xr-rendering-input-and-spatial-understanding`): predict where
the head will be at scanout, and re-warp the finished frame against the newest pose
immediately before display. **⚠️ This means your effective latency is decoupled from your
frame rate — which is why a dropped frame is survivable and a broken reprojection is
not.**

**⚠️ Note the distinction for eye tracking**: gaze-contingent foveated rendering has its
own "eye-motion-to-photon" budget, and it is **more forgiving than head latency** —
measured maximum tolerable system latency for foveated rendering lands in the
**42–91 ms** range depending on foveal region size and the degradation applied, with
artifact detection reportedly unchanged below ~60 ms. ⚠️ **Do not confuse the two budgets;
they differ by roughly 3×.**

### 1.2 Cybersickness
**⚠️ The dominant explanation is sensory conflict**: your eyes report motion your
vestibular system does not. **The documented primary contributors are latency, field of
view, vergence-accommodation mismatch, and unnatural locomotion.**

> **⚠️ GOTCHA — susceptibility varies enormously between people, and developers are the
> worst possible test population.** You acclimate. ⚠️ **Something that feels fine to you
> after six months of daily use can make a first-timer ill in ninety seconds.** **Test
> with fresh users, and take the first ten minutes seriously.**

**Mitigations that have evidence behind them:**
- **⚠️ Hit frame rate consistently.** The single biggest lever.
- **Avoid imposed acceleration** — ⚠️ **the worst offender is camera motion the user did
  not initiate.** Constant velocity is much better than accelerating; instant is better
  still.
- **Dynamic FOV restriction (vignetting) during locomotion** — reduces peripheral optic
  flow, which is what drives vection.
- **⚠️ Rest frames** — a static cockpit, nose reference, or grid gives the vestibular
  system something consistent. **Peripheral teleportation and similar rest-frame designs
  are an active research direction.**
- **Foveated depth-of-field blur and peripheral degradation** — ⚠️ **reduces peripheral
  motion information, and studies indicate a measurable reduction in simulator sickness.**
- **⚠️ Never take control of the camera.** No cutscene head movement, no forced rotation,
  no screen shake.

### 1.3 Vergence-accommodation conflict
**⚠️ The unsolved optical problem of every mainstream headset.**
In natural vision, **vergence** (the eyes rotating to converge on a point) and
**accommodation** (the lens focusing) are coupled and specify the same depth. **In an HMD,
the eyes accommodate to a fixed screen distance while continuing to converge freely** on
virtual objects at varying depths.
**⚠️ The documented consequences**: discomfort and fatigue, cybersickness, longer
time-to-focus, **distorted distance perception, and impaired motor planning and control** —
⚠️ **which matters enormously for surgical training and any task where a few centimetres
of error is serious.**
**Mitigations**: **varifocal** and **multi-focal** displays (⚠️ **prototypes and
research; multi-focal AR prototypes add their own MTP burden**), light fields, and
**the practical one available today — keep interactive content in a comfortable depth
range and avoid forcing rapid depth changes.**

### 1.4 Presence
**The perceptual illusion of being there.** Built by consistent, low-latency, plausible
sensory input; ⚠️ **destroyed instantly by tracking loss, a hand passing through a solid
object, wrong-scale environments, or latency spikes.** **Presence is the product, and
§9 → `xr-platforms-audio-and-comfort` and §10 → `xr-ux-design-and-performance-budgeting` exist to protect it.**

---
