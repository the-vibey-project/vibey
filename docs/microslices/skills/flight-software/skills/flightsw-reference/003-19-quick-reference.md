---
id: skill-19-quick-reference-399a294531
purpose: 19 quick reference
source: src/vibey_tools/skills/plugins/flight-software/skills/flightsw-reference/SKILL.md
requires: ["skill-18-books-and-standards-a3163010e8"]
links: ["skill-20-method-bd9500d451"]
---

## §19. Quick Reference

### 19.1 The rules that map to dead vehicles
```
Bound every loop statically                     §3.3 / runaway
No dynamic allocation after init                §3.3 / fragmentation, exhaustion
Enable priority inheritance                     §16.1 / Mars Pathfinder
Re-validate inherited code for the new envelope §16.2 / Ariane 501
Specify units at every interface                §16.3 / Mars Climate Orbiter
Plausibility-check sensors against state        §16.4 / Mars Polar Lander
Don't remove hardware interlocks                §16.5 / Therac-25
Test the integrated end-to-end sequence         §16.6 / Starliner OFT-1
Immutable or dual-redundant bootloader          §11 / unrecoverable bricking
Scrub memory faster than double-error accrual   §5.1 / uncorrectable SEU
Widely-separated enum bit patterns              §5.3 / single-flip state change
Compute your counter rollover interval          §9 / 32-bit ms wraps at 49.7 days
```

### 19.2 Picker
| Need | Choice |
|---|---|
| Framework, mature + heritage + CCB | **cFS** (§2.2 → `flightsw-architecture-languages-and-standards`) |
| Framework, small team, instrument scale | **F Prime** (§2.2 → `flightsw-architecture-languages-and-standards`) |
| Language, default | **C** + MISRA + Power of 10 (§3 → `flightsw-architecture-languages-and-standards`) |
| Language, provable absence of runtime errors | **SPARK/Ada** (§3.1 → `flightsw-architecture-languages-and-standards`) |
| Language, new memory-safe work | ⚠️ **Rust, non-critical path first** (§3.2 → `flightsw-architecture-languages-and-standards`) |
| RTOS, certification evidence | **VxWorks**, LynxOS-178, PikeOS (§7 → `flightsw-processors-radiation-and-real-time`) |
| RTOS, no licence cost, heritage | **RTEMS** (§7 → `flightsw-processors-radiation-and-real-time`) |
| RTOS, cubesat | **FreeRTOS** or Zephyr (§7 → `flightsw-processors-radiation-and-real-time`) |
| Deterministic launch-vehicle sequencing | **Cyclic executive** (§6 → `flightsw-processors-radiation-and-real-time`) |
| Mixed criticality | ARINC 653 partitioning or hypervisor (§7 → `flightsw-processors-radiation-and-real-time`) |
| Memory protection | **SECDED + background scrubber** (§5.1 → `flightsw-processors-radiation-and-real-time`) |
| File transfer over a bad link | **CFDP** (§11 → `flightsw-fdir-time-telemetry-and-updates`) |
| Command/telemetry | **CCSDS**, + **SDLS** for authentication (§10 → `flightsw-fdir-time-telemetry-and-updates`) |
| Concurrency verification | **SPIN** model checking (§13 → `flightsw-gnc-verification-ground-and-autonomy`) |
| Ground visualization | **OpenMCT**, OpenC3, Yamcs (§14 → `flightsw-gnc-verification-ground-and-autonomy`) |

### 19.3 Review checklist
- [ ] Every loop statically bounded? (§3.3 → `flightsw-architecture-languages-and-standards`)
- [ ] Zero dynamic allocation after init? (§3.3 → `flightsw-architecture-languages-and-standards`)
- [ ] Stack depth analysed with margin? (§6 → `flightsw-processors-radiation-and-real-time`)
- [ ] WCET bounded for every hard-real-time path? (§6 → `flightsw-processors-radiation-and-real-time`)
- [ ] Priority inheritance on every shared mutex? (§16.1 → `flightsw-gnc-verification-ground-and-autonomy`)
- [ ] All interfaces unit-specified? (§16.3 → `flightsw-gnc-verification-ground-and-autonomy`)
- [ ] Sensor inputs plausibility-checked against state? (§16.4 → `flightsw-gnc-verification-ground-and-autonomy`)
- [ ] Enum values widely separated in bit pattern? (§5.3 → `flightsw-processors-radiation-and-real-time`)
- [ ] Critical structures checksummed and periodically verified? (§5.3 → `flightsw-processors-radiation-and-real-time`)
- [ ] Every counter's rollover interval computed and handled? (§9 → `flightsw-fdir-time-telemetry-and-updates`)
- [ ] Safe mode survivable indefinitely, Earth/Sun-pointed? (§8 → `flightsw-fdir-time-telemetry-and-updates`)
- [ ] Command loss timer implemented and tested? (§8 → `flightsw-fdir-time-telemetry-and-updates`)
- [ ] Fault responses inhibited during critical sequences? (§8 → `flightsw-fdir-time-telemetry-and-updates`)
- [ ] Diagnostics persisted *before* recovery action? (§8 → `flightsw-fdir-time-telemetry-and-updates`)
- [ ] Bootloader immutable or dual-redundant? (§11 → `flightsw-fdir-time-telemetry-and-updates`)
- [ ] Update path has automatic rollback? (§11 → `flightsw-fdir-time-telemetry-and-updates`)
- [ ] Hazardous commands two-stage arm/fire? (§10 → `flightsw-fdir-time-telemetry-and-updates`)
- [ ] Out-of-range parameters rejected, not clamped? (§10 → `flightsw-fdir-time-telemetry-and-updates`)
- [ ] Telemetry sufficient to diagnose an unanticipated fault? (§10 → `flightsw-fdir-time-telemetry-and-updates`)
- [ ] Static analysis clean, multiple tools, zero warnings? (§3.3 → `flightsw-architecture-languages-and-standards`)
- [ ] Fault injection campaign run? (§13 → `flightsw-gnc-verification-ground-and-autonomy`)
- [ ] Testbed configuration under control and matching flight? (§13.3 → `flightsw-gnc-verification-ground-and-autonomy`)

---
