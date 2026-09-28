---
id: skill-11-macos-boot-launch-storage-and-security-b2733bc5f1
purpose: 11 macos boot launch storage and security
source: src/vibey_tools/skills/plugins/research-deep-dives/skills/volume-b-linux-macos-internals-deep-dive/SKILL.md
requires: ["skill-10-macos-architecture-f5c0d0844a"]
links: ["skill-12-drivers-and-system-extensions-650eeda3a2"]
---

## 11. macOS boot, launch, storage and security

macOS boot involves signed components, recovery, volume layout and platform policy. APFS supports containers, volumes, snapshots, encryption, copy-on-write metadata and space sharing. The visible filesystem hierarchy is a policy-managed composition, not simply an old writable root disk.

launchd manages system and user agents and daemons. Launch configuration uses property lists and constraints. Launch Services maps documents, applications, roles and user-facing activation.

Security includes code signing, Gatekeeper, notarization, sandboxing, TCC privacy controls, SIP, FileVault, keychain services, entitlements and authenticated system volumes. A root shell does not automatically bypass all controls because some are enforced by boot policy, hardware-backed keys, signed components, entitlements or consent databases.
