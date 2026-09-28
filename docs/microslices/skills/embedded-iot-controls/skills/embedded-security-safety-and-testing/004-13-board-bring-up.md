---
id: skill-13-board-bring-up-03ee099e9a
purpose: 13 board bring up
source: src/vibey_tools/skills/plugins/embedded-iot-controls/skills/embedded-security-safety-and-testing/SKILL.md
requires: ["skill-12-testing-verification-and-debugging-534af92c27"]
links: []
---

## §13. Board Bring-Up

A sequence that saves days, in order. Do not skip ahead.

1. **Power rails first, with the MCU unpopulated or held in reset.** Verify every rail's
   voltage, ripple, and sequencing on a scope. A rail that's 200 mV low explains
   everything downstream.
2. **Reset and boot pins**: confirm reset releases and BOOT straps read as intended.
3. **Clock**: probe the crystal (with a low-capacitance probe — a 10 pF probe can stop a
   marginal oscillator). Output the system clock on the MCU's clock-out pin (MCO) and
   measure it. A wrong PLL config invalidates every timing measurement you make later.
4. **Debug connection**: can the probe halt and read the core? If not, check SWD pins
   aren't remapped, power isn't in a low-power mode at boot, and there's no code already
   flashed that disables debug.
5. **Blink an LED** from a bare-metal register write. This proves clock + GPIO + toolchain
   + flash programming + linker script all work. Do not proceed until it blinks.
6. **UART/RTT output**: get a "hello" out. Now you have observability.
7. **Each peripheral, one at a time, in isolation**, verified with a logic analyzer against
   the datasheet's timing diagram — not against "the sensor returned something."
8. **Power measurement**: measure sleep current before you write application code. If
   deep-sleep current is 3 mA instead of 3 µA, you want to know now, while the cause is
   still findable.
9. **Then** integrate.

**Hardware/firmware co-development**: firmware should review the schematic before layout.
The cheap things to catch at that stage: test points on every bus, a debug header that
isn't under a connector, no strapping pins used as outputs, LEDs on spare GPIOs for
state indication, a way to measure current (a 0 Ω shunt in series with the MCU supply),
and pull-ups sized for the actual bus capacitance.
