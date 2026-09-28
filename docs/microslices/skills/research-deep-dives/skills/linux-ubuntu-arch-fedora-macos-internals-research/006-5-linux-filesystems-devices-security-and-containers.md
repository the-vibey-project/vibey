---
id: skill-5-linux-filesystems-devices-security-and-containers-c89caa2e52
purpose: 5 linux filesystems devices security and containers
source: src/vibey_tools/skills/plugins/research-deep-dives/skills/linux-ubuntu-arch-fedora-macos-internals-research/SKILL.md
requires: ["skill-4-kernel-programming-b1694a8ab6"]
links: ["skill-6-ubuntu-700fe1b587"]
---

## 5. Linux filesystems, devices, security, and containers

- `/proc`: process and kernel state.
- `/sys`: devices, buses, drivers, kernel objects, and attributes.
- `/dev`: device nodes, commonly created by udev/systemd-udevd.
- `/run`: volatile runtime state.
- `/etc`: host configuration.
- `/var`: logs, caches, package state, spools, and databases.
- `/usr`: most installed userland in modern unified-usr layouts.

Namespaces isolate process IDs, mounts, networking, users, IPC, and cgroups. Cgroups control and account for CPU, memory, I/O, PIDs, and other resources. Containers combine these with filesystem isolation and a process runtime but share the host kernel; they are not VMs.

AppArmor and SELinux use Linux security-module hooks. Fedora commonly emphasizes SELinux; Ubuntu commonly uses AppArmor. Capabilities split root privileges, seccomp restricts syscalls, and namespaces reduce visibility.
