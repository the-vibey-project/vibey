---
id: skill-12-gnc-software-69c4c07d58
purpose: 12 gnc software
source: src/vibey_tools/skills/plugins/flight-software/skills/flightsw-gnc-verification-ground-and-autonomy/SKILL.md
requires: []
links: ["skill-13-verification-and-validation-d6a52a674f"]
---

## §12. GNC Software

**[DURABLE] The mathematics is in a rocket-science reference §11; this is the software
practice.**

**The loop**: sensors (IMU, star tracker, GPS) → **estimation** (⚠️ **Kalman filter
variants — EKF, UKF; and numerical conditioning matters: use square-root or UD
factorization forms, because covariance matrices lose positive-definiteness in single
precision**) → guidance → control law → actuators.

**⚠️ Model-based development is the norm here and it changes the workflow**: algorithms are
developed in Simulink or equivalent, then **autocoded to C** (DO-331 covers this for
certification). **The benefit is that the model is the specification and it is executable;
the risk is that the generated code's WCET and stack behaviour must still be analysed** —
autocoding does not exempt you from §6 → `flightsw-processors-radiation-and-real-time`.

**⚠️ Numerical hazards specific to flight:**
- **Single vs double precision** — ⚠️ **a real trade on constrained hardware, and the wrong
  choice destroyed Ariane 501** (§16.2).
- **Angle wrapping** at ±180°, and **quaternion sign ambiguity** (⚠️ **q and −q are the same
  rotation; a naive interpolation or comparison takes the long way round**).
- **⚠️ Gimbal lock in Euler angles** — use quaternions internally, convert only for display.
- **Filter divergence** — ⚠️ **an over-confident covariance stops believing measurements.**
  Bound it.
- **Integrator windup** in controllers with saturating actuators — clamp.
- **Units. Always units.** §16.3.

---
