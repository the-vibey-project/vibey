---
id: skill-2-linux-internals-e407509031
purpose: 2 linux internals
source: src/vibey_tools/skills/plugins/research-deep-dives/skills/linux-ubuntu-arch-fedora-macos-internals-research/SKILL.md
requires: ["skill-1-universal-os-model-caec6f7213"]
links: ["skill-3-linux-languages-and-programming-68a24d3393"]
---

## 2. Linux internals

Linux is primarily a monolithic but modular kernel. Most core services run in kernel space; drivers and features may be built in or loaded as modules. Linux also supplies namespaces, cgroups, eBPF, KVM, virtual filesystems, user-space filesystem support, security modules, and many tracing facilities.

The kernel is written mostly in C, with architecture-specific assembly. Rust is now used for selected kernel work, but it does not replace the C/assembly foundation. [Linux kernel development HOWTO](https://cdn.kernel.org/doc/html/latest/process/howto.html)

### Major subsystems

- **Architecture:** boot, exceptions, system-call entry, context switching, atomics, page tables, interrupt controllers, and CPU topology.
- **Scheduler:** runnable tasks, priorities, CPU affinity, load balancing, real-time classes, cgroups, and power behavior.
- **Memory management:** virtual memory, page cache, reclaim, slab allocators, NUMA, huge pages, copy-on-write, cgroups, and swap.
- **VFS:** common file operations over ext4, XFS, Btrfs, tmpfs, procfs, sysfs, NFS, FUSE, overlayfs, and other filesystems.
- **Block layer:** queued storage I/O, NVMe, SCSI, device mapper, RAID, and filesystem integration.
- **Networking:** sockets, routing, netfilter, traffic control, namespaces, protocol stacks, drivers, and eBPF.
- **Drivers:** PCI, USB, I2C, SPI, GPIO, input, DRM/KMS graphics, media, sound, serial, Bluetooth, Wi-Fi, storage, and sensors.
- **Security:** credentials, capabilities, LSM hooks, seccomp, keyrings, integrity measurement, module signing, namespaces, and audit.
- **Virtualization:** KVM, virtio, vhost, VFIO, namespaces, and cgroups.
- **Observability:** printk, tracepoints, ftrace, perf, eBPF, kprobes, lockdep, crash dumps, and sanitizers.

### Syscalls and executable formats

Linux programs use system calls such as `openat`, `read`, `write`, `mmap`, `clone`, `execve`, `futex`, `epoll`, `io_uring`, `socket`, `connect`, and `ioctl`. libc wraps many but not all syscalls. glibc, musl, and other libcs are user-space choices; the kernel does not require glibc.

ELF is the normal Linux executable/object format. The dynamic linker maps shared libraries, resolves symbols, applies relocations, and starts the program. ABI compatibility depends on architecture, libc, symbol versions, syscall behavior, compiler ABI, and distribution policy.

### Process and service mechanics

Linux uses `fork`, `execve`, `clone`, and `clone3` to create and configure processes and threads. Processes have address spaces, credentials, files, signals, namespaces, cgroups, and resource limits. Threads share selected process resources. Synchronization uses atomics, mutexes, futexes, condition variables, semaphores, pipes, sockets, eventfd, epoll, and io_uring.

Signals are asynchronous notifications; child exit status is collected with `wait*`; orphaned processes are reparented to PID 1 or a subreaper.

On current Ubuntu, Arch, and Fedora installs, systemd commonly supplies PID 1 and service management. Units include services, sockets, timers, mounts, targets, devices, swaps, paths, and slices. Dependencies, ordering, cgroups, journaling, socket activation, and sandbox directives are separate concepts.

Useful inspection:

```sh
systemctl status name.service
journalctl -u name.service -b
systemd-analyze critical-chain
systemd-cgls
ps auxww
ss -tulpn
```
