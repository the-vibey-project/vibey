---
id: skill-15-anti-patterns-122967ed57
purpose: 15 anti patterns
source: src/vibey_tools/skills/plugins/diy-kit-dev/skills/maker-reference/SKILL.md
requires: []
links: ["skill-16-contested-questions-9215fffa11"]
---

## §15. Anti-Patterns

| Anti-pattern | Why |
|---|---|
| Reaching for a Pi when an MCU would do | Boot time, power, SD corruption, no real-time (§1 → `maker-boards-and-platforms`) |
| Reaching for an MCU when you need Linux | Fighting the platform (§1 → `maker-boards-and-platforms`) |
| **Not checking power first** | ⚠️ **The most common root cause of everything** (§4 → `maker-power-electronics-and-io`) |
| Powering motors or servos from the board regulator | ⚠️ **The classic destruction** (§4.1 → `maker-power-electronics-and-io`) |
| Sizing the supply for average, not peak | Brownouts that look like software bugs (§4.1 → `maker-power-electronics-and-io`) |
| No decoupling capacitors | "Random reboots" and flaky sensors (§4.1 → `maker-power-electronics-and-io`) |
| Separate supplies without common ground | Nothing works, signals float (§4.1 → `maker-power-electronics-and-io`) |
| Assuming the USB cable is fine | ⚠️ Charge-only and thin cables cause under-voltage (§4.1 → `maker-power-electronics-and-io`) |
| 5V signal into a 3.3V pin | Destroys the part. Level-shift (§4.2 → `maker-power-electronics-and-io`) |
| LED without a current-limiting resistor | Burns out. Every time (§5 → `maker-power-electronics-and-io`) |
| Floating input instead of a pull-up/pull-down | ⚠️ **Not "low" — random** (§5 → `maker-power-electronics-and-io`) |
| No flyback diode on a motor/relay/solenoid | ⚠️ Kills the driver transistor (§5 → `maker-power-electronics-and-io`) |
| Not debouncing a mechanical switch | One press reads as several (§6 → `maker-power-electronics-and-io`) |
| Trusting a cheap sensor's absolute reading | Accurate relatively, wrong absolutely (§6 → `maker-power-electronics-and-io`) |
| Treating a disconnected sensor's 0 as real | ⚠️ **Failures read as plausible values** (§6 → `maker-power-electronics-and-io`) |
| Resistive soil moisture sensors | Corrode away in weeks (§6 → `maker-power-electronics-and-io`) |
| Believing "eCO₂" is CO₂ | It's a VOC-based estimate (§6 → `maker-power-electronics-and-io`) |
| Undersizing LED strip power | ~60mA/pixel at white; 300 LEDs ≈ 18A (§7 → `maker-power-electronics-and-io`) |
| **Breadboarding mains voltage** | ⚠️ **Different category of risk** (§7 → `maker-power-electronics-and-io`) |
| Charging LiPo unattended on a flammable surface | ⚠️ **The one fire risk here** (§4.3 → `maker-power-electronics-and-io`) |
| `delay()` in anything that must stay responsive | Blocks everything (§8 → `maker-software-build-and-debug`) |
| Wi-Fi credentials committed to GitHub | ⚠️ Happens constantly (§11 → `maker-networking-enclosures-and-productization`) |
| No watchdog on a permanent installation | You'll be visiting it (§13 → `maker-networking-enclosures-and-productization`) |
| No OTA update path | You'll be physically retrieving it (§13 → `maker-networking-enclosures-and-productization`) |
| Assuming a working prototype is nearly a product | ⚠️ **The last 10% is 90%** (§13 → `maker-networking-enclosures-and-productization`) |
| Permanent project left on a breadboard | Intermittent contact faults forever (§9.1 → `maker-software-build-and-debug`) |
| Not documenting the pinout as you build | You won't remember in six months (§9.3 → `maker-software-build-and-debug`) |
| Signal wires bundled with motor wires | Coupled noise you'll blame on software (§9.3 → `maker-software-build-and-debug`) |
| Sealed outdoor enclosure with no drainage | ⚠️ **Condensation forms inside** (§12 → `maker-networking-enclosures-and-productization`) |
| PLA enclosure in direct sun or a car | Deforms. Use PETG (§12 → `maker-networking-enclosures-and-productization`) |
| Trusting an untested cheap SD card | ⚠️ Test with `f3`/H2testw first (§14 → `maker-networking-enclosures-and-productization`) |
| Buying critical ICs or power supplies from the cheapest source | Counterfeits (§14 → `maker-networking-enclosures-and-productization`) |
| Adopting a brand-new chip before toolchain support lands | ⚠️ **Pre-production silicon isn't hobby-ready** (§3.3 → `maker-boards-and-platforms`) |
| Debugging code before verifying power, ground and connections | Wrong order (§10 → `maker-software-build-and-debug`) |
| Hot-plugging sensors onto a powered board | Voltage on a pin before ground connects (§10 → `maker-software-build-and-debug`) |

---
