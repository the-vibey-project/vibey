---
id: skill-0-routing-18ce400993
purpose: 0 routing
source: src/vibey_tools/skills/plugins/os-development-kernel-shell/skills/linux-kernel-architecture-and-code/SKILL.md
requires: []
links: ["skill-1-kernel-architecture-23112f1bb4"]
---

## §0. Routing

### 0.1 What kind of OS work is this?

| Task | Where it lives | Language | Risk if wrong |
|---|---|---|---|
| Observe the system | eBPF, ftrace, perf | BPF C / bpftrace | Low — verifier catches most of it |
| Change scheduling policy | **sched_ext** BPF scheduler | BPF C / Rust | Low — kernel reverts to fair class on error |
| Drive new hardware | Kernel module / driver | C or **Rust** | High — oops, corruption |
| Add a syscall or change ABI | Core kernel | C | **Permanent.** You can never take it back |
| New filesystem | fs/ | C | Data loss |
| Userspace init/service | systemd unit, D-Bus | Config / any | Medium |
| Automate a system task | Shell / Python | bash, POSIX sh | **Very high** — `rm -rf "$UNSET/"` |
| Build a distro / image | Yocto, Buildroot, mkosi | Recipes | Medium |
| Harden a system | sysctl, LSM, seccomp, lockdown | Config | Medium |

**[DURABLE] Before writing kernel code, ask whether you can do it in userspace or in
BPF instead.** The kernel community asks this first and so should you. A driver that
could be a `uio`/`vfio` userspace driver, a filesystem that could be FUSE, a monitor that
could be eBPF — all are better engineering *and* faster to ship, because they don't
require review by a maintainer who has been burned a thousand times.

### 0.2 The question router

| Asked about... | Go to |
|---|---|
| What is the kernel actually doing? Processes, scheduling, memory, VFS | §1 |
| Writing kernel code — modules, drivers, C idioms, Rust | §2 |
| Locking, RCU, memory barriers, per-CPU, preemption | §3 |
| Syscalls, the ABI, "don't break userspace", vDSO | §4 → `linux-syscalls-ebpf-boot-and-init` |
| eBPF, sched_ext, tracing programs | §5 → `linux-syscalls-ebpf-boot-and-init` |
| Boot: firmware → bootloader → initramfs → init | §6 → `linux-syscalls-ebpf-boot-and-init` |
| systemd, units, cgroups, namespaces, containers | §7 → `linux-syscalls-ebpf-boot-and-init` |
| Shell semantics — word splitting, quoting, expansion | §8 → `linux-shell-scripting-and-userland` |
| Bash vs zsh vs fish vs nushell; which to use | §9 → `linux-shell-scripting-and-userland` |
| Writing shell that doesn't destroy things | §10 → `linux-shell-scripting-and-userland` |
| The userland: coreutils, text processing, process tools | §11 → `linux-shell-scripting-and-userland` |
| Debugging: ftrace, perf, KASAN, crash, printk | §12 → `linux-kernel-debugging-process-and-hardening` |
| Kernel dev process: patches, maintainers, stable, CVEs | §13 → `linux-kernel-debugging-process-and-hardening` |
| Security: LSM, seccomp, lockdown, hardening, attack surface | §14 → `linux-kernel-debugging-process-and-hardening` |
| "Don't do this" | §15 → `linux-kernel-shell-reference` |
| "Which is better, X or Y?" | §16 → `linux-kernel-shell-reference` (contested) |
| "Is this still current?" | §17 → `linux-kernel-shell-reference` |
| Books, docs, people | §18 → `linux-kernel-shell-reference` |

---
