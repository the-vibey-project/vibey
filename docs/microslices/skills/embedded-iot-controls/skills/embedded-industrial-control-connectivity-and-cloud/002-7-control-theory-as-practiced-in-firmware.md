---
id: skill-7-control-theory-as-practiced-in-firmware-cc2f185320
purpose: 7 control theory as practiced in firmware
source: src/vibey_tools/skills/plugins/embedded-iot-controls/skills/embedded-industrial-control-connectivity-and-cloud/SKILL.md
requires: ["skill-6-industrial-control-and-ot-946a86375a"]
links: ["skill-8-connectivity-3055df089c"]
---

## §7. Control Theory as Practiced in Firmware

### 7.1 PID done correctly

Textbook PID is three lines. Production PID is thirty, and the extra twenty-seven are
where the engineering lives.

```c
typedef struct {
    float kp, ki, kd;
    float dt;              /* FIXED sample period, seconds — see note below */
    float integral;
    float prev_meas;       /* derivative on MEASUREMENT, not error */
    float d_filt;          /* filtered derivative state */
    float tau;             /* derivative low-pass time constant, seconds */
    float out_min, out_max;
    bool  first_run;
} pid_t;

float pid_update(pid_t *p, float setpoint, float meas) {
    float error = setpoint - meas;

    /* ---- Proportional ---- */
    float P = p->kp * error;

    /* ---- Derivative on measurement (kills SETPOINT KICK) ----
       d/dt(error) spikes to infinity on a setpoint step. d/dt(measurement) does not.
       Sign flips because d(sp - meas)/dt = -d(meas)/dt for constant sp.            */
    if (p->first_run) { p->prev_meas = meas; p->d_filt = 0.0f; p->first_run = false; }
    float raw_d = -(meas - p->prev_meas) / p->dt;
    p->prev_meas = meas;

    /* ---- Filter the derivative (MANDATORY on any real sensor) ----
       Unfiltered D amplifies sensor noise by kd/dt. First-order LPF: */
    float alpha = p->dt / (p->tau + p->dt);
    p->d_filt  += alpha * (raw_d - p->d_filt);
    float D = p->kd * p->d_filt;

    /* ---- Integral with CONDITIONAL INTEGRATION anti-windup ----
       Compute the unsaturated output first; only integrate if we are not saturated
       in the direction that would make saturation worse.                          */
    float I_candidate = p->integral + p->ki * error * p->dt;
    float u_unsat     = P + I_candidate + D;

    bool saturating_high = (u_unsat > p->out_max) && (error > 0.0f);
    bool saturating_low  = (u_unsat < p->out_min) && (error < 0.0f);
    if (!saturating_high && !saturating_low) {
        p->integral = I_candidate;             /* only then commit */
    }

    float u = P + p->integral + D;

    /* ---- Saturate ---- */
    if (u > p->out_max) u = p->out_max;
    if (u < p->out_min) u = p->out_min;
    return u;
}

/* Bumpless transfer: when switching manual→auto, back-calculate the integral so the
   output does not jump. */
void pid_set_auto(pid_t *p, float current_output, float setpoint, float meas) {
    p->integral  = current_output - p->kp * (setpoint - meas);
    p->prev_meas = meas;
    p->d_filt    = 0.0f;
    p->first_run = false;
}
```

**The five PID mistakes that cause ~90% of field problems:**
1. **No anti-windup** — integrator charges while the actuator is saturated; the system
   massively overshoots when it comes off the limit. This is the #1 issue.
