---
id: skill-2-linux-kernel-e506b9d569
purpose: 2 linux kernel
source: src/vibey_tools/skills/plugins/research-deep-dives/skills/volume-b-linux-macos-internals-deep-dive/SKILL.md
requires: ["skill-1-boot-and-initialization-6e057344a9"]
links: ["skill-3-processes-services-and-ipc-e1d6858daf"]
---

## 2. Linux kernel

The Linux kernel is primarily C plus architecture-specific assembly, with Rust increasingly used for selected components. It provides process and thread management, virtual memory, scheduling, system calls, signals, virtual filesystems, networking, drivers, block I/O, namespaces, cgroups, cryptography, security interfaces, tracing and eBPF.

A process has a virtual address space, credentials, file descriptors, signal state and scheduling attributes. Threads share much of an address space. A system call transitions through an architecture-specific ABI into kernel code. Interrupt, softirq, workqueue and process contexts have different constraints. Locking, memory ordering, RCU, reference counting and lifetime management are major sources of kernel bugs.

Virtual memory combines page tables, TLBs, anonymous and file-backed pages, mmap, copy-on-write, shared memory, huge pages, swap, page cache and reclaim. The VFS gives a common interface over ext4, XFS, Btrfs, tmpfs, procfs, sysfs, NFS and overlayfs. Durability also depends on ordering, journaling or copy-on-write, barriers, device caches, checksums, snapshots, encryption and tested recovery.

Sources: [Linux kernel documentation](https://docs.kernel.org/), [Linux kernel source](https://git.kernel.org/), [Linux man-pages](https://www.kernel.org/doc/man-pages/).
