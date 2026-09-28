---
id: skill-15-anti-patterns-d78f54fd1d
purpose: 15 anti patterns
source: src/vibey_tools/skills/plugins/automotive-software/skills/auto-reference/SKILL.md
requires: []
links: ["skill-16-numbers-58df2dbc77"]
---

## §15. Anti-Patterns

| Anti-pattern | Why |
|---|---|
| Treating ASIL as a label applied late | ⚠️ **It determines architecture. HARA comes first** (§6.1 → `auto-real-time-safety-and-cybersecurity`) |
| ASIL decomposition without dependent-failure analysis | ⚠️ **Shared clock/power/bus invalidates it** (§6.2 → `auto-real-time-safety-and-cybersecurity`) |
| "Safe state = shut down" | ⚠️ **Losing steering assist at speed is itself a hazard** (§6.4 → `auto-real-time-safety-and-cybersecurity`) |
| Watchdog that only checks aliveness | ⚠️ **Alive-but-wrong is the failure it misses. Use program flow monitoring** (§6.4 → `auto-real-time-safety-and-cybersecurity`) |
| Trusting UDS 0x27 security access | ⚠️ **Fixed algorithm, extractable from tester software** (§8 → `auto-diagnostics-ota-and-adas`) |
| Putting a fresh ECU on the powertrain bus unsegmented | CAN has no authentication (§3.1 → `auto-architecture-buses-and-autosar`, §7.3 → `auto-real-time-safety-and-cybersecurity`) |
| Skipping E2E protection on safety-relevant messages | ⚠️ **Corruption, repetition, loss and masquerade all go undetected** (§6.4 → `auto-real-time-safety-and-cybersecurity`) |
| Assuming Adaptive AUTOSAR replaces Classic | ⚠️ **They coexist by design** (§4.2 → `auto-architecture-buses-and-autosar`) |
| Zonal architecture as a pure hardware cost play | ⚠️ **Complexity moves to software governance** (§2.1 → `auto-architecture-buses-and-autosar`) |
| Ethernet for control traffic without TSN | No bounded latency (§3.2 → `auto-architecture-buses-and-autosar`) |
| Wrong CAN termination | ⚠️ **Two 120 Ω, at the ends. Classic intermittent fault** (§3.1 → `auto-architecture-buses-and-autosar`) |
| Bus load above ~50% | No latency headroom (§3.1 → `auto-architecture-buses-and-autosar`) |
| Autocoded model assumed exempt from WCET/MISRA checks | ⚠️ **It isn't** (§11 → `auto-process-testing-domains-and-supply-chain`) |
| Undocumented MISRA deviations | Documented is fine; silent is a finding (§11 → `auto-process-testing-domains-and-supply-chain`) |
| Mutable bootloader, single bank | ⚠️ **An unrecoverable brick** (§9 → `auto-diagnostics-ota-and-adas`) |
| OTA without power-loss safety at every step | The customer will unplug it (§9 → `auto-diagnostics-ota-and-adas`) |
| OTA without per-vehicle software provenance records | ⚠️ **R156 requires it** (§7.2 → `auto-real-time-safety-and-cybersecurity`, §9 → `auto-diagnostics-ota-and-adas`) |
| Marketing an L2 system in L3+ language | ⚠️ **A liability and regulatory problem, not a wording one** (§10.1 → `auto-diagnostics-ota-and-adas`) |
| Driver monitoring by steering torque alone | Trivially defeated (§10.3 → `auto-diagnostics-ota-and-adas`) |
| Claiming validation by disengagement rate | ⚠️ **Gameable and not comparable** (§10.4 → `auto-diagnostics-ota-and-adas`) |
| Claiming autonomy is validated at all | ⚠️ **No accepted sufficient methodology exists** (§10.4 → `auto-diagnostics-ota-and-adas`) |
| Ignoring quiescent current in sleep design | Flat battery in the airport car park (§2.3 → `auto-architecture-buses-and-autosar`) |
| Variant handling by preprocessor sprawl | Unmaintainable combinatorics (§13 → `auto-process-testing-domains-and-supply-chain`) |
| Treating security as a feature rather than type approval | ⚠️ **No CSMS certificate, no sale** (§7.2 → `auto-real-time-safety-and-cybersecurity`) |

---
