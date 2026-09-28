---
id: skill-3-tracking-f3ef506358
purpose: 3 tracking
source: src/vibey_tools/skills/plugins/vr-ar-development/skills/xr-perceptual-constraints-displays-and-tracking/SKILL.md
requires: ["skill-2-displays-and-optics-f374770dd2"]
links: []
---

## §3. Tracking

**3DoF** (rotation only) vs **6DoF** (rotation + position). ⚠️ **3DoF for seated video;
anything interactive needs 6DoF.**

**Approaches**: **outside-in** (external base stations — ⚠️ **highly accurate, fixed
volume, setup burden**) vs **inside-out** (on-headset cameras running SLAM — ⚠️ **the
consumer standard; no setup, but it fails in the conditions SLAM fails in**).

**⚠️ The sensor fusion is the whole trick**: an **IMU** gives you angular rate and
acceleration at ~1000 Hz with **very low latency but unbounded drift** (double-integrating
accelerometer noise diverges fast). **Cameras give you drift-free absolute pose at 30–60 Hz
with high latency.** **Fusing them — typically an EKF or a factor graph — gives you both**,
and this is exactly the VIO problem from a computer-vision reference.

**⚠️ Prediction is mandatory** (§1.1): you must render for where the head *will* be.
**Prediction error shows up as swimming or overshoot on rapid head turns** — and ⚠️ **it's
worse the longer your pipeline, which is another reason to keep it short.**

**⚠️ Where inside-out tracking actually fails** — design for these, don't hope:
featureless white walls, ⚠️ **low light**, **highly repetitive texture** (patterned
carpet, brick), **mirrors and large glass**, ⚠️ **moving environments — a train, a car, a
boat, where the visual world and the vestibular world genuinely disagree**, and rapid
motion causing blur. **Detect tracking degradation and degrade gracefully rather than
letting the world lurch.**

**Controller tracking**: constellation IR + IMU, or ⚠️ **camera-visible controllers,
which lose tracking behind the body or out of the camera frustum — hence the IMU dead
reckoning that briefly covers the gap.**
