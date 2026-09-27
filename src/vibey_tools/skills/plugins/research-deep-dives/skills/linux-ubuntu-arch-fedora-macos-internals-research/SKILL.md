---
name: linux-ubuntu-arch-fedora-macos-internals-research
description: "Use when researching linux and macos internals: ubuntu, arch, fedora, and macos; this source-cited deep dive covers its concepts, evidence, practical trade-offs, and common errors."
---

# Linux and macOS Internals: Ubuntu, Arch, Fedora, and macOS

## Research brief

This reference explains how Linux-based operating systems and macOS work, how to program them, how to build distributions and images, and how to test software from user space through kernels and drivers.

Important distinctions:

- **Linux** is the kernel.
- **Ubuntu, Arch, and Fedora** are distributions: kernels, user space, package systems, defaults, security policy, release engineering, and documentation.
- **macOS** uses the partially open Darwin/XNU foundation plus proprietary Apple components, frameworks, drivers, firmware, graphics, and security infrastructure.
- An application, daemon, kernel module, driver, system extension, package, container, and VM are different engineering boundaries.

Commands are version-sensitive. Test bootloaders, kernels, filesystems, drivers, partitions, and security changes only in disposable VMs, snapshots, test disks, or systems with verified backups.

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

## 3. Linux languages and programming

You can program Linux in C, C++, Rust, Go, Zig, Swift, Fortran, Ada, Java, Kotlin, C#, Python, Ruby, Perl, JavaScript/TypeScript, shell, Lua, R, and many more. The stable boundary is the kernel ABI and user-space APIs, not a particular language.

Typical roles:

- C: libc, kernel-facing libraries, mature systems tooling, and established interfaces.
- C++: large systems, GUI toolkits, performance-sensitive code.
- Rust: memory-safe systems components and selected kernel/user-space projects.
- Go: services, networking, distributed systems, and CLI tools.
- Python/shell/Ruby/Perl: automation, administration, testing, and orchestration.
- Assembly: boot, ABI glue, context switching, SIMD, atomics, and hardware-specific work.

The build chain is preprocessing/macro expansion, compilation, assembly, linking, packaging, installation, and dynamic loading. Toolchains include GCC, Clang/LLVM, binutils, Make, Ninja, CMake, Meson, Cargo, Go tooling, and language package managers.

A serious build records compiler, SDK, flags, target architecture, dependency versions, source revision, generated files, locale, and timestamps. Use warnings, sanitizers, static analysis, dependency audits, signed artifacts, and reproducible-build checks.

## 4. Kernel programming

Kernel code must obey context and lifetime rules: interrupt versus process context, sleeping versus atomic context, locking order, memory barriers, RCU, reference counting, user-copy validation, DMA, cache coherence, and resource cleanup. There is no ordinary floating point in normal kernel paths.

A minimal educational module:

```c
#include <linux/init.h>
#include <linux/module.h>
static int __init example_init(void) { pr_info("loaded\\n"); return 0; }
static void __exit example_exit(void) { pr_info("unloaded\\n"); }
module_init(example_init);
module_exit(example_exit);
MODULE_LICENSE("GPL");
```

Build against the target kernel’s build tree using kbuild; test in a VM; inspect with `modinfo`, `dmesg`, `journalctl -k`, and `lsmod`. Modules depend on kernel configuration, compiler ABI, symbol versions, architecture, signing, lockdown, and distribution policy.

### Kernel source workflow

```sh
git clone https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git
cd linux
make mrproper
make O=../linux-build olddefconfig
make O=../linux-build -j"$(nproc)"
make O=../linux-build modules
```

Use a known distribution configuration when testing hardware. Verify kernel, modules, initramfs, boot entry, signatures, and rollback before rebooting.

Kernel testing includes KUnit, kselftest, LTP, syzkaller, lockdep, KASAN, KMSAN, UBSAN, KFENCE, kmemleak, fault injection, stress, QEMU/KVM, performance regression, and real-hardware testing. A booting kernel is not necessarily a correct kernel.

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

## 6. Ubuntu

