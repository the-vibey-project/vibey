---
id: skill-1-choosing-a-board-a7236d8886
purpose: 1 choosing a board
source: src/vibey_tools/skills/plugins/diy-kit-dev/skills/maker-boards-and-platforms/SKILL.md
requires: ["skill-0-routing-de627438fa"]
links: ["skill-2-raspberry-pi-d5935d95f7"]
---

## §1. Choosing a Board

**[DURABLE] The single decision that determines everything else.** The mistake in both
directions: reaching for a Pi because Linux is familiar, or forcing a microcontroller to
do something that genuinely needs an OS.

### 1.1 The decision tree

```
Does it need a filesystem, a display server, a camera pipeline,
containers, or arbitrary Linux software?
├─ YES → Single-board computer (Raspberry Pi 5 / Zero 2 W / alternatives)  §2
└─ NO  → Does it need to be battery-powered for weeks/months?
         ├─ YES → Microcontroller, and low-power design matters       §4.4
         └─ NO  → Does it need Wi-Fi/BLE?
                  ├─ YES → ESP32 family (usually ESP32-S3 or C6)      §3.3
                  └─ NO  → Pico / Arduino / any cheap MCU             §2.3, §3
```

**[DURABLE] The questions that actually decide it:**

| Question | Why it matters |
|---|---|
| **Real-time timing?** | ⚠️ **Linux is not real-time.** Precise pulse timing, motor control, and protocol bit-banging want an MCU |
| **Boot time** | MCU: instant. Pi: 20–30 seconds, and it must shut down cleanly |
| **Power budget** | MCU: µA–mA in sleep. Pi: hundreds of mA minimum, always |
| **⚠️ Will it lose power unexpectedly?** | **An SD-card Pi hates this.** MCUs don't care |
| **Analog inputs?** | ⚠️ **Raspberry Pi has no ADC.** MCUs do. This surprises people constantly |
| **Networking** | Pi: full stack. ESP32: excellent Wi-Fi/BLE. Pico W: good. AVR Arduino: needs a shield |
| **Heavy compute / vision / ML** | Pi 5, or an MCU with an accelerator for small models |
| **Unit cost at volume** | §13 → `maker-networking-enclosures-and-productization` |

**[DURABLE] The hybrid answer is often the right one and under-used**: a **Pico or ESP32
handling real-time I/O, talking to a Pi over UART/I²C/USB** that handles networking,
storage, and logic. You get deterministic timing *and* Linux.

---
