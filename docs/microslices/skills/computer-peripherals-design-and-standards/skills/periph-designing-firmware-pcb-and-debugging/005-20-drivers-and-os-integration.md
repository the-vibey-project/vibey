---
id: skill-20-drivers-and-os-integration-e4838fa83e
purpose: 20 drivers and os integration
source: src/vibey_tools/skills/plugins/computer-peripherals-design-and-standards/skills/periph-designing-firmware-pcb-and-debugging/SKILL.md
requires: ["skill-19-enumeration-and-debugging-5b93883665"]
links: ["skill-21-measuring-latency-64bb759a23"]
---

## §20. Drivers and OS Integration

**⚠️ Prefer the class driver** (§1 → `periph-stack-usb-thunderbolt-and-wireless`, §8 → `periph-buses-pcie-hid-keyboards-mice-and-displays`) — ⚠️ **a custom driver is a permanent maintenance
liability across OS versions.**
**⚠️ Userspace access** is the middle path: ⚠️ **libusb, HIDAPI, WebUSB and WebHID —
⚠️ and WebHID in particular means a configuration tool can be a web page rather than an
installed application, which is a genuine improvement in the peripheral world.**
**⚠️ When a kernel driver is genuinely required**: ⚠️ **Windows WDF/UMDF and driver signing;
Linux kernel modules; macOS DriverKit having replaced kexts.**
**⚠️ Permissions**: ⚠️ **udev rules on Linux, and the mistake of instructing users to run
things as root rather than shipping a rules file.**
**⚠️ The honest observation about vendor software**: ⚠️ **much peripheral configuration
software is heavy, runs at startup, and exists partly for telemetry — which is why
ONBOARD PROFILE STORAGE is a real feature, letting the device keep its configuration
without resident software.**

---
