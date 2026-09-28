---
id: skill-9-testing-and-debugging-b5348bd2c8
purpose: 9 testing and debugging
source: src/vibey_tools/skills/plugins/research-deep-dives/skills/volume-b-linux-macos-internals-deep-dive/SKILL.md
requires: ["skill-8-languages-and-toolchains-899c26e659"]
links: ["skill-10-macos-architecture-f5c0d0844a"]
---

## 9. Testing and debugging

Test at multiple levels: unit, syscall and ABI, filesystem and storage faults, service integration, virtualization and hardware matrices, fuzzing, stress, race, fault injection, security boundaries, reproducible builds, package transactions, upgrades, rollback and disaster recovery.

Useful Linux tools include strace, gdb, perf, bpftrace, ftrace, journalctl, systemd-analyze, lsns, nsenter, coredumpctl, lsof, ss, ip, ethtool, mount, findmnt and dmesg. Each observes a different layer.

A useful bug report includes kernel and distribution version, hardware, exact reproduction, expected and observed results, logs, recent changes, a minimal case and whether the failure survives a clean environment.
