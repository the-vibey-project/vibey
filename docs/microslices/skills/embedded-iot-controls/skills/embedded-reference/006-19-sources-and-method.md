---
id: skill-19-sources-and-method-7160b9248c
purpose: 19 sources and method
source: src/vibey_tools/skills/plugins/embedded-iot-controls/skills/embedded-reference/SKILL.md
requires: ["skill-18-quick-reference-cards-65d850090c"]
links: []
---

## §19. Sources and Method

**Method note.** This document was assembled as a narrative (not systematic) review.
Durable engineering content (§1 → `embedded-silicon-and-firmware-models`, §4 → `embedded-languages-realtime-and-patterns`, §5 → `embedded-languages-realtime-and-patterns`, §7 → `embedded-industrial-control-connectivity-and-cloud`, §11 → `embedded-security-safety-and-testing`, §16) is synthesized from established
practice and the canonical literature in §15. Every **time-sensitive** claim — versions,
dates, regulatory deadlines, product status — was verified against a primary or
near-primary source in **August 2026** and is flagged in §17 with a decay-risk rating.
Where practitioners disagree, §14 presents both cases rather than adjudicating, and
disputed claims (notably OPC UA PubSub adoption and Azure IoT Central's status) are
marked as disputed in place.

**Search log** (queries run, August 2026): Zephyr LTS status · embedded-hal 1.0 / Embassy /
RTIC ecosystem · EU CRA deadlines · Matter specification releases · Bluetooth Core
versions · Azure IoT Central/Hub/Operations status · MISRA C:2025 and C++:2023 · EN 18031
and the RED delegated act · Unified Namespace / Sparkplug B / OPC UA · TinyML runtimes and
Ethos-U · FreeRTOS LTS and kernel versions · ESP-IDF v6.0 and RISC-V ESP32 parts ·
MCUboot/SUIT/post-quantum firmware signing · PREEMPT_RT mainlining and Yocto releases ·
Ferrocene safety qualification · IEC 62443 parts and current practice · cellular IoT
(NB-IoT/LTE-M/RedCap) status · single-pair Ethernet and Ethernet-APL · AWS IoT
Core/Greengrass status.

**Primary sources consulted (selected):**
- Zephyr Project release documentation and release-management wiki — docs.zephyrproject.org
- FreeRTOS 202604 LTS announcement (AWS) and FreeRTOS-Kernel release notes — freertos.org, github.com/FreeRTOS
- European Commission, Cyber Resilience Act and CRA reporting obligations — digital-strategy.ec.europa.eu
- CEN-CENELEC and Commission Implementing Decision (EU) 2025/138 on EN 18031 harmonisation
- MISRA Consortium — misra.org.uk (MISRA C and MISRA C++ pages)
- Bluetooth SIG — bluetooth.com (Core 6.0/6.2 feature overviews and release blogs)
- Connectivity Standards Alliance — csa-iot.org (Matter 1.5, 1.5.1 releases)
- Microsoft Learn / Azure IoT Operations documentation and release notes; Microsoft Tech Community
- AWS IoT Greengrass documentation (V1 end-of-support notice)
- Espressif — ESP-IDF v6.0 announcement and Programming Guide
- Yocto Project release notes 6.0 (Wrynose)
- Ferrous Systems — Ferrocene qualification announcements and release notes
- Arm Developer — Cortex-M and Ethos-U edge AI documentation
- NIST SP 800-208; NSA CNSA 2.0 advisory; IETF RFCs 9019, 9124, 8554, 8391
- Linux Foundation realtime wiki; Linux 6.12 release coverage
- Embassy and rust-embedded working group documentation

**Confidence statement.** High confidence in §1–§8 → `embedded-silicon-and-firmware-models`, `embedded-industrial-control-connectivity-and-cloud`, §11–§13 → `embedded-security-safety-and-testing`, §15–§16 and §18 (durable
engineering and well-documented history). High confidence in §17's verified items as of
the stated date. Moderate confidence in market-adoption characterizations (§6.4 → `embedded-industrial-control-connectivity-and-cloud`, §8.1 → `embedded-industrial-control-connectivity-and-cloud`,
§8.3 → `embedded-industrial-control-connectivity-and-cloud`) — these rest partly on vendor and practitioner commentary, where incentives differ;
they are stated as tendencies, not measurements.