2. **Derivative on error** — setpoint changes produce a huge output spike ("derivative
   kick").
3. **Unfiltered derivative** — sensor noise × kd/dt drives the actuator into chatter.
4. **Variable `dt`** — computing `dt` from a timestamp each call means gain varies with
   jitter. Run the loop from a **hardware timer interrupt at a fixed rate** and treat `dt`
   as a constant. If you must handle variable dt, the math still works but tuning becomes
   unreliable.
5. **Sample rate too slow** — rule of thumb: sample at **10–20× the closed-loop bandwidth**
   you want. A 1 Hz process needs ≥10 Hz sampling; a current loop at 1 kHz bandwidth needs
   10–20 kHz.

**Tuning methods, ranked by practicality:**
- **Lambda / IMC tuning** — pick a desired closed-loop time constant λ; compute gains from
  a first-order-plus-dead-time (FOPDT) model. Predictable, conservative, the process
  industry default.
- **Relay autotuning (Åström–Hägglund)** — drive the process with a relay, measure the
  resulting limit cycle to find the ultimate gain and period, then apply tuning rules. The
  basis of most "autotune" buttons.
- **Cohen–Coon** — better than Ziegler–Nichols for dead-time-dominant processes.
- **Ziegler–Nichols** — historically important, **aggressively underdamped** (~25%
  overshoot by design). Use as a starting point, then detune. Don't ship Z-N gains.
- **Manual**: increase Kp until sustained oscillation, back off to ~half; add Ki to remove
  steady-state error; add Kd last and only if you have a clean sensor.

**Fixed-point vs float**: on any Cortex-M4F/M7/M33 with an FPU, use `float`. Single-
precision add/mul is 1–3 cycles. On M0/M0+ without an FPU, software float is 50–100+
cycles and Q15/Q31 fixed-point (with CMSIS-DSP) is the right answer — but watch overflow
and be explicit about your scaling.

### 7.2 Beyond PID

- **Cascade control**: inner fast loop (e.g. motor current, 10 kHz) inside an outer slow
  loop (position, 1 kHz) inside an outer-outer (temperature, 1 Hz). Each loop should be
  **5–10× faster** than the one enclosing it. This is how nearly all real motion and
  process control is structured, and it solves problems that no amount of single-loop
  tuning will.
- **Feedforward**: if you know the disturbance or the required steady-state effort, add it
  directly. Feedback then only corrects the error. In motion control, velocity and
  acceleration feedforward reduce following error by an order of magnitude.
- **Dead time / transport delay**: PID degrades badly when dead time approaches the
  process time constant. **Smith predictor** uses a process model to control against a
  delay-free prediction. Fragile to model error; use with care.
- **State-space + observers**: for MIMO or when states aren't directly measurable. A
  **Luenberger observer** estimates unmeasured states; a **Kalman filter** does it
  optimally under Gaussian noise assumptions.
- **Complementary filter**: the poor man's Kalman for IMU fusion, and often the right
  choice on an M0: `angle = a*(angle + gyro*dt) + (1-a)*accel_angle`. Two lines, no matrix
  math, and it captures the essential idea (trust the gyro short-term, the accelerometer
  long-term).
- **MPC at the edge**: real on Cortex-M7/M33-class hardware for small problems (embedded
  QP solvers like OSQP/qpOASES). Worth it when constraints matter (thermal limits,
  actuator limits) and a model exists.

### 7.3 Motor control

**Commutation methods** in order of complexity:
1. **Six-step / trapezoidal** (BLDC): switch phases based on Hall sensors. Simple, torque
   ripple at commutation, adequate for fans/pumps.
2. **Sinusoidal**: smoother, still no current regulation in the rotating frame.
3. **FOC (Field-Oriented Control)**: the standard for anything requiring precision.

**FOC in one paragraph**: measure two phase currents → **Clarke transform** (3-phase abc →
2-axis stationary αβ) → **Park transform** (αβ → rotating dq frame, using rotor angle) →
now torque-producing current `iq` and flux-producing current `id` are **DC quantities**,
so two simple PI loops regulate them → **inverse Park** → **Space Vector Modulation**
(SVPWM, ~15% better DC bus utilization than sinusoidal PWM) → three PWM duty cycles.

**Timing is everything**: the current loop runs at the PWM frequency (typically 10–20 kHz)
and must complete within one PWM period. ADC sampling must be synchronized to the PWM —
sample at the **centre of the PWM period** (when the low-side FETs are on and the current
is at its average), triggered by the timer, not by software.

**Rotor angle sources**: Hall sensors (60° resolution, cheap), incremental encoder
(needs indexing), absolute encoder/resolver (expensive, no homing), or **sensorless**
(back-EMF observer or high-frequency injection) — sensorless is free in BOM and expensive
in engineering, and has a low-speed blind spot.

> **⚠️ GOTCHA — dead time and its compensation.** Hardware dead time prevents
> shoot-through, but it distorts the output voltage (the actual volt-seconds don't match
> the commanded duty), producing torque ripple and current distortion at low speed. Dead-
> time compensation (adding a sign-of-current-dependent correction to the duty) is standard
> practice in production FOC and absent from most tutorials.

---
