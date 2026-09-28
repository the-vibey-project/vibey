---
id: skill-12-drivers-and-system-extensions-650eeda3a2
purpose: 12 drivers and system extensions
source: src/vibey_tools/skills/plugins/research-deep-dives/skills/volume-b-linux-macos-internals-deep-dive/SKILL.md
requires: ["skill-11-macos-boot-launch-storage-and-security-b2733bc5f1"]
links: ["skill-13-macos-development-and-testing-8d752fb87a"]
---

## 12. Drivers and system extensions

Apple recommends DriverKit and System Extensions for many low-level functions rather than kernel extensions. DriverKit drivers run in user space. Network Extension supports VPN, DNS proxy, content filtering and related functions. Endpoint Security provides a C API for monitoring and, for authorized clients, controlling security-relevant events.

These systems require entitlements, signing, packaging, user approval and lifecycle testing. Kernel extensions are a constrained legacy path. Apple documents migration toward user-space extensions where possible.

Sources: [System Extensions](https://developer.apple.com/system-extensions/), [DriverKit](https://developer.apple.com/documentation/driverkit), [Endpoint Security](https://developer.apple.com/documentation/endpointsecurity).
