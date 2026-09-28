---
id: skill-11-macos-architecture-5d8323ef3a
purpose: 11 macos architecture
source: src/vibey_tools/skills/plugins/research-deep-dives/skills/linux-ubuntu-arch-fedora-macos-internals-research/SKILL.md
requires: ["skill-10-creating-a-linux-distribution-989269e9ff"]
links: ["skill-12-macos-system-extensions-security-and-testing-ffe1d44418"]
---

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
