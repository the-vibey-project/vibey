---
id: skill-17-currency-snapshot-verified-august-2026-2d5bd2992a
purpose: 17 currency snapshot verified august 2026
source: src/vibey_tools/skills/plugins/os-development-kernel-shell/skills/linux-kernel-shell-reference/SKILL.md
requires: ["skill-16-contested-questions-0ab2d6f525"]
links: ["skill-18-the-canon-9b5a2f6566"]
---

## §17. Currency Snapshot — verified August 2026

| Thing | Status as of Aug 2026 | Decay risk |
|---|---|---|
| **Kernel mainline** | **7.1.9** (19 Aug 2026); 7.2-rc in flight. **7.0 released 12 April 2026** after 6.19; major number carries no semantic meaning. **7.0 already EOL (27 June 2026)** | **High** |
| **Kernel LTS** | 5.10, 5.15, 6.1, 6.6, 6.12, **6.18**. GKH **extended 6.6/6.12/6.18 in Feb 2026**; 6.18 → at least **Dec 2028**. ⚠️ **5.10 and 5.15 EOL 31 Dec 2026** | Medium |
| **Rust for Linux** | **Experimental label removed in 7.0.** First-class language; coexistence policy formalized at the 2025 Tokyo Maintainers Summit (Rust for new code, C stays, no forced migration). Stable-Rust-only builds, min ~1.93. Kernel Rust API covers PCI enumeration, IRQ, DMA mapping, platform device registration. **Graphics subsystem to accept only Rust for new drivers** (GKH, OSS India, July 2026) | Medium |
| **PREEMPT_RT** | **Mainlined in 6.12** (Sept 2024): x86, arm64, RISC-V | Low |
| **sched_ext** | Merged **6.12**. `scx` schedulers (`scx_rusty`, `scx_lavd`, `scx_bpfland`, `scx_layered`) in production at Meta. SCX-enabled kernels default on Fedora/Arch/CachyOS/NixOS/openSUSE TW; Ubuntu 26.04 HWE only; Debian stable needs backports | Medium |
| **EEVDF** | Fair-class scheduler since 6.6 (replaced CFS) | Low |
| **bcachefs** | ⚠️ Marked "externally maintained" **Aug 2025**; **removed from the tree entirely in 6.18** ("It's now a DKMS module, making the in-kernel code stale"). Ships as DKMS; tools v1.38.6 (June 2026) dropped the "experimental" label. Root-fs use requires an initramfs that loads the module | Medium |
| **Kernel CVEs** | kernel.org is a CNA since Feb 2024; ~50 CVEs/week, **no severity scores**; **432 published in <48h in July 2026**. Largest CVE issuer in existence | **High** |
| **EU CRA** | Vulnerability/incident **reporting obligations start 11 Sept 2026**; full application 11 Dec 2027. The kernel is a component in your SBOM | **Imminent** |
| **io_uring** | ~60% of Google VRP kernel exploit submissions; ~$1M paid in io_uring bounties. Disabled in ChromeOS, restricted on Android, blocked by containerd's default seccomp profile. Published io_uring-only rootkit evades syscall monitoring. `kernel.io_uring_disabled=2` to disable | Medium |
| **systemd** | **v261** current; **v258** removed cgroup v1 and SysV runlevels; **v259** deprecated SysV scripts, made journald persistent by default, dropped iptables NAT for nftables; **v260 (March 2026) removed SysV generators entirely**; v260 raises minimums (kernel 5.10, glibc 2.34, OpenSSL 3.0, Python 3.9) | Medium |
| **bash** | **5.3** (3 July 2025) — first release in 3 years. `${ cmd; }` / `${\| cmd; }` non-forking command substitution, `GLOBSORT`, `source -p`, no fork for `&&`/`\|\|` RHS, C23 conformance. Readline 8.3. ⚠️ **macOS still ships 3.2** | Low |
| **zsh** | **5.9.1** (31 May 2026). macOS default since Catalina | Low |
| **fish** | **4.7** (May 2026); Rust rewrite since 4.0 (Feb 2025). Non-POSIX by design | Medium |
| **nushell** | Past **0.111**, still pre-1.0. Structured-data pipelines | High |
| **POSIX** | **POSIX.1-2024 / Base Specifications Issue 8 / SUSv5**, published 14 June 2024. Aligned with C17. ⚠️ **`test -a`/`-o` removed**; `gettimeofday()` removed; new "intrinsic utilities" category. First technical corrigendum in progress | Low |
| **Shell usage** | Bash/shell scripting at **49% of developers** (SO 2025 survey), 5th overall, ahead of TypeScript. Fish ~7% among developers | Annual |
| **Distro userland** | Ubuntu shipping **uutils** (Rust coreutils) — behavioural differences from GNU are a new source of portability surprises | Medium |

**Goes stale fastest:** kernel version numbers and LTS EOL dates; CVE volume; Rust
subsystem policy; nushell. **Essentially never stale:** §1 → `linux-kernel-architecture-and-code` (architecture), §3 → `linux-kernel-architecture-and-code`
(concurrency), §4.1 → `linux-syscalls-ebpf-boot-and-init` (the ABI contract), §8 → `linux-shell-scripting-and-userland` (shell semantics), §10 → `linux-shell-scripting-and-userland` (defensive scripting),
§15 (anti-patterns).

---
