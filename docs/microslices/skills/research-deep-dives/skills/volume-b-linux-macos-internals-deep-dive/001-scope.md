---
id: skill-scope-2d3e18b68f
purpose: scope
source: src/vibey_tools/skills/plugins/research-deep-dives/skills/volume-b-linux-macos-internals-deep-dive/SKILL.md
requires: []
links: ["skill-1-boot-and-initialization-6e057344a9"]
---

## Scope

An operating system is a layered contract: firmware and hardware initialize a machine; a kernel manages privileged resources; drivers and filesystems expose abstractions; services compose a usable environment; libraries and runtimes support programs; applications operate above those layers. The layers leak: filesystem semantics affect durability, package policy affects boot, drivers affect security, and language runtimes depend on ABI and kernel behavior.
