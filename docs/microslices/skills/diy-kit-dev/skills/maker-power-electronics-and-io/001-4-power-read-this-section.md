---
id: skill-4-power-read-this-section-4bf4b0ad9d
purpose: 4 power read this section
source: src/vibey_tools/skills/plugins/diy-kit-dev/skills/maker-power-electronics-and-io/SKILL.md
requires: []
links: ["skill-5-the-electronics-you-actually-need-46edae03cc"]
---

## §4. Power — Read This Section

**[DURABLE] More project failures trace to power than to anything else, and it's rarely
the first thing people check.**

### 4.1 The rules

- **⚠️ Amps are pulled, not pushed.** A 5V/3A supply doesn't force 3A into your circuit;
  the circuit draws what it needs up to that limit. **Undersizing means brownouts, not a
  clean failure.**
- **⚠️ Budget for peak, not average.** A Wi-Fi transmit burst, a motor stall, or a servo
  starting can be **many times** the idle draw — and lasts milliseconds, which is exactly
  long enough to reset your board and short enough to be invisible on a multimeter.
- **⚠️ Never power motors or servos from a board's regulator.** This is the single most
  common beginner destruction. **Separate supply, common ground.**
- **Decoupling capacitors.** 0.1 µF ceramic next to every IC's power pin, plus bulk
  electrolytic (100–1000 µF) near motors and LED strips. **⚠️ This fixes a startling
  proportion of "random reboot" and "flaky sensor" problems.**
- **Common ground, always.** Separate supplies must share a ground reference or nothing
  works and signals float.
- **⚠️ Wire gauge and voltage drop are real.** Long thin wires to an LED strip cause dim
  ends and brownouts. Inject power at both ends of a long run.
- **USB cables are not equal.** ⚠️ **A charge-only or thin cable causes under-voltage that
  presents as software flakiness.** Suspect the cable early.

### 4.2 Common voltages
**5V** (USB, most Arduinos, LED strips), **3.3V** (ESP32, Pi GPIO, most modern sensors,
most SD cards), **12V** (motors, LED strips, automotive), **LiPo 3.7V nominal** (⚠️ **3.0–4.2V
across its range — plan for both ends**).

**⚠️ Level shifting is not optional.** Connecting a 5V output to a 3.3V input destroys the
3.3V part. A **bidirectional level shifter** or even a resistor divider for one-way
signals costs pennies. **A 3.3V output into a 5V input often works** (many 5V parts read
3.3V as high) — **but check the datasheet rather than assuming.**

### 4.3 Batteries
**LiPo/Li-ion** — best energy density, needs **protection circuitry and a proper charge
IC (TP4056 and better)**. **⚠️ Lithium cells are genuinely dangerous when mistreated: never
charge unattended on a flammable surface, never puncture, never over-discharge, and never
use a cell that has swollen.** This is the one place in hobby electronics where the failure
mode is fire.
**18650 cells** — cheap, replaceable, ⚠️ **and the counterfeit rate is enormous** (a
"9900mAh" 18650 does not exist; real cells top out around 3500mAh).
**LiFePO4** — safer chemistry, lower density, longer life.
**Alkaline/NiMH** — fine for low-drain, no fire risk.
**Solar** — needs a charge controller sized for a rainy week, not an average day.

### 4.4 Low-power design
**[DURABLE] The order of magnitude that matters**: an ESP32 running Wi-Fi continuously
lasts hours on a small battery; the **same ESP32 in deep sleep, waking briefly to
transmit, lasts months.**
**The techniques**: deep sleep between readings (⚠️ **the dominant lever by far**),
duty-cycling the radio, powering sensors from a GPIO so they're fully off, cutting
regulator quiescent current, and **⚠️ measuring actual consumption** — a USB power meter or
a current-sense module tells you in minutes what guessing won't tell you in a week.

---
