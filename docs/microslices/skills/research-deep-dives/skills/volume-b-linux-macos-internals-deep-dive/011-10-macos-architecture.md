---
id: skill-10-macos-architecture-f5c0d0844a
purpose: 10 macos architecture
source: src/vibey_tools/skills/plugins/research-deep-dives/skills/volume-b-linux-macos-internals-deep-dive/SKILL.md
requires: ["skill-9-testing-and-debugging-b5348bd2c8"]
links: ["skill-11-macos-boot-launch-storage-and-security-b2733bc5f1"]
---

## 10. macOS architecture

macOS combines Darwin components with proprietary Apple frameworks and services. Darwin includes the XNU kernel, which combines Mach concepts with BSD subsystems, plus I/O and userland components. Apple adds launch services, signing, notarization, sandboxing, privacy controls, APFS, frameworks, security policy, graphics stacks and hardware-specific behavior.

Apple Open Source releases are valuable but incomplete. They do not expose every proprietary framework, service, driver, model or operational policy. Source availability for one component does not mean the whole macOS behavior is represented.

Sources: [Apple Open Source](https://opensource.apple.com/), [XNU source](https://github.com/apple-oss-distributions/xnu), [Apple Platform Security](https://support.apple.com/guide/security/welcome/web).
