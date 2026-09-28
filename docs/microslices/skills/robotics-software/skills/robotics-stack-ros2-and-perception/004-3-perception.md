---
id: skill-3-perception-0ad064825f
purpose: 3 perception
source: src/vibey_tools/skills/plugins/robotics-software/skills/robotics-stack-ros2-and-perception/SKILL.md
requires: ["skill-2-ros-2-and-middleware-22e45f3041"]
links: ["skill-4-state-estimation-and-slam-f6210a3079"]
---

## §3. Perception

**[DURABLE] Sensor modalities and their honest failure modes** — and the failure modes
matter more than the specs:

| Sensor | Gives you | ⚠️ Fails at |
|---|---|---|
| **Camera (mono)** | Rich semantics, cheap | No metric scale; ⚠️ **motion blur, low light, direct sun, glass** |
| **Stereo** | Depth by disparity | ⚠️ **Textureless surfaces — a blank wall has no disparity** |
| **RGB-D** (structured light / ToF) | Dense depth, short range | ⚠️ **Sunlight destroys structured light**; multipath on ToF |
| **LiDAR** | Precise 3D geometry | ⚠️ **Rain, fog, dust, and retroreflectors**; sparse at range; expensive |
| **Radar** | Velocity directly (Doppler), all-weather | Low angular resolution; ⚠️ **multipath and ghost targets** |
| **IMU** | High-rate acceleration and angular rate | ⚠️ **Drifts. Always. It is a relative sensor** (§4) |
| **Wheel odometry** | Cheap relative motion | ⚠️ **Slip makes it lie confidently** |
| **F/T sensors** | Contact forces | Drift, temperature sensitivity |
| **GNSS/RTK** | Global position | ⚠️ **Urban canyon, indoors, multipath, jamming/spoofing** |

**[DURABLE] The design principle: every sensor fails in a specific, knowable way, and
good perception is chosen so that the failure modes don't correlate.** Camera + LiDAR is a
strong pairing because sun blinds one and rain degrades the other. **Two cameras is not
redundancy.**

**The processing stack**: detection and segmentation (⚠️ **now overwhelmingly learned, and
the practical constraint is latency at the edge**), 3D detection over point clouds,
tracking (Kalman/particle filters plus data association — ⚠️ **association is the hard
part, not filtering**), and increasingly **BEV (bird's-eye-view) fusion** and
**occupancy networks** as the AV-derived approach to multi-sensor fusion.

### 3.4 ⚠️ Time and transforms — the two eternal bugs

> **⚠️ GOTCHA — these two cause more robotics bugs than every algorithm combined.**
>
> **Coordinate frames.** Every measurement is in *some* frame. **`map` → `odom` → `base_link`
> → `sensor`** is the ROS convention, and **⚠️ mixing them up produces plausible, wrong
> behaviour rather than an error.** Use tf2 rigorously; **never hand-compose transforms**;
> and know your conventions — ⚠️ **REP-103 says x-forward, y-left, z-up, and quaternions
> are (x,y,z,w) in ROS and (w,x,y,z) in several libraries.** That one has cost the field
> thousands of hours.
>
> **Timestamps.** ⚠️ **Sensor data is always stale by the time you use it.** Every message
> must carry the time the measurement was *taken*, not published. Clocks across devices
> must be synchronized (**PTP** where it matters, NTP otherwise), and **latency must be
> budgeted end to end** — sensor → driver → processing → planning → control → actuator.
> **A control loop acting on 200ms-old state is a control loop with 200ms of dead time,
> and dead time destabilizes controllers** (§6 → `robotics-planning-control-and-manipulation`).

---