Ubuntu combines upstream Linux with Debian-derived packaging, Canonical integration, release engineering, installers, security maintenance, and distribution defaults. Official architectures include amd64, arm64, armhf, ppc64el, s390x, and riscv64, with release-specific support. [Ubuntu supported architectures](https://ubuntu.com/project/docs/how-ubuntu-is-made/concepts/supported-architectures/)

### APT/dpkg

Ubuntu primarily uses Debian packages. APT resolves repository metadata and dependencies; dpkg unpacks/configures individual packages.

```sh
apt update
apt policy package
apt show package
apt install package
apt source package
apt build-dep package
dpkg -L package
dpkg -S /path/to/file
```

Repository metadata and source configuration are version-sensitive; modern Ubuntu releases use deb822 sources in `/etc/apt/sources.list.d/*.sources`. [Ubuntu package management](https://ubuntu.com/server/docs/how-to/software/package-management/)

Snaps are a separate package/distribution mechanism with revisions, channels, confinement, and transactional refresh behavior. A deb, Snap, container, and source build have different integration and update semantics.

### Ubuntu kernel and package development

Canonical maintains multiple kernel trees and variants. The Ubuntu `linux` source can produce differently configured binaries such as generic and low-latency kernels. Canonical documents source access, builds, module rebuilds, testing, and kernel-team workflows. [Ubuntu kernel variants](https://ubuntu.com/kernel/docs/reference/ubuntu-kernels/) and [Ubuntu kernel how-to guides](https://ubuntu.com/kernel/docs/how-to/)

For packages use source packages, `debuild`/dpkg-buildpackage, clean `sbuild`-style environments, autopkgtest, linting, upgrade tests, systemd units, documentation, and explicit removal/conffile behavior.

Boot commonly involves UEFI, a signed shim or equivalent, GRUB or a unified kernel image, kernel, initramfs, and root filesystem. Secure Boot, AppArmor, systemd, capabilities, namespaces, and seccomp form overlapping security layers.

## 7. Arch Linux

Arch is a rolling distribution emphasizing upstream-oriented packages, pacman, PKGBUILDs, systemd, and administrator control.

### pacman and PKGBUILD

A PKGBUILD is a Bash build recipe containing source retrieval, checksums, dependencies, build steps, and packaging. `makepkg` creates a compressed package; `pacman` installs and tracks it. Arch recommends clean chroots because dirty build environments can create unrepeatable dependencies and runtime behavior. [Arch Build System](https://wiki.archlinux.org/title/Arch_Build_System) and [Creating packages](https://wiki.archlinux.org/title/Creating_packages)

```sh
sudo pacman -S --needed base-devel git devtools
pkgctl repo clone --protocol=https package-name
cd package-name
makepkg --verifysource
makepkg -s
makepkg --clean
sudo pacman -U package-name-*.pkg.tar.zst
```

Read PKGBUILDs before execution: they run shell code. Build as a normal user. Use a clean chroot for reliable packages. Treat AUR recipes as code to audit, not as equivalent to signed official packages.

### Arch kernels and images

Arch can reuse the official Linux PKGBUILD, alter configuration or patches, build with makepkg, install kernel and headers, regenerate initramfs, and add bootloader entries. Arch warns custom kernels can cause instability or data loss. [Arch kernel build system](https://wiki.archlinux.org/title/Kernel/Arch_build_system)

Unified kernel images combine a UEFI stub, kernel, initramfs, and resources in a PE file. Boot configuration, microcode, initramfs generation, signing, and firmware behavior all matter.

## 8. Fedora

Fedora is an upstream-oriented distribution ecosystem with RPM, DNF, systemd, SELinux, signed packages, rapid releases, Workstation/Server/IoT and image variants.

### RPM/DNF

RPM packages contain metadata, payloads, dependencies, scripts, and signatures. Spec files describe source, build, files, dependencies, and scriptlets. `rpmbuild`, `rpmdevtools`, `mock`, `fedpkg`, and DNF are central tools.

```sh
sudo dnf install rpmdevtools rpm-build
rpmdev-setuptree
rpmbuild -ba SPECS/example.spec
rpm -qpi RPMS/.../example.rpm
rpm -qpl RPMS/.../example.rpm
```

Use clean mock or Fedora build infrastructure; do not build packages as root. Test upgrades, scriptlets, SELinux labels, systemd activation, and file ownership.

### Kernel and images

Fedora’s custom-kernel workflow uses Fedora source/spec trees, `fedpkg`, build dependencies, `pesign`, and `grubby`; official builds are signed through controlled infrastructure. [Fedora custom kernel](https://fedoraproject.org/wiki/Docs/CustomKernel)

Fedora image workflows produce ISOs, QCOW2, raw images, OSTree commits, or root filesystems using tools including KIWI, image-builder, mkosi, and lorax depending on the variant. [Building Fedora](https://fedoraproject.org/wiki/Building_a_Fedora)

### SELinux

SELinux enforces policy through labels, domains, types, transitions, and allowed operations.

```sh
getenforce
ausearch -m AVC -ts recent
ls -Z path
restorecon -Rv path
```

Do not blindly paste `audit2allow` output. Understand the denied operation, correct labels and service design, and write the narrowest policy needed.

## 9. Shared Linux testing

Test at multiple levels:

1. Static: formatting, warnings, type checking, lint, dependency and policy checks.
2. Unit: parsers, libraries, state machines, and KUnit.
3. Component: syscalls, drivers, package scripts, services, and filesystems.
4. Integration: IPC, storage, networking, graphics/session, upgrades.
5. System: boot, install, encryption, Secure Boot, suspend/resume, graphics, recovery.
6. Adversarial: fuzzing, malformed input, races, privilege boundaries, resource exhaustion, fault injection.
7. Performance: latency, throughput, CPU, memory, energy, I/O, boot time.

Use QEMU/KVM, libvirt, containers, chroots, systemd-nspawn, snapshots, network namespaces, loopback filesystems, and real hardware. Containers share the host kernel; use a VM to test a new kernel.

Useful tools:

```sh
uname -a; cat /proc/cmdline; cat /proc/version
lspci -nnk; lsusb -t; findmnt; ss -tulpn
strace -f -o trace.log command
perf stat command
perf record -g command
vmstat 1; iostat -xz 1
```

Use gdb for user-space debugging, perf/eBPF for profiling and tracing, tcpdump/Wireshark for networks, crash reports and kernel logs for failures, and sanitizers for memory/undefined behavior.

## 10. Creating a Linux distribution

There are four common meanings:

1. **Remaster:** customize an existing ISO/image with packages, defaults, policy, branding, and installer settings.
2. **Root filesystem:** build a package-managed root using tools such as debootstrap/mmdebstrap, dnf installroot/mock, or pacstrap.
3. **Appliance/image:** compose ISO, QCOW2, raw disk, container, OSTree, or embedded image with boot, partitioning, encryption, signing, updates, and recovery.
4. **From source:** bootstrap toolchain/libc, kernel, userland, packages, repositories, signatures, release tests, and security maintenance.

A viable distribution needs kernel/initramfs, root filesystem, PID 1, libc, shell/core utilities, device management, network/time/logging/certificates, users/permissions, package manager, signed repositories, installer/image builder, upgrades, rollback, recovery, vulnerability response, documentation, build farm, and mirrors.

“Compiled successfully” is not “supported.” Define ABI, hardware, boot, filesystem, upgrade, security, performance, and recovery guarantees.

## 11. macOS architecture

macOS is built on Darwin/XNU plus proprietary Apple components. Apple describes the kernel environment as Mach, BSD, I/O Kit, filesystems, and networking. Darwin does not include proprietary graphics and application layers such as Cocoa and Quartz. [Apple kernel architecture overview](https://developer.apple.com/library/archive/documentation/Darwin/Conceptual/KernelProgramming/Architecture/Architecture.html)

### Mach, BSD, and I/O Kit

Mach manages processor resources, scheduling support, virtual memory, protection, tasks, threads, ports, messages, IPC, and pagers.

The BSD layer supplies processes, PIDs, signals, file descriptors, VFS/filesystems, sockets, networking, credentials, syscalls, and much of the POSIX environment. Apple notes it is primarily FreeBSD-derived but not identical. [Apple BSD overview](https://developer.apple.com/library/archive/documentation/Darwin/Conceptual/KernelProgramming/BSD/BSD.html)

Historically I/O Kit provided an object-oriented C++ driver framework built around families, nubs, services, matching, power, and device stacks. [Apple I/O Kit overview](https://developer.apple.com/library/archive/documentation/Darwin/Conceptual/KernelProgramming/IOKit/IOKit.html)

Modern macOS prefers user-space system extensions and DriverKit. Apple says DriverKit drivers and system extensions run in user space; kexts are restricted and should be used only where no equivalent exists. [Apple DriverKit/system extensions](https://developer.apple.com/system-extensions/) and [low-level implementation guidance](https://developer.apple.com/documentation/kernel/implementing_drivers_system_extensions_and_kexts)

### macOS languages

C/C++ remain important in XNU, Darwin, system libraries, legacy frameworks, tools, and DriverKit. Objective-C remains in Cocoa and older APIs. Swift is the primary modern application language. Assembly serves boot, ABI, synchronization, SIMD, and hardware-specific code. Shell, Python, Ruby, Perl, Go, Rust, and others can be installed for user-space work; their availability is not equivalent to a stable system component.

### Mach-O and user-space tools

macOS uses Mach-O rather than ELF. Universal binaries may contain arm64 and x86_64 slices. Useful inspection:

```sh
file program
otool -L program
otool -l program
dyld_info program
codesign -dvvv --entitlements :- program
spctl --assess --type execute program
nm -m program
vmmap pid-or-path
sample pid 5
fs_usage
log stream --level debug
```

Build with Xcode/clang/Swift toolchains and documented SDK frameworks. Use launchd property-list jobs for persistent services rather than assuming systemd.

## 12. macOS system extensions, security, and testing

System extensions include DriverKit, NetworkExtension, EndpointSecurity, and other specialized interfaces. They are delivered inside an app bundle, activated through SystemExtensions, and checked for signatures, identifiers, entitlements, and placement. DriverKit templates use C++ and an I/O Kit interface-generator header. Apple requires drivers inside `Contents/Library/SystemExtensions`. [DriverKit creation](https://developer.apple.com/documentation/driverkit/creating-a-driver-using-the-driverkit-sdk) and [installation](https://developer.apple.com/documentation/systemextensions/installing-system-extensions-and-drivers)

macOS security layers include code signing, Developer ID, notarization, Gatekeeper, App Sandbox, TCC privacy permissions, hardened runtime, entitlements, quarantine, SIP, and system-extension approval.

Apple’s notarization workflow requires signing, hardened runtime and appropriate entitlements for modern distributed software; `notarytool` is the current submission tool. [Apple notarization](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution)

Conceptual workflow:

```sh
xcodebuild archive ...
xcodebuild -exportArchive ...
codesign --verify --deep --strict --verbose=4 path
ditto -c -k --keepParent path artifact.zip
xcrun notarytool submit artifact.zip --wait
xcrun stapler staple path
spctl --assess --type execute --verbose=4 path
```

Test on clean macOS installations and both architectures where relevant. Test sleep/wake, hot plug, multiple users, privacy prompts, sandbox failure, update/uninstall, network loss, and code-signing/notarization behavior.

SIP protects system areas and unauthorized execution. Apple says it may need temporary disabling for certain low-level development, but it should be restored immediately. [Apple SIP guidance](https://developer.apple.com/documentation/security/disabling-and-enabling-system-integrity-protection)

## 13. Comparative architecture

| Area | Ubuntu/Arch/Fedora | macOS |
|---|---|---|
| Kernel | Upstream Linux plus distro configuration/patches | XNU: Mach/BSD/I/O Kit and Apple components |
| Public source | Broad upstream and distribution trees | Darwin/XNU portions; proprietary layers remain |
| Executable | ELF | Mach-O |
| Packages | deb/APT, Arch packages/pacman, RPM/DNF | App bundles, installer packages, Mac App Store |
| Services | Usually systemd | launchd and Apple service frameworks |
| Mandatory policy | SELinux/AppArmor/LSM, capabilities, namespaces, seccomp | SIP, TCC, sandbox, entitlements, signatures |
| Drivers | Kernel modules and Linux device subsystems | DriverKit/system extensions preferred; kexts restricted |
| Custom kernel | Normal but risky and distro-specific | Not a general supported replacement path |
| GUI | X11/Wayland plus GTK/Qt/etc. | Quartz/WindowServer/AppKit/SwiftUI |
| Update authority | Distribution repositories and administrator | Apple update/signing/notarization ecosystem |

## 14. Creating a new OS

### Educational kernel

Use QEMU and a cross-compiler. Implement boot entry, serial output, exceptions, page allocator, virtual memory, timer interrupts, interrupt controller, scheduler, context switching, user mode, syscalls, ELF loading, a filesystem, processes, IPC, and a shell. Start single-core and add SMP, preemption, drivers, and security deliberately.

### Linux-based OS

Reuse Linux and concentrate on kernel configuration, initramfs, rootfs, PID 1, services, package/update mechanism, security policy, image builder, installer, signing, rollback, and recovery. This becomes useful far sooner than a new kernel but still demands long-term security and release engineering.

### Microkernel/research OS

Keep scheduling, address spaces, IPC, and minimal hardware primitives in the kernel; move drivers, filesystems, networking, and services into user space. This can improve isolation but increases IPC, driver, ecosystem, and performance complexity.

## 15. Programming workflows

### User-space utility

Use standard streams and exit codes; handle permissions, signals, malformed input, temporary files, locale, and interruption. Unit-test logic, integration-test syscalls, package it for target distributions, and trace it in each launch context.

### Network service

Define protocol, authentication, authorization, timeouts, backpressure, logging, metrics, TLS, resource limits, systemd/launchd integration, upgrade, and recovery. Test packet loss, slow clients, malformed requests, partial writes, restart, clock skew, and credential rotation.

### Filesystem/storage tool

Define crash consistency, fsync, atomicity, permissions, xattrs, sparse files, quotas, encryption, snapshots, case sensitivity, and recovery. Test power loss with loopback images and fault injection.

### Driver/system extension

Document hardware protocol, interrupts/DMA, power states, hotplug, reset, concurrency, firmware, user API, entitlements, security boundaries, and recovery. Test disconnects, suspend/resume, resource exhaustion, concurrent opens, malformed devices, and no-network conditions.

### GUI application

Separate UI, model, I/O, and privileged operations. Test accessibility, localization, scaling, multiple displays, sleep/wake, sandbox/privacy prompts, corrupted data, crash recovery, update, and uninstall.

## 16. Reproducibility and release engineering

A serious OS project needs source tags, deterministic toolchains, dependency/license inventory, signed commits and artifacts, reproducible-build comparison, build logs, package repositories, update channels, rollback, vulnerability intake, hardware/VM matrices, upgrade tests, and recovery documentation.

Never put signing keys in source control. Never call an artifact supported merely because it compiled once.

## 17. Progressive curriculum

1. **User space:** C or Rust, memory, ownership/pointers, processes, threads, files, sockets, compilers, linkers, shell, Git, debugging. Build a shell and TCP server.
2. **Unix/Linux:** syscalls, proc/sysfs, file descriptors, signals, epoll, mmap, namespaces, cgroups, capabilities, systemd, packages, containers. Build and package a service for deb, RPM, and Arch.
3. **Kernel:** concurrency, memory ordering, interrupts, DMA, PCI/USB, device model, filesystems, networking, tracing, security. Build a module and QEMU test harness.
4. **Distribution:** image, repository, signed package, installer, updates, rollback, CI matrix; learn AppArmor, SELinux, Secure Boot, and image builders.
5. **macOS:** Mach-O, launchd, codesign, notarization, entitlements, sandbox/TCC, Instruments, Darwin/XNU, DriverKit, NetworkExtension, and EndpointSecurity.

## 18. Investigation checklist

When behavior differs across systems, record OS release, kernel/XNU version, architecture, hardware, executable format/slices, compiler/SDK/libc/runtime, exact package/source revision, environment, working directory, locale, limits, user/group/capabilities, sandbox/SELinux/AppArmor/SIP/TCC/entitlements, launch context, filesystem/mount flags/ACLs/xattrs, network path, logs, traces, crash reports, and whether failure is deterministic or hardware/timing-specific.

## 19. Myths and failure modes

- Ubuntu is not merely a theme on Linux; its kernel, packages, policy, release, and integration matter.
- Arch is not structureless; it delegates more decisions to the administrator.
- Fedora is not simply a beta; it has its own release, security, packaging, and image systems.
- macOS is not unknowable because it is partly closed; Darwin, XNU portions, tools, APIs, and observations are substantial, but proprietary boundaries are real.
- A kernel module is not an ordinary plugin.
- A container is not a VM; it shares the host kernel.
- A successful compile does not prove ABI, policy, hardware, signing, boot, upgrade, or runtime compatibility.
- Disabling security controls is not a general fix.
- A language does not make a system safe; interfaces, drivers, FFI, concurrency, provenance, and operations matter.

## Research note

Prepared 2026-09-27. This is a deep orientation and engineering roadmap, not a substitute for the current kernel, distribution, Apple SDK, driver, package, or security documentation for a specific release. Commands and policies change. The safest progression is user-space programming in VMs, then packaging and service development, then controlled kernel/driver work with source-backed tests and rollback.
