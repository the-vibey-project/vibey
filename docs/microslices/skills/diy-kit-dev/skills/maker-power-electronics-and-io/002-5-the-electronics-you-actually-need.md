---
id: skill-5-the-electronics-you-actually-need-46edae03cc
purpose: 5 the electronics you actually need
source: src/vibey_tools/skills/plugins/diy-kit-dev/skills/maker-power-electronics-and-io/SKILL.md
requires: ["skill-4-power-read-this-section-4bf4b0ad9d"]
links: ["skill-6-sensors-and-inputs-36883d5d02"]
---

## §5. The Electronics You Actually Need

**[DURABLE] You don't need an EE degree. You do need these.**

**Ohm's law** (V = IR) and **power** (P = VI). ⚠️ **The one calculation you will use
constantly: the LED series resistor.** R = (V_supply − V_forward) / I_desired. A red LED
at ~2V forward, 20mA, on 5V → (5−2)/0.02 = 150Ω.

**⚠️ LEDs without a current-limiting resistor burn out.** Every time. This is the most
common first mistake.

**Pull-up and pull-down resistors** — ⚠️ **a floating input is not "low," it's random.**
Buttons need a pull-up or pull-down (most MCUs have internal ones — `INPUT_PULLUP`).
**I²C requires pull-ups on SDA and SCL** — usually 4.7kΩ, and often already on breakout
boards (⚠️ **which is why chaining many breakouts can over-pull the bus**).

**Transistors and MOSFETs as switches** — when a GPIO pin can't supply enough current
(⚠️ **which is most of the time — a pin sources tens of milliamps at best**). Use a
**logic-level MOSFET** for DC loads and a **relay or solid-state relay** for AC.

**⚠️ Flyback diodes.** Any inductive load — motor, relay coil, solenoid — generates a
large reverse voltage spike when switched off that **will destroy your driver
transistor**. A diode across the coil is non-negotiable.

**Capacitors** — decoupling (§4.1), smoothing, timing. **Voltage regulators** — linear
(LM7805, AMS1117: simple, ⚠️ **wastes the difference as heat**) vs. switching/buck
(efficient, slightly noisier).

**The protocols you'll meet**:

| Protocol | Wires | Notes |
|---|---|---|
| **GPIO** | 1 | On/off |
| **PWM** | 1 | Dimming, servos, motor speed |
| **ADC** | 1 | Analog in. ⚠️ **Not on Raspberry Pi** |
| **I²C** | 2 + gnd | Addressed bus, many devices. ⚠️ **Address conflicts are the classic failure** |
| **SPI** | 4+ | Faster, one chip-select per device |
| **UART** | 2 + gnd | Serial. ⚠️ **TX→RX, RX→TX — crossed, not straight** |
| **1-Wire** | 1 + gnd | DS18B20 temperature sensors |
| **CAN** | 2 | Automotive and robust industrial |

**Tools worth owning**, in order of value: a **multimeter** (⚠️ **non-negotiable, and £20
is enough**), a decent **soldering iron** with temperature control, **helping hands**,
**wire strippers**, **flush cutters**, a **USB power meter**, and eventually a
**logic analyzer** (⚠️ **£10 clones of the Saleae work with the free Sigrok/PulseView
software and will save you days**) and a **bench power supply with current limiting**.

---
