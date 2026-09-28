---
id: skill-11-drones-and-uas-da120ed3aa
purpose: 11 drones and uas
source: src/vibey_tools/skills/plugins/aerospace-engineering/skills/aero-drones-launch-vehicles-flight-test-and-design/SKILL.md
requires: []
links: ["skill-12-launch-vehicles-8f651432d9"]
---

## §11. Drones and UAS

### 11.1 Multirotor dynamics
**⚠️ A quadrotor has four actuators and six degrees of freedom — it is underactuated, and
that shapes everything.** **It cannot translate without tilting.**
```
Thrust    T ∝ ω²        ⚠️ so control is quadratic in motor speed
Roll/pitch  differential thrust across opposing pairs
Yaw       ⚠️ differential TORQUE — speed up one rotation direction, slow the other.
          This is why yaw authority is weak and yaw is the slowest axis
```
**⚠️ Control architecture is nested loops**: **rate (inner, fast, gyro-driven) → attitude →
velocity → position (outer, slow, GNSS-driven).** ⚠️ **Tune inner loops first; a badly
tuned rate loop cannot be fixed by the outer loops.**
**State estimation** — ⚠️ **complementary or Kalman filter fusing IMU with magnetometer,
barometer, GNSS and optical flow.** ⚠️ **Magnetometers are routinely corrupted by motor
currents and nearby steel; most "toilet bowling" behaviour is a compass problem.**

**⚠️ Physics of scale, and it's the reason drones exist as a category**: **rotor thrust
scales with disc area while mass scales with volume**, ⚠️ **so small multirotors have
enormous thrust-to-weight and very fast attitude dynamics.** **The same design does not
scale up gracefully.**
**⚠️ Endurance is brutally limited**: **typical small multirotor 20–40 minutes**, because
**hover consumes power continuously and battery specific energy (~250–300 Wh/kg for Li-ion)
is roughly 50× worse than kerosene.** **Fixed-wing and VTOL-hybrid designs exist precisely
to escape this.**

### 11.2 Configurations and hazards
**Multirotor** (hover, simple, inefficient), **fixed-wing** (efficient, needs
launch/recovery), **VTOL hybrid** (⚠️ **tiltrotor, tailsitter, or lift+cruise — carrying
the mass of both systems is the trade**), **helicopter**, **lighter-than-air**.
**⚠️ Hazards specific to rotorcraft**: **vortex ring state** (⚠️ **descending into your own
downwash — recovery is to move laterally, not to add power**), **ground effect**, **loss
of GNSS**, **battery thermal runaway**, **prop strikes.**

### 11.3 Regulation — §16.1 for the current picture
**Core concepts**: **VLOS vs BVLOS**, **Remote ID** (⚠️ **broadcast registration and
position — a digital licence plate**), registration, **detect-and-avoid**, **UTM/U-space**,
airspace authorization (LAANC), and weight-class thresholds.
**⚠️ The regulatory dividing line everywhere is BVLOS**, because it removes the human
who was providing collision avoidance.

---
