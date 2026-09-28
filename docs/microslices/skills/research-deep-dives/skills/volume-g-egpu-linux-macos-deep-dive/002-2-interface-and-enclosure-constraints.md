---
id: skill-2-interface-and-enclosure-constraints-ab596c36d6
purpose: 2 interface and enclosure constraints
source: src/vibey_tools/skills/plugins/research-deep-dives/skills/volume-g-egpu-linux-macos-deep-dive/SKILL.md
requires: ["skill-1-what-an-egpu-is-52de06731c"]
links: ["skill-3-linux-architecture-7725430551"]
---

## 2. Interface and enclosure constraints

Check:

- host port actually supports Thunderbolt 3/4 or USB4 PCIe tunneling;
- host firmware and operating-system support;
- enclosure controller generation and firmware;
- cable certification, length, and signal quality;
- GPU physical length, thickness, power connectors, and airflow;
- enclosure PSU wattage and transient capacity;
- USB, Ethernet, and display-port bandwidth sharing;
- hot-plug, sleep/wake, reboot, and safe-removal behavior;
- external-display routing and internal-panel acceleration;
- warranty, repairability, and replacement availability.

Thunderbolt and USB4 are transport ecosystems, not guarantees that every port exposes external PCIe devices. A USB-C connector alone is not enough.

A self-contained enclosure is quieter and simpler; an open or modular enclosure can offer more upgradeability but requires more care with power, cooling, exposed electronics, and compatibility. Integrated docks may share bandwidth between GPU and peripherals.
