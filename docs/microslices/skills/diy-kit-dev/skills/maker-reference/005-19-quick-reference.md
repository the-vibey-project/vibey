---
id: skill-19-quick-reference-0c36723fd7
purpose: 19 quick reference
source: src/vibey_tools/skills/plugins/diy-kit-dev/skills/maker-reference/SKILL.md
requires: ["skill-18-the-canon-d7e87c995c"]
links: ["skill-20-sources-and-method-dd063e8310"]
---

## §19. Quick Reference

### 19.1 Board picker
| Need | Board |
|---|---|
| Learning electronics, first project | **Arduino Uno R3** — 5V-tolerant, hard to break |
| Connected sensor / anything with Wi-Fi | **ESP32-S3** (or C6 for Matter/Thread) |
| Cheapest capable MCU | **Pico 2 / RP2350**, $5 |
| Battery sensor, months of life | **ESP32-C6** with deep sleep, or a Pico + LoRa |
| Linux, general purpose | **Pi 5** (or **Zero 2 W** for value) |
| Desktop replacement | **Pi 500 / 500+** |
| Camera, vision, ML | **Pi 5**, or **ESP32-S3**/**P4** for on-device |
| Video/display HMI panel | **ESP32-P4** + C6 companion |
| Real-time timing + Linux | **Pi + Pico over UART**, or BeagleBone PRU |
| Precise audio / timing | **Teensy** |
| BLE product | **Nordic nRF52/nRF53** |
| Teaching a child | **Micro:bit** |
| Embedding in your own product | **CM5**, or an **ESP32 module** (pre-certified) |

### 19.2 Numbers worth remembering
- **GPIO: 3.3V on Pi and ESP32, 5V on classic Arduino. ⚠️ Pi GPIO is not 5V-tolerant.**
- **A GPIO pin sources tens of mA at most.** Anything more needs a transistor.
- **LED resistor: R = (V_supply − V_forward) / I.** ~150–220Ω for a red LED on 5V.
- **I²C pull-ups: ~4.7kΩ** (often already on breakouts).
- **WS2812B: ~60mA per pixel at full white.**
- **Decoupling: 0.1µF at every IC power pin.**
- **LiPo: 3.0–4.2V**, nominal 3.7V.
- **Soldering: ~350°C leaded, ~370°C lead-free.**
- **PETG over PLA for enclosures.**

### 19.3 When it doesn't work
1. **Power** — measure at the pin, under load (§4 → `maker-power-electronics-and-io`)
2. **Ground** — common? (§4.1 → `maker-power-electronics-and-io`)
3. **Connections** — continuity, breadboard contacts, solder joints (§9.1 → `maker-software-build-and-debug`)
4. **Orientation** — polarity, pin 1, TX/RX crossed (§5 → `maker-power-electronics-and-io`)
5. **Voltage levels** — 3.3V vs 5V (§4.2 → `maker-power-electronics-and-io`)
6. **The part** — dead, wrong variant, or counterfeit? (§14 → `maker-networking-enclosures-and-productization`)
7. **Then the code** (§10 → `maker-software-build-and-debug`)

---
