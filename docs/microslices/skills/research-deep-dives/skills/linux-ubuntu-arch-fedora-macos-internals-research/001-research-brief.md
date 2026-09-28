---
id: skill-research-brief-5950b4d78a
purpose: research brief
source: src/vibey_tools/skills/plugins/research-deep-dives/skills/linux-ubuntu-arch-fedora-macos-internals-research/SKILL.md
requires: []
links: ["skill-1-universal-os-model-caec6f7213"]
---

## Research brief

This reference explains how Linux-based operating systems and macOS work, how to program them, how to build distributions and images, and how to test software from user space through kernels and drivers.

Important distinctions:

- **Linux** is the kernel.
- **Ubuntu, Arch, and Fedora** are distributions: kernels, user space, package systems, defaults, security policy, release engineering, and documentation.
- **macOS** uses the partially open Darwin/XNU foundation plus proprietary Apple components, frameworks, drivers, firmware, graphics, and security infrastructure.
- An application, daemon, kernel module, driver, system extension, package, container, and VM are different engineering boundaries.

Commands are version-sensitive. Test bootloaders, kernels, filesystems, drivers, partitions, and security changes only in disposable VMs, snapshots, test disks, or systems with verified backups.
