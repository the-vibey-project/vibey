---
id: skill-6-sensors-and-inputs-36883d5d02
purpose: 6 sensors and inputs
source: src/vibey_tools/skills/plugins/diy-kit-dev/skills/maker-power-electronics-and-io/SKILL.md
requires: ["skill-5-the-electronics-you-actually-need-46edae03cc"]
links: ["skill-7-outputs-motors-and-actuators-c3a03ec9b8"]
---

## §6. Sensors and Inputs

**[DURABLE] The categories, with the ones actually worth using:**

| Measuring | Common parts | ⚠️ Notes |
|---|---|---|
| **Temp / humidity** | **BME280/BME680** (I²C, also pressure/gas), DS18B20 (1-Wire, waterproof versions), SHT4x | ⚠️ **Avoid DHT11 — it's cheap and bad.** DHT22 is tolerable; BME280 is better for pennies more |
| **Motion** | PIR (HC-SR501), mmWave radar (LD2410) | ⚠️ **mmWave detects presence, not just motion** — it sees a stationary person. Big upgrade for room occupancy |
| **Distance** | HC-SR04 (ultrasonic, cheap, crude), VL53L0X/L1X (laser ToF, precise), LiDAR | Ultrasonic is confused by soft surfaces and angles |
| **Light** | LDR (crude), BH1750/TSL2591 (calibrated lux) | |
| **Motion/orientation** | MPU6050 (⚠️ ubiquitous and ageing), BNO085 (⚠️ **on-board sensor fusion — worth the money**), ICM-20948 | Raw IMU data needs fusion; a chip that does it for you saves enormous effort |
| **Current** | INA219/INA226 (I²C), ACS712 (hall) | For measuring your own power draw (§4.4) |
| **Air quality** | SGP30/SGP41 (VOC), SCD40/41 (⚠️ **true NDIR CO₂ — accept no "eCO₂" substitute**), PMS5003 (particulates) | ⚠️ **"eCO₂" from a VOC sensor is an estimate, not a CO₂ measurement** |
| **Soil moisture** | Capacitive | ⚠️ **Never resistive — it corrodes away in weeks** |
| **Camera** | Pi Camera Module 3, ESP32-CAM, USB webcam | ESP32-CAM is cheap and fiddly |
| **RFID/NFC** | RC522, PN532 | |
| **Input** | Buttons (⚠️ **debounce them**), rotary encoders, capacitive touch, joysticks | Debounce in hardware (RC) or software |

**[DURABLE] The practices that separate working from flaky:**
- **⚠️ Debounce every mechanical switch.** A button press is electrically several presses.
- **Filter noisy analog readings** — moving average or an exponential filter. **Raw ADC
  readings jitter.**
- **Calibrate.** ⚠️ **Cheap sensors are frequently accurate in relative terms and wrong in
  absolute ones.** Compare against a known reference before trusting a number.
- **Read the datasheet for the settling and warm-up time.** Many sensors need seconds to
  minutes before their first reading means anything — **gas sensors especially.**
- **Handle the failure case.** ⚠️ **A disconnected sensor often reads a plausible value
  (0, or full-scale), not an error.** Sanity-check ranges.

---
