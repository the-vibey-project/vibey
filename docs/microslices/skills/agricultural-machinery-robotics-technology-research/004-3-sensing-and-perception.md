---
id: skill-3-sensing-and-perception-cd8f287921
purpose: 3 sensing and perception
source: src/vibey_tools/skills/plugins/research-deep-dives/skills/agricultural-machinery-robotics-technology-research/SKILL.md
requires: ["skill-2-automotive-and-mechatronic-mechanics-bd803bdb0f"]
links: ["skill-4-precision-agriculture-76418eaf47"]
---

## 3. Sensing and perception

### Position and motion

GNSS/GPS, corrected signals, inertial measurement units, wheel-speed sensors, steering-angle sensors, radar, encoders, and machine-vision landmarks help estimate location and motion. Accuracy requirements vary: broad guidance may tolerate more error than seed placement, strip tillage, drainage installation, or orchard navigation.

Loss of correction signal, multipath, tree canopy, terrain, poor calibration, or a shifted implement can create systematic error. A system should detect uncertainty and degrade safely rather than silently continue with a false position.

### Soil and plant sensing

Sensors and imagery may estimate:

- soil moisture, temperature, texture, compaction, salinity, and nutrients;
- crop stand, height, biomass, color, stress, disease, weeds, maturity, and yield;
- fruit count, size, bruising, canopy temperature, and surface wetness;
- animal location, activity, rumination, body temperature, milk yield, and health indicators;
- grain moisture, temperature, quality, foreign material, and storage risk.

Sources include in-machine sensors, weather stations, satellites, drones, cameras, LiDAR, radar, thermal imaging, spectroscopy, soil probes, RFID, collars, load cells, and machine telemetry. Sensing is only useful when the measurement is calibrated, representative, timely, and connected to a decision.

USDA NIFA reports research on plant and fruit imaging, soil and plant moisture sensors, yield estimation, machine vision, disease detection, automated spraying, robotic harvest assistance, and heat or frost mitigation. It also reports that performance varies by crop and task; research demonstrations should not be treated as universal commercial capability. [USDA NIFA Automation for Specialty Crops](https://www.nifa.usda.gov/about-nifa/impacts/automation-specialty-crops)
