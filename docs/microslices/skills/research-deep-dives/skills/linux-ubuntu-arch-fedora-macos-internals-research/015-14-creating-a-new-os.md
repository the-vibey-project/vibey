---
id: skill-14-creating-a-new-os-cb0f6986ba
purpose: 14 creating a new os
source: src/vibey_tools/skills/plugins/research-deep-dives/skills/linux-ubuntu-arch-fedora-macos-internals-research/SKILL.md
requires: ["skill-13-comparative-architecture-463771aae3"]
links: ["skill-15-programming-workflows-521e5ba9a5"]
---

## 14. Creating a new OS

### Educational kernel

Use QEMU and a cross-compiler. Implement boot entry, serial output, exceptions, page allocator, virtual memory, timer interrupts, interrupt controller, scheduler, context switching, user mode, syscalls, ELF loading, a filesystem, processes, IPC, and a shell. Start single-core and add SMP, preemption, drivers, and security deliberately.

### Linux-based OS

Reuse Linux and concentrate on kernel configuration, initramfs, rootfs, PID 1, services, package/update mechanism, security policy, image builder, installer, signing, rollback, and recovery. This becomes useful far sooner than a new kernel but still demands long-term security and release engineering.

### Microkernel/research OS

Keep scheduling, address spaces, IPC, and minimal hardware primitives in the kernel; move drivers, filesystems, networking, and services into user space. This can improve isolation but increases IPC, driver, ecosystem, and performance complexity.
