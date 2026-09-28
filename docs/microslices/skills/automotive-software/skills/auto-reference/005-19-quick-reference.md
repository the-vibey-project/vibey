---
id: skill-19-quick-reference-a6fd17f4a8
purpose: 19 quick reference
source: src/vibey_tools/skills/plugins/automotive-software/skills/auto-reference/SKILL.md
requires: ["skill-18-books-and-resources-090f94313f"]
links: ["skill-20-method-3e9d0a9702"]
---

## §19. Quick Reference

### 19.1 Picker
| Need | Use |
|---|---|
| Cheap sensor/actuator link | **LIN** (§3 → `auto-architecture-buses-and-autosar`) |
| Robust real-time control bus | **CAN / CAN FD** (§3.1 → `auto-architecture-buses-and-autosar`) |
| High bandwidth backbone | **Automotive Ethernet + TSN** (§3.2 → `auto-architecture-buses-and-autosar`) |
| Deterministic legacy x-by-wire | FlexRay (⚠️ legacy — use Ethernet+TSN now) (§3 → `auto-architecture-buses-and-autosar`) |
| Deeply embedded ASIL-D control | ⚠️ **AUTOSAR Classic on an MCU** (§4.1 → `auto-architecture-buses-and-autosar`) |
| Updatable high-compute function | ⚠️ **AUTOSAR Adaptive on POSIX** (§4.2 → `auto-architecture-buses-and-autosar`) |
| Service discovery in-vehicle | **SOME/IP** or DDS (§3.2 → `auto-architecture-buses-and-autosar`) |
| Mixed criticality on one SoC | ⚠️ **Hypervisor partitioning, or a separate safety MCU** (§2.2 → `auto-architecture-buses-and-autosar`) |
| Detect corrupted/lost/replayed safety data | ⚠️ **E2E protection (CRC + counter + data ID)** (§6.4 → `auto-real-time-safety-and-cybersecurity`) |
| Authenticate in-vehicle messages | **SecOC** (§7.3 → `auto-real-time-safety-and-cybersecurity`) |
| Diagnostic access | **UDS over ISO-TP (CAN) or DoIP (Ethernet)** (§8 → `auto-diagnostics-ota-and-adas`) |
| Flash an ECU | **UDS 0x34/36/37 + signature verify + A/B banks** (§9 → `auto-diagnostics-ota-and-adas`) |
| Test an ECU in isolation | ⚠️ **HIL with restbus simulation** (§12 → `auto-process-testing-domains-and-supply-chain`) |
| Validate a safety mechanism | **Fault injection** (§12 → `auto-process-testing-domains-and-supply-chain`) |
| Argue safety for an ML component | ⚠️ **Verifiable safety monitor around it** (§10.3 → `auto-diagnostics-ota-and-adas`) |

### 19.2 Design review checklist
- [ ] HARA done, ASIL assigned per safety goal, before architecture froze? (§6.1 → `auto-real-time-safety-and-cybersecurity`)
- [ ] Any ASIL decomposition backed by dependent-failure analysis? (§6.2 → `auto-real-time-safety-and-cybersecurity`)
- [ ] Safe state defined — and is it actually safe in every operating condition? (§6.4 → `auto-real-time-safety-and-cybersecurity`)
- [ ] E2E protection on every safety-relevant signal path? (§6.4 → `auto-real-time-safety-and-cybersecurity`)
- [ ] Program flow monitoring, not just an alive watchdog? (§6.4 → `auto-real-time-safety-and-cybersecurity`)
- [ ] WCET bounded and schedulability analysed, including CAN response times? (§5 → `auto-real-time-safety-and-cybersecurity`)
- [ ] Bus load within budget, termination correct? (§3.1 → `auto-architecture-buses-and-autosar`)
- [ ] TARA done; CSMS/SUMS evidence produced for the customer? (§7 → `auto-real-time-safety-and-cybersecurity`)
- [ ] Network segmented between external-facing and control domains? (§7.3 → `auto-real-time-safety-and-cybersecurity`)
- [ ] Bootloader immutable or A/B, signature-verified, power-loss safe? (§9 → `auto-diagnostics-ota-and-adas`)
- [ ] Per-vehicle software provenance recorded for R156? (§7.2 → `auto-real-time-safety-and-cybersecurity`, §9 → `auto-diagnostics-ota-and-adas`)
- [ ] Autocoded code checked for WCET, stack and MISRA? (§11 → `auto-process-testing-domains-and-supply-chain`)
- [ ] MISRA deviations documented and justified? (§11 → `auto-process-testing-domains-and-supply-chain`)
- [ ] Quiescent current budget allocated and measured? (§2.3 → `auto-architecture-buses-and-autosar`)
- [ ] ODD stated explicitly, and behaviour outside it defined? (§10.1 → `auto-diagnostics-ota-and-adas`)

---
