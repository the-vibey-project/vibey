---
id: skill-16-case-studies-the-failures-everyone-should-know-7c9cd4dea9
purpose: 16 case studies the failures everyone should know
source: src/vibey_tools/skills/plugins/embedded-iot-controls/skills/embedded-reference/SKILL.md
requires: ["skill-15-the-canon-who-and-what-to-cite-fbb941ba4e"]
links: ["skill-17-currency-snapshot-verified-august-2026-7b577945d8"]
---

## §16. Case Studies — the failures everyone should know

| Case | What happened | The transferable lesson |
|---|---|---|
| **Therac-25** (1985–87) | Radiation therapy machine gave massive overdoses; a race condition between the UI task and the setup task, plus a one-byte counter overflow, reachable only when an operator typed quickly. Hardware interlocks had been *removed* in favour of software. | Removing hardware protection because "software will handle it" is the original sin. Also: concurrency bugs are reachable by timing you didn't imagine, and a vendor who dismisses reports as impossible is a systemic failure. |
| **Ariane 5 Flight 501** (1996) | Reused Ariane 4 inertial reference software; a 64-bit float horizontal-velocity value converted to a 16-bit signed int overflowed on a trajectory it was never designed for. The exception handler shut the unit down; the redundant unit ran identical code and failed identically. | **Reuse without re-validating the operating envelope is not reuse.** Identical redundancy protects against random faults, not systematic ones. |
| **Mars Pathfinder** (1997) | Repeated system resets on Mars. A low-priority meteorological task held a mutex on the information bus; a high-priority bus-management task blocked on it; a medium-priority comms task preempted the low-priority one. Classic **priority inversion**; the watchdog reset the system. | Fixed remotely by enabling **priority inheritance** on that mutex. The reason every RTOS mutex now offers PI, and the reason you should ship a debug/trace capability you can enable in the field. |
| **Toyota unintended acceleration** (analysed 2013) | Koopman's expert analysis found ~10,000 global variables, deeply nested logic, stack overflow risk, a single-point-of-failure task, inadequate watchdog design, and recursion — in software controlling throttle. | The watchdog architecture matters as much as the code (§5.9 → `embedded-languages-realtime-and-patterns`). Complexity metrics and global-state count are safety-relevant. Firmware quality is legally discoverable. |
| **Boeing 737 MAX / MCAS** (2018–19) | A flight-control function authorized to command large nose-down trim, driven by a **single** angle-of-attack sensor, with a disagreement alert sold as an option, and inadequate pilot documentation. | Single-sensor authority over a safety-critical actuator is a requirements/architecture failure, not a coding failure. Certification did not catch it. |
| **Stuxnet** (2010) | Targeted Siemens S7 PLCs, altered centrifuge speeds while replaying recorded normal values to the HMI. | Air gaps are a myth; OT is a target; **the HMI can lie**. Drove the creation of the modern ICS security discipline and much of IEC 62443's urgency. |
| **Mirai** (2016) | Botnet built by scanning for IoT devices with **default telnet credentials**; used to launch record DDoS. | Why every regulation since (ETSI 303 645, PSTI, EN 18031, CRA) bans universal default passwords. The simplest possible attack, at enormous scale. |
| **Jeep Cherokee remote hack** (Miller/Valasek, 2015) | Remote compromise via the cellular-connected head unit, then pivot onto the CAN bus to control steering and brakes. 1.4 M vehicle recall. | **Flat internal networks turn one compromised component into total compromise.** The direct ancestor of automotive gateway/domain-controller architectures and UNECE R155. |
| **Ukraine grid attacks** (2015, 2016 Industroyer) | Coordinated intrusion opened breakers; 2016's Industroyer/CrashOverride spoke IEC 60870-5-101/104, IEC 61850, and OPC DA natively. | Attackers learn your protocols. Protocol-aware malware is the norm, not the exception. |
| **Triton / Trisis** (2017) | Malware targeting Triconex **Safety Instrumented Systems** — an attempt to disable the last line of defence against a physical catastrophe. | The safety system is itself a target. Safety and security cannot be separate programmes. |
| **Ripple20 / URGENT-11** (2019–20) | Vulnerabilities in the Treck and VxWorks TCP/IP stacks propagated into hundreds of millions of devices across every industry — most vendors could not tell whether they were affected. | The birth of the SBOM mandate. **You cannot patch what you cannot inventory.** |
| **Colonial Pipeline** (2021) | Ransomware hit IT/billing; operations were shut down precautionarily because the OT/IT boundary couldn't be trusted. | Business continuity, not just technical compromise. The Purdue boundary must be *designed and testable*, not assumed. |
| **Log4Shell** (2021) | A logging library vulnerability with unbounded blast radius across the software supply chain. | Accelerated SBOM/VEX adoption and directly informs the CRA's supply-chain provisions. |

---
