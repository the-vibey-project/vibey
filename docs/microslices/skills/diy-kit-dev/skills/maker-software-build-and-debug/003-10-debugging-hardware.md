---
id: skill-10-debugging-hardware-a011fcbc60
purpose: 10 debugging hardware
source: src/vibey_tools/skills/plugins/diy-kit-dev/skills/maker-software-build-and-debug/SKILL.md
requires: ["skill-9-building-it-physically-ef13a49de0"]
links: []
---

## §10. Debugging Hardware

**[DURABLE] The discipline is different from software debugging: you can't trust that the
hardware is doing what the code says.**

**The order to check, which is empirically the right order:**
```
1. POWER            §4. Voltage at the actual pin, under load, with a meter
2. GROUND           Common ground between everything?
3. CONNECTIONS      Continuity test. Breadboard contacts. Cold solder joints
4. ORIENTATION      Polarity, pin 1, TX/RX crossed
5. LEVELS           3.3V vs 5V mismatch
6. THE PART         Is it counterfeit, dead, or the wrong variant? (§14)
7. ONLY THEN        Your code
```

**Techniques**: **binary-search by disconnection** (remove half the circuit); **the blink
test** (⚠️ **an LED on a GPIO is the world's cheapest debugger**); **serial print
everything**; **a logic analyzer for any bus problem** (⚠️ **I²C and SPI issues are
essentially unguessable and completely obvious on a trace**); **`i2cdetect`** to confirm a
device is even present and at the address you think; **swap a known-good part**; and
**test subsystems in isolation before integrating.**

**⚠️ The magic-smoke rules**: unplug before rewiring; **double-check polarity before
applying power** (reversed polarity kills most things instantly); use a **current-limited
bench supply** for first power-up of anything new; and **don't hot-plug** — connecting a
sensor to a powered board can put voltage on a pin before ground connects.
