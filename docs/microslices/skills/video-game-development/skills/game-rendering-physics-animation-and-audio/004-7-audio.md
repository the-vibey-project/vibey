---
id: skill-7-audio-e6fb999462
purpose: 7 audio
source: src/vibey_tools/skills/plugins/video-game-development/skills/game-rendering-physics-animation-and-audio/SKILL.md
requires: ["skill-6-animation-e0bfe0c01b"]
links: []
---

## §7. Audio

**[DURABLE] Audio is the most-cut and highest-return-per-dollar discipline in games.**
Players don't consciously notice good audio and immediately feel its absence.

- **Middleware**: **Wwise** and **FMOD** are the standards, and both are worth the
  integration cost on any team with a dedicated audio person. Engine-native audio is fine
  for small projects.
- **Concepts**: buses and mixing, **ducking** (dip the music under dialogue), **DSP**
  (reverb, EQ, compression), **occlusion and obstruction**, **HRTF/spatial audio**,
  attenuation curves, and **voice limiting** (⚠️ 200 simultaneous gunshots will clip and
  eat your CPU — cap and prioritize).
- **Variation is what prevents fatigue**: multiple samples per event, randomized pitch and
  volume, round-robin. A single footstep sample played 10,000 times is a defining amateur
  tell.
- **Streaming vs. in-memory**: music and dialogue stream; short SFX stay resident.
- **Loudness**: normalize to a platform target; console certification (§13.3 → `game-performance-feel-and-shipping`) has loudness
  requirements you can fail on.
