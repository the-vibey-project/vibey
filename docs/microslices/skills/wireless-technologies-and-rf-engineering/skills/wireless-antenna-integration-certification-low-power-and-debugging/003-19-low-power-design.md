---
id: skill-19-low-power-design-694d5e4610
purpose: 19 low power design
source: src/vibey_tools/skills/plugins/wireless-technologies-and-rf-engineering/skills/wireless-antenna-integration-certification-low-power-and-debugging/SKILL.md
requires: ["skill-18-certification-9db14488b0"]
links: ["skill-20-provisioning-and-onboarding-989600fcb7"]
---

## §19. Low-Power Design

**⚠️ The arithmetic that decides battery life**: ⚠️ **average current = (active current ×
active time + sleep current × sleep time) ÷ total time.**
> **⚠️ GOTCHA — SLEEP CURRENT USUALLY DOMINATES, and people optimize the wrong term.**
> ⚠️ **A device transmitting for 10 ms once a minute spends 99.98% of its life asleep, so a
> few microamps of leakage matters more than transmit efficiency.** **⚠️ Measure sleep
> current on the real board — a stray pull-up or a floating input can cost more than the
> radio.**

**⚠️ The protocol levers**: ⚠️ **BLE connection interval and slave latency; Wi-Fi TWT;
LoRaWAN class A; cellular PSM and eDRX** — ⚠️ **all of them trade responsiveness for
current.**
**⚠️ Battery reality**: ⚠️ **self-discharge, capacity falling with temperature, and PEAK
CURRENT capability — a coin cell can have plenty of capacity and still collapse under a
transmit pulse, which is why bulk capacitance next to the radio is standard.**
**⚠️ Measurement**: ⚠️ **a current profiler with microsecond resolution, because
averaging multimeters cannot see the pulses that matter.**

---
