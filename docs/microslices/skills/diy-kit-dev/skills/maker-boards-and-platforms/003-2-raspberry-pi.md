---
id: skill-2-raspberry-pi-d5935d95f7
purpose: 2 raspberry pi
source: src/vibey_tools/skills/plugins/diy-kit-dev/skills/maker-boards-and-platforms/SKILL.md
requires: ["skill-1-choosing-a-board-a7236d8886"]
links: ["skill-3-arduino-esp32-and-the-microcontroller-field-e58c043b39"]
---

## §2. Raspberry Pi

**[VERSIONED] The families**: **Model B** (the main boards), **Zero** (small, cheap,
low-power), **400/500** (a computer inside a keyboard), **Compute Module** (for embedding
in your own product), and **Pico** — ⚠️ **which is a microcontroller, not a Linux
computer**, and is conceptually closer to an Arduino or ESP32 than to a Pi.

### 2.1 The current lineup (mid-2026)

| Board | Notes |
|---|---|
| **Pi 5** | The current flagship. BCM2712, PCIe for NVMe. ⚠️ **Wants active cooling and a proper 5V/5A USB-C supply** |
| **Pi 4B** | Still widely deployed and a fine budget entry. Firmware-boosted to 1.8 GHz |
| **Pi Zero 2 W** | ⚠️ **The value pick.** Outperforms a Pi 3B on most tasks at lower power and cost |
| **Pi 500 / 500+** | Pi 5 in a keyboard. 500 is 8 GB; **500+ (Sept 2025, ~$200) adds 16 GB RAM, a 256 GB NVMe SSD, and a mechanical keyboard** |
| **CM5** | Compute Module 5 — BCM2712 as a module for your own carrier board. §13 → `maker-networking-enclosures-and-productization` |
| **Pico 2 / Pico 2 W** | **RP2350: dual Cortex-M33 @ 150 MHz**, floating point and DSP. From **$5**. W adds Wi-Fi and **Bluetooth 5.2** |

**⚠️ Pi 1/2/3 are not worth buying new** — a Zero 2 W beats a 3B for less money and less
power.

**[VERSIONED] The RP2350 chip is separately purchasable** for your own designs:
**RP2350A (7×7 QFN60) ~$1.10** and **RP2350B (10×10 QFN80) ~$1.20** singly, dropping to
**~$0.80–0.90 on reels** — with **RP2354** variants adding 2 MB stacked flash.
**⚠️ This matters more than it looks**: it's a credible, well-documented, cheaply available
MCU for a custom board, backed by unusually good documentation.

### 2.2 The Pi gotchas

> **⚠️ GOTCHA — the recurring Raspberry Pi failure modes, in order of how often they bite:**
> - **⚠️ SD card corruption is the #1 Pi reliability problem.** Cheap or counterfeit cards,
>   sudden power loss, and write-heavy workloads kill them. **Fixes: a good A2-rated card,
>   move logs to tmpfs, consider read-only root, or boot from USB/NVMe on a Pi 5.**
> - **Under-voltage.** ⚠️ **The lightning-bolt icon and `vcgencmd get_throttled` are your
>   friends.** A phone charger is not a Pi supply. The Pi 5 in particular wants 5V/5A.
> - **Thermal throttling.** The Pi 5 needs active cooling under sustained load.
> - **No ADC.** Add an MCP3008 or use an MCU.
> - **⚠️ GPIO is 3.3V and not 5V-tolerant.** 5V on a GPIO pin will destroy the chip.
>   **Level-shift.**
> - **Not real-time.** Don't bit-bang timing-critical protocols from Linux userspace.
> - **Unclean shutdown** corrupts filesystems. Add a UPS HAT or design for it.

### 2.3 The alternatives
**Orange Pi, Radxa Rock, Banana Pi, Libre Computer, Odroid** — frequently better specs per
dollar. **⚠️ The trade-off is real and consistently underweighted: software support and
community size.** Raspberry Pi's advantage was never the hardware — it's that every
tutorial, library, and forum answer assumes it. **For a first project, that's worth more
than the extra RAM.**
**Jetson Orin Nano / Super** for genuinely GPU-heavy vision and ML.
**BeagleBone** for its PRUs (real-time cores alongside Linux) — a genuinely distinctive
answer to §1's timing problem.

---
