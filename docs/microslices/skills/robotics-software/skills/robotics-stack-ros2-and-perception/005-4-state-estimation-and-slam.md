---
id: skill-4-state-estimation-and-slam-f6210a3079
purpose: 4 state estimation and slam
source: src/vibey_tools/skills/plugins/robotics-software/skills/robotics-stack-ros2-and-perception/SKILL.md
requires: ["skill-3-perception-0ad064825f"]
links: []
---

## §4. State Estimation and SLAM

**[DURABLE] The core insight of the whole field: you never know where you are; you have a
probability distribution over where you might be.** Engineering that distribution well
*is* state estimation.

**The filter family**: **Kalman filter** (optimal for linear-Gaussian), **EKF**
(linearize; ⚠️ **diverges when the linearization is poor**), **UKF** (sigma points,
better for strong nonlinearity), **particle filter** (arbitrary distributions,
⚠️ **suffers particle depletion**; the basis of AMCL), and **factor graphs / pose graph
optimization** — ⚠️ **which is what modern SLAM actually uses**, via GTSAM, g2o, or Ceres.

**[DURABLE] The move from filtering to smoothing (factor graphs) is one of the genuine
methodological advances of the last two decades**: keeping and re-optimizing a window of
history beats propagating a single mean and covariance forward.

**SLAM in practice**: **visual** (ORB-SLAM3, and the classic), **visual-inertial**
(VINS-Fusion, OKVIS — ⚠️ **IMU + camera is strongly complementary: the IMU covers fast
motion and the camera bounds drift**), **LiDAR** (LOAM family, FAST-LIO2, KISS-ICP),
**LIO** (LiDAR-inertial), and increasingly **learned front-ends with classical back-ends**.

**⚠️ The problems that actually bite**: **loop closure** (recognizing you've been here
before — and ⚠️ **a false positive corrupts the whole map**), **the kidnapped robot
problem**, **long-term map maintenance in changing environments** (⚠️ **the underrated
one: your warehouse map is wrong the moment someone moves a pallet**), **degenerate
geometry** (a long featureless corridor is unobservable along its axis), and
**scale drift** in monocular systems.
