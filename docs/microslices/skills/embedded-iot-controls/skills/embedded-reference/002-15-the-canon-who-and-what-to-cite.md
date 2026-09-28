---
id: skill-15-the-canon-who-and-what-to-cite-fbb941ba4e
purpose: 15 the canon who and what to cite
source: src/vibey_tools/skills/plugins/embedded-iot-controls/skills/embedded-reference/SKILL.md
requires: ["skill-14-contested-questions-present-both-cases-don-t-adjudicate-2e1e69a4c2"]
links: ["skill-16-case-studies-the-failures-everyone-should-know-7c9cd4dea9"]
---

## §15. The Canon — who and what to cite

### 15.1 Books that practitioners actually reference

| Author | Work | Why it matters |
|---|---|---|
| **Michael Barr** | *Programming Embedded Systems in C and C++*; **Barr Group Embedded C Coding Standard** | The coding standard is a genuinely usable, rule-by-rule document designed to prevent specific bugs |
| **Jack Ganssle** | *The Art of Designing Embedded Systems*; *The Embedded Muse* newsletter | Decades of hard-won engineering-management and firmware-quality wisdom; the standards/discipline advocate |
| **Miro Samek** | *Practical UML Statecharts in C/C++* (QP framework) | The definitive treatment of hierarchical state machines and the active-object model in firmware |
| **Elecia White** | *Making Embedded Systems* (2nd ed.) | The best modern on-ramp; strong on architecture and the engineer's mindset |
| **Joseph Yiu** | *The Definitive Guide to Arm Cortex-M0/M3/M4/M23/M33* | The authoritative Cortex-M architecture reference outside Arm's own TRMs |
| **Philip Koopman** | *Better Embedded System Software*; *Understanding Checksums and CRCs*; the Toyota UA analysis | The safety/reliability authority; his CRC selection work and his expert testimony on Toyota are both foundational |
| **James Grenning** | *Test-Driven Development for Embedded C* | The book that made host-based TDD for firmware a mainstream practice |
| **Bruce Powel Douglass** | *Design Patterns for Embedded Systems in C*; *Real-Time Agility* | Catalogue of RT patterns with concrete trade-off analysis |
| **Christopher Kormanyos** | *Real-Time C++* | The reference for using modern C++ properly on microcontrollers |
| **Jean Labrosse** | *MicroC/OS-II / µC/OS-III* books | Written by the kernel author; the classic "how an RTOS actually works" text |
| **Jonathan Valvano** | *Embedded Systems* series | Rigorous academic treatment with real hardware |
| **Colin Walls** | *Embedded Software: The Works* | Broad practitioner survey |
| **Rust Embedded WG** | *The Embedded Rust Book*, *Discovery*, *The Embedonomicon* | The canonical embedded Rust texts |

### 15.2 Primary documentation (always prefer over blogs)
- **Arm**: Architecture Reference Manuals (ARMv7-M ARM, ARMv8-M ARM), core Technical
  Reference Manuals, CMSIS documentation, and Arm's application notes.
- **Zephyr**: `docs.zephyrproject.org` — release notes, migration guides, devicetree
  bindings index.
- **FreeRTOS**: `freertos.org` — the API docs and the "FreeRTOS on Cortex-M" pages,
  especially the interrupt-priority section.
- **Espressif**: ESP-IDF Programming Guide (versioned per chip), plus the technical
  reference manuals and **errata**.
- **Silicon vendors**: reference manual + datasheet + **errata sheet** (read the errata;
  the bug you're chasing is often in there) + app notes.
- **IETF RFCs** worth knowing by number: **7228** (terminology for constrained-node
  networks — defines Class 0/1/2 devices), **7252** (CoAP), **8323** (CoAP over TCP/TLS),
  **8949** (CBOR), **9019**/**9124** (SUIT firmware update), **9147** (DTLS 1.3),
  **8554** (LMS), **8391** (XMSS).
- **Standards bodies**: MISRA (`misra.org.uk`), IEC/ISO, IEEE 802.1/802.3, Bluetooth SIG,
  CSA (`csa-iot.org`), OPC Foundation, LoRa Alliance, 3GPP.

### 15.3 Ongoing sources worth following
**Interrupt** (Memfault's engineering blog — consistently the best deep firmware writing
being published), **Embedded Artistry** (Phillip Johnston — architecture and process),
**Jack Ganssle's Embedded Muse**, **Beningo Embedded Group** (Jacob Beningo),
**Ferrous Systems** blog (Rust safety-critical), **embedded.fm** podcast (Elecia White),
**The Amp Hour**, **Phil's Lab** (hardware/firmware crossover), **CNX Software** (news),
**/r/embedded** (surprisingly high signal for tooling and part-selection questions),
and the **Rust Blog's** safety-critical series.

---
