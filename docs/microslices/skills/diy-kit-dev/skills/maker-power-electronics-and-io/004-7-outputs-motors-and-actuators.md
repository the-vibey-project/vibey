---
id: skill-7-outputs-motors-and-actuators-c3a03ec9b8
purpose: 7 outputs motors and actuators
source: src/vibey_tools/skills/plugins/diy-kit-dev/skills/maker-power-electronics-and-io/SKILL.md
requires: ["skill-6-sensors-and-inputs-36883d5d02"]
links: []
---

## §7. Outputs, Motors and Actuators

| Actuator | Notes |
|---|---|
| **Servo** | Position control via PWM, 0–180°. ⚠️ **Cheap servos jitter and stall — and a stalling servo draws a lot** (§4.1) |
| **Continuous-rotation servo** | Speed, not position. Convenient for small robots |
| **DC motor** | Needs an **H-bridge driver** (L298N is common and inefficient; DRV8833 or TB6612FNG are better). ⚠️ **Never drive from a GPIO** |
| **Stepper** | Precise positioning. A28YBJ-48 + ULN2003 to learn; **NEMA 17 + A4988/TMC2209** for real work (⚠️ **TMC drivers are near-silent — worth it**) |
| **Solenoid / relay** | ⚠️ **Flyback diode** (§5). For mains, use a proper relay module or SSR |
| **LED strips** | **WS2812B/NeoPixel** (one data wire, ⚠️ **timing-critical — an ESP32/Pico handles this better than a busy Linux box**), **SK6812** (adds white), **APA102/DotStar** (clocked, easier timing). ⚠️ **Power budget: ~60mA per pixel at full white** — a 300-LED strip can pull 18A |
| **Displays** | SSD1306 OLED (tiny, cheap, I²C), ST7789/ILI9341 TFT (SPI, colour), e-paper (⚠️ **beautiful for low-refresh status displays and zero power when static**), HD44780 character LCD |
| **Audio** | DFPlayer Mini (MP3 from SD), I²S DACs, piezo buzzers |

> **⚠️ GOTCHA — mains voltage.** If your project switches 120/230V AC, that is a different
> category of risk from everything else here. **Use a properly enclosed, certified relay
> module or a commercial smart plug you control over the network** rather than wiring mains
> onto a breadboard. **If you're not confident, don't** — and in many jurisdictions
> permanent mains wiring is legally restricted to qualified electricians regardless of your
> confidence.
