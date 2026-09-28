---
id: skill-13-numbers-bb47899ed0
purpose: 13 numbers
source: src/vibey_tools/skills/plugins/vr-ar-development/skills/xr-reference/SKILL.md
requires: ["skill-12-anti-patterns-1b9eb809f2"]
links: ["skill-14-the-platform-landscape-verified-august-2026-540cff073f"]
---

## §13. Numbers

```
LATENCY  ⚠️ THE CONSTRAINT
Motion-to-photon target      <20 ms  ⚠️ the consensus rule
Gaze-to-photon (foveation)   42–91 ms tolerable; artifacts unchanged under ~60 ms
                             ⚠️ a different, looser budget than head MTP

FRAME BUDGET
72 Hz → 13.9 ms · 90 Hz → 11.1 ms · 120 Hz → 8.3 ms   ⚠️ for BOTH eyes
Low persistence illumination ~2 ms

OPTICS
⚠️ Human acuity ~60 PPD (the "retinal" target)
Render target typically 1.2–1.4× display resolution (distortion headroom)
IPD range ~54–72 mm typical adult

SENSORS
IMU ~1000 Hz, low latency, ⚠️ unbounded drift
Camera/SLAM 30–60 Hz, drift-free, ⚠️ high latency
→ fuse for both (§3)

UX
Comfortable content depth ~0.5–20 m · reading sweet spot ~1–3 m
Primary content within ~±30° of forward gaze
⚠️ Looking up is worse than looking down
```

---
