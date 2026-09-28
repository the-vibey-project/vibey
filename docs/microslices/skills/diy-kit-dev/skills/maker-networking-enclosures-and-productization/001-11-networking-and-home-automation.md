---
id: skill-11-networking-and-home-automation-c82b8bce11
purpose: 11 networking and home automation
source: src/vibey_tools/skills/plugins/diy-kit-dev/skills/maker-networking-enclosures-and-productization/SKILL.md
requires: []
links: ["skill-12-enclosures-and-fabrication-fe58655272"]
---

## §11. Networking and Home Automation

**Protocols**: **Wi-Fi** (easy, power-hungry), **BLE** (low power, short range),
**Zigbee** and **Thread** (mesh, low power, ⚠️ **need a coordinator/border router**),
**Matter** (⚠️ **the cross-vendor standard — an ESP32-C6 or H2 is the hobbyist path in**),
**LoRa / LoRaWAN** (⚠️ **kilometres of range at very low data rates — the right answer for
remote sensors**), **ESP-NOW** (⚠️ **Espressif's connectionless peer-to-peer protocol —
fast, no router needed, excellent for sensor→hub links**), **MQTT** (the default
application protocol for this world).

**[DURABLE] Home Assistant is the centre of gravity for hobbyist home automation**, and
**ESPHome** integrates with it so tightly that a sensor node becomes a YAML file. **If
you're building anything sensor-and-automation shaped, look there before writing code.**
**Node-RED** for flow-based logic; **InfluxDB + Grafana** for time-series and dashboards;
**Zigbee2MQTT** for bringing commercial Zigbee devices under your own control.

> **⚠️ GOTCHA — security, briefly but seriously.** Hobby IoT devices are notoriously bad,
> and yours will be too unless you decide otherwise. **The minimum: put them on a separate
> VLAN or guest network; don't port-forward anything to the internet (use a VPN or
> Tailscale); change default credentials; don't hardcode Wi-Fi passwords into code you'll
> push to GitHub** (⚠️ **this happens constantly — use a secrets file and gitignore it**);
> **prefer local control over cloud dependency**; and **have an update path** (§13).

---
