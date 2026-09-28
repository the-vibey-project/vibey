---
id: skill-17-currency-snapshot-verified-august-2026-dd7aa6a206
purpose: 17 currency snapshot verified august 2026
source: src/vibey_tools/skills/plugins/diy-kit-dev/skills/maker-reference/SKILL.md
requires: ["skill-16-contested-questions-9215fffa11"]
links: ["skill-18-the-canon-d7e87c995c"]
---

## §17. Currency Snapshot — verified August 2026

**[DURABLE] The electronics fundamentals (§4 → `maker-power-electronics-and-io`, §5 → `maker-power-electronics-and-io`, §9 → `maker-software-build-and-debug`, §10 → `maker-software-build-and-debug`) have not changed in decades
and won't.** What follows is the part that moves.

| Thing | Status as of Aug 2026 | Decay risk |
|---|---|---|
| **⚠️ Qualcomm–Arduino** | **Announced 7 October 2025**, subject to regulatory approval; terms undisclosed. Arduino to remain an **independent brand supporting multiple silicon vendors**. Launched alongside the **UNO Q** — **"dual brain": Qualcomm Dragonwing QRB2210 running Debian Linux + an STMicro MCU**, with **Edge Impulse** for edge AI and **Arduino App Lab**. ⚠️ **First UNO-family board that is a standalone SBC rather than an MCU dev board.** Builds on Qualcomm's Edge Impulse and Foundries.io acquisitions. Arduino cited **33M active users** | Low (event) |
| **⚠️ Community reaction** | **Openly skeptical** — IEEE Spectrum: *"Qualcomm Buys Arduino, and the Open-Source Community Is Skeptical."* Adafruit noted **Arduino and Qualcomm did not respond to inquiries over several months** and read the "community trust"/"heritage" language as **defensive framing**. **Flashpoint: a T&C change read as locking down previously-open software/hardware** — **Arduino says that reading was incorrect** and held an AMA (with Qualcomm, Edge Impulse, STMicro) reasserting **"100% commitment"** to open source and continued non-Qualcomm partnerships. ⚠️ **Where it lands is not yet knowable** | Medium |
| **Raspberry Pi lineup** | **Pi 5** flagship (BCM2712, PCIe/NVMe, wants 5V/5A + active cooling). **Pi 4B** still current-ish. **Zero 2 W** the value pick — beats a 3B for less. **Pi 500** (Pi 5 in a keyboard, 8 GB); **Pi 500+ (Sept 2025, ~$200): 16 GB RAM, 256 GB NVMe, mechanical keyboard**. **CM5** for embedding. **Pi 1/2/3 not worth buying new** | Medium |
| **Pico / RP2350** | **Pico 2 / 2 W: RP2350, dual Cortex-M33 @ 150 MHz with FP and DSP, from $5**; W adds Wi-Fi + **BT 5.2**. **Chips sold separately: RP2350A ~$1.10, RP2350B ~$1.20 singly; ~$0.80–0.90 on reels.** **RP2354** variants add 2 MB stacked flash | Medium |
| **ESP32 family** | ⚠️ **Roughly a dozen variants now.** **S3** = best hobbyist all-rounder (Xtensa dual 240 MHz, 128-bit SIMD for wake-word/vision, USB, camera/LCD). **C3** = cheap RISC-V. **C6** = Wi-Fi 6 + BLE + 802.15.4 → **Thread/Zigbee/Matter; the pick for net-new battery sensors**. **H2** = 802.15.4-only Matter-over-Thread. **P4** = dual RISC-V 400 MHz, MIPI CSI/DSI, **H.264 1080p30, up to 32 MB PSRAM, ⚠️ no wireless — needs a C5/C6 companion** | **High** |
| **⚠️ New-silicon caution** | Newer parts (S31, C61, H21 and others announced through 2026) may be **pre-production, without official modules, and unsupported in Arduino-ESP32 or MicroPython**, while established parts have **abundant module stock, lowest price, most stable supply, richest community support.** **Check toolchain support first** | **High** |
| **Toolchains** | **ESP32 Arduino Core 3.1.x** (Jan 2026) covers ESP32/S3/C6 with full BLE 5 + Wi-Fi 6 on newer chips; the popular libraries "just work." **Pico W Arduino core (Philhower) stable**, though with fewer complex libraries. **MicroPython 1.27.0 (Dec 2025)**, with ESP32-P4 builds including C5/C6-coprocessor variants. **CircuitPython** actively developed; Matter/Thread support constrained by needing C SDK linkage | Medium |
| **Supply chain** | Reported as **stable in 2026**, having recovered from 2024 disruptions around newly-introduced parts (ESP32-P4, Pico 2 W). ESP32 modules in mass production; Pico W stock steady | Medium |

**Goes stale fastest:** §3.3 → `maker-boards-and-platforms`'s ESP32 variant table and §2.1 → `maker-boards-and-platforms`'s lineup. **Essentially never
stale:** §4 → `maker-power-electronics-and-io`, §5 → `maker-power-electronics-and-io`, §6 → `maker-power-electronics-and-io`'s practices, §9 → `maker-software-build-and-debug`, §10 → `maker-software-build-and-debug`, §15.

---
