---
id: skill-17-currency-snapshot-verified-august-2026-7b577945d8
purpose: 17 currency snapshot verified august 2026
source: src/vibey_tools/skills/plugins/embedded-iot-controls/skills/embedded-reference/SKILL.md
requires: ["skill-16-case-studies-the-failures-everyone-should-know-7c9cd4dea9"]
links: ["skill-18-quick-reference-cards-65d850090c"]
---

## §17. Currency Snapshot — verified August 2026

Everything in this section decays. Re-verify against the primary source before relying on
a date or version number.

| Thing | Status as of Aug 2026 | Decay risk |
|---|---|---|
| **Zephyr** | 4.4 (Apr 2026) stable; **v3.7 is current LTS**; v4.5 due Oct 2026; **v4.6 planned LTS Apr 2027**; 6-month Apr/Oct cadence | High — releases every 6 months |
| **FreeRTOS** | **202604 LTS**, kernel **v11.3.0**; coreMQTT **v5.0.2 adds MQTT v5**; SMP in mainline since v11.0; EMP offers up to 10 extra years of patches | Medium |
| **Linux / PREEMPT_RT** | PREEMPT_RT **mainlined in 6.12** (Sept 2024, x86/arm64/RISC-V); 6.18 is the current LTS; 7.0 released May 2026 | Medium |
| **Yocto** | **6.0 "Wrynose" LTS** (May 2026), Linux 6.18, GCC 15.2, glibc 2.43, supported to **Apr 2030**; explicit SBOM/CVE work for CRA. 5.3 Whinlatter EOL June 2026 | Low (LTS) |
| **ESP-IDF** | **v6.0** (Mar 2026): full support for ESP32-C5/C61, preview H21/H4; picolibc; PSA Crypto replacing legacy mbedTLS APIs; **recovery bootloader on C5/C61**; warnings-as-errors default; legacy ADC/DAC/I2S drivers removed. v6.1 in beta | High |
| **Rust embedded** | **embedded-hal 1.0 stable**; Embassy is the de facto async runtime, compiles on stable since Rust 1.75; probe-rs has largely displaced OpenOCD in Rust workflows; esp-rs is Espressif-official | Medium |
| **Ferrocene** | TÜV SÜD-qualified: ISO 26262 **ASIL D**, IEC 61508 **SIL 3** (supporting SIL 4), IEC 62304 **Class C**; **certified `core` subset at SIL 2 / ASIL B** (25.11.0, extended in 26.02.0); targets incl. Armv7E-M, Armv8-A, QNX | Medium |
| **MISRA** | **MISRA C:2025** (Mar 2025) current, ~225 guidelines, C90–C18; **MISRA C++:2023** current (C++17, ~179 rules, absorbed AUTOSAR C++14); new MISRA C++ in development, no date | Low |
| **EU CRA** | ⚠️ **Reporting obligations start 11 Sept 2026** (24 h / 72 h / 14 d); full application **11 Dec 2027**; Commission guidance published 27 Jul 2026 | **Imminent** |
| **EU RED cyber** | Mandatory since **1 Aug 2025**; EN 18031-1/2/3 harmonised **with restrictions** (Decision 2025/138) — restricted clauses still need a Notified Body | Low |
| **Bluetooth** | Core **6.3** (May 2026); 6.2 (Nov 2025) cut min connection interval to **375 µs**; 6.0 introduced Channel Sounding; twice-yearly cadence | Medium |
| **Matter** | 1.5 (Nov 2025) added cameras/closures/soil sensors; 1.5.1 (Mar 2026) camera refinements; **1.6 reported as current** mid-2026 | High |
| **Cellular IoT** | 2G/3G sunset in most markets; **AT&T shut down NB-IoT**; LTE-M leads roaming; Cat-1/Cat-1bis is the safe global default; RedCap live with **~30 operators in 21 countries** (early 2026), broader 2027–28; **SGP.32 eSIM** accelerating | Medium |
| **Edge AI** | LiteRT-for-Microcontrollers still the most-used MCU runtime; ExecuTorch growing (best with NPUs); **Ethos-U85** adds transformer support + TOSA; ONNX + INT8 the de facto interchange | Medium |
| **Azure IoT** | IoT Hub + **IoT Operations** (Arc/K8s edge, MQTT broker, OPC UA connectors, 72 h offline); releases 2510, 2603 GA'd persistence, X.509 via Device Registry, no-code dataflow graphs. IoT Central retirement notice was **retracted as erroneous** — verify current status | High |
| **AWS IoT** | IoT Core + Greengrass **v2**; ⚠️ **Greengrass V1 end of support 7 Oct 2026** | Medium |
| **Google Cloud IoT Core** | **Retired 16 Aug 2023.** No managed replacement on GCP | Settled |
| **Single-pair Ethernet** | IEEE 802.3cg: 10BASE-T1L (1000 m, 10 Mbps) and 10BASE-T1S (multidrop, ~25 m); **Ethernet-APL** builds on T1L for intrinsically-safe process (trunk-and-spur, ~1000 m, ~50 devices, ~500 mW/spur); 10BASE-T1M and 100BASE-T1L in progress | Medium |

**What goes stale fastest**, in order: cloud platform service names and retirement dates;
Matter/Bluetooth spec versions; vendor SDK major versions; regulatory deadlines. **What
essentially never goes stale**: §1 → `embedded-silicon-and-firmware-models` (silicon fundamentals), §4 → `embedded-languages-realtime-and-patterns` (concurrency), §5 → `embedded-languages-realtime-and-patterns` (patterns),
§7 → `embedded-industrial-control-connectivity-and-cloud` (control theory), §16 (case studies).

---
