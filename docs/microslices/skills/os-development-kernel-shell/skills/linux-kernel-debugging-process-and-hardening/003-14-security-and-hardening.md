---
id: skill-14-security-and-hardening-434cf64a8e
purpose: 14 security and hardening
source: src/vibey_tools/skills/plugins/os-development-kernel-shell/skills/linux-kernel-debugging-process-and-hardening/SKILL.md
requires: ["skill-13-the-kernel-development-process-bdd52622a5"]
links: []
---

## §14. Security and Hardening

### 14.1 The kernel attack surface

**[DURABLE] Everything reachable from an unprivileged process is attack surface**: every
syscall, every ioctl, every `/proc` and `/sys` write, every netlink socket, every
filesystem parser (mounting an untrusted filesystem image is executing an untrusted
parser in ring 0), every network protocol, every driver bound to a device a user can
plug in. The kernel's size is its security problem.

Dominant bug classes, in the order they appear in CVEs: **use-after-free** (especially
refcount errors and races on teardown), **out-of-bounds read/write**, **race conditions /
double-free**, **integer overflow feeding a size calculation**, **type confusion**, and
**info leaks** (uninitialized kernel memory copied to userspace — always
`memset` structs you `copy_to_user`, and mind the padding).

### 14.2 The defenses

| Mechanism | What it does |
|---|---|
| **KASLR** / KPTI | Randomize kernel base; separate page tables (Meltdown) |
| **SMEP / SMAP** (x86), PAN/PXN (arm64) | Kernel can't execute or access user pages accidentally |
| **Stack protector**, `CONFIG_STACKLEAK` | Canaries; erase kernel stack on syscall return |
| **`CONFIG_FORTIFY_SOURCE`** | Compile-time and runtime bounds checks on str/mem functions |
| **`CONFIG_RANDSTRUCT`**, `CONFIG_STRUCTLEAK` | Randomize struct layout; zero-init |
| **CFI** (`CONFIG_CFI_CLANG`), arm64 **BTI/PAC**, x86 **IBT** | Control-flow integrity |
| **Lockdown LSM** | `integrity`/`confidentiality` modes: block `/dev/mem`, kexec of unsigned images, some BPF, some MSR writes, hibernation. **Auto-enabled under Secure Boot** |
| **Module signing** (`module.sig_enforce`) | Only signed modules load |
| **seccomp-bpf** | Per-process syscall filter. **The single most effective userspace sandbox primitive** |
| **LSMs**: SELinux, AppArmor, Smack, Tomoyo, **Landlock**, **BPF-LSM**, Yama, IMA/EVM | Mandatory access control. Stackable since 5.1 (`lsm=` on the cmdline) |
| **Landlock** | **Unprivileged** sandboxing — a process can restrict *itself* without root. Genuinely new capability |
| Namespaces + cgroups | Isolation and resource bounds (§7.3 → `linux-syscalls-ebpf-boot-and-init`) |

**Sysctls worth knowing** (`/proc/sys/kernel/`, `/proc/sys/net/`):
```
kernel.kptr_restrict=2            # hide kernel pointers from /proc
kernel.dmesg_restrict=1           # dmesg needs CAP_SYSLOG
kernel.perf_event_paranoid=3      # restrict perf
kernel.unprivileged_bpf_disabled=1
kernel.yama.ptrace_scope=1        # only ptrace descendants (2 = admin only)
kernel.io_uring_disabled=2        # see §4.3
kernel.kexec_load_disabled=1
user.max_user_namespaces=0        # if you don't need rootless containers
vm.mmap_min_addr=65536            # blocks NULL-deref exploit mapping
fs.protected_symlinks=1  fs.protected_hardlinks=1  fs.protected_fifos=2  fs.protected_regular=2
```

**[DURABLE] Reduce surface before adding mitigations.** Blocklist unused modules (Ubuntu
already does some of this), build a config with only what you need, disable unused
protocols and filesystems, and don't expose ioctls you don't need. A driver that isn't
compiled in cannot be exploited.

**Attack-surface note that catches people**: `modprobe` autoloading means an unprivileged
process opening a socket with an obscure protocol family can cause a rarely-audited module
to load. That's how several CVEs became reachable. `install <module> /bin/true` in
`/etc/modprobe.d/` blocks it.

### 14.3 Kernel hardening posture, honestly

- **Run a maintained LTS and take the point releases** (§13.3). This single practice
  beats every mitigation config in expected value.
- **Enable KASAN and lockdep in test, KFENCE in production.**
- **Use seccomp + an LSM for every service** — or use systemd's sandboxing options
  (§7.1 → `linux-syscalls-ebpf-boot-and-init`), which are seccomp and namespaces with a friendlier interface.
- **Threat-model before disabling things.** io_uring, user namespaces, and eBPF are all
  simultaneously large attack surfaces and genuinely valuable features. There is no
  universal right answer, only a right answer for your exposure.
