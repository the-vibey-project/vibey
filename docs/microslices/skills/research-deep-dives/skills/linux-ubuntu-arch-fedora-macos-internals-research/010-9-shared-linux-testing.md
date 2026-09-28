---
id: skill-9-shared-linux-testing-b7f5917393
purpose: 9 shared linux testing
source: src/vibey_tools/skills/plugins/research-deep-dives/skills/linux-ubuntu-arch-fedora-macos-internals-research/SKILL.md
requires: ["skill-8-fedora-45ba7a30a8"]
links: ["skill-10-creating-a-linux-distribution-989269e9ff"]
---

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
