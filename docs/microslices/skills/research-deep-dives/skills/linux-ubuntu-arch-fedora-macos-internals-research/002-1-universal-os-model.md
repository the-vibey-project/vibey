---
id: skill-1-universal-os-model-caec6f7213
purpose: 1 universal os model
source: src/vibey_tools/skills/plugins/research-deep-dives/skills/linux-ubuntu-arch-fedora-macos-internals-research/SKILL.md
requires: ["skill-research-brief-5950b4d78a"]
links: ["skill-2-linux-internals-e407509031"]
---

## 1. Universal OS model

Hardware provides CPUs, privilege levels, virtual-memory hardware, caches, interrupts, timers, buses, storage, networking, GPUs, and firmware. The operating system turns those resources into abstractions:

- processes and threads;
- virtual address spaces and physical memory;
- filesystems and file descriptors;
- sockets and IPC;
- devices and drivers;
- credentials, permissions, capabilities, and sandboxes;
- schedulers, timers, signals, and resource limits;
- services, logs, package databases, and update mechanisms.

### Boot sequence

1. Firmware initializes hardware and selects a boot path.
2. A boot manager/loader selects kernel, command line, and initramfs.
3. The kernel establishes architecture state, page tables, interrupts, memory, scheduling, and early drivers.
4. The initramfs discovers storage, loads drivers, unlocks encryption, assembles RAID/LVM where applicable, and mounts the real root.
5. PID 1/service management starts logging, devices, networking, storage, security, display, and login services.
6. A session launches a shell, graphical desktop, or remote service.
7. A program is loaded through ELF or Mach-O, a dynamic linker, shared libraries, credentials, file descriptors, and policy.

### User/kernel boundary

User programs normally cannot touch arbitrary memory, devices, or privileged instructions. They use system calls, libraries, IPC, device files, sockets, or broker services. The kernel validates addresses, object handles, credentials, resource limits, and access policy.

Kernel bugs are system-wide failures. Prefer user-space APIs, FUSE, eBPF, a service, or macOS DriverKit/system extensions over kernel code whenever the problem allows.
