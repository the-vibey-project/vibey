---
id: skill-14-cross-platform-programming-849b572021
purpose: 14 cross platform programming
source: src/vibey_tools/skills/plugins/research-deep-dives/skills/volume-b-linux-macos-internals-deep-dive/SKILL.md
requires: ["skill-13-macos-development-and-testing-8d752fb87a"]
links: ["skill-15-common-errors-f91d98f028"]
---

## 14. Cross-platform programming

Portable applications should isolate platform-specific code behind small interfaces and test filesystem paths, case behavior, permissions, Unicode, locale, process spawning, signals, networking, certificates, time zones, GPU capabilities, packaging, updates, sandboxing, consent, crash reporting and architecture differences.

Use capability detection rather than OS-name guessing. Treat errors as part of the API. Keep privileged operations small, auditable and separately tested.
