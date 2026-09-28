---
id: skill-16-contested-questions-0ab2d6f525
purpose: 16 contested questions
source: src/vibey_tools/skills/plugins/os-development-kernel-shell/skills/linux-kernel-shell-reference/SKILL.md
requires: ["skill-15-anti-patterns-3b715e7079"]
links: ["skill-17-currency-snapshot-verified-august-2026-2d5bd2992a"]
---

## §16. Contested Questions

**16.1 Rust in the kernel.** §2.6 → `linux-kernel-architecture-and-code`. Settled as policy, unsettled as social reality.

**16.2 The CVE flood.** §13.3 → `linux-kernel-debugging-process-and-hardening`. Honest-but-unusable vs. dishonest-but-triageable.

**16.3 systemd.** §7.1 → `linux-syscalls-ebpf-boot-and-init`.

**16.4 io_uring: performance vs. attack surface.** §4.3 → `linux-syscalls-ebpf-boot-and-init`. The unusual feature of this
argument is that both sides cite the same evidence — it *is* fast and it *has* produced a
disproportionate share of exploitable bugs.

**16.5 Monolithic vs. microkernel.** The oldest argument in the field (Tanenbaum–Torvalds,
1992). Linux won commercially and decisively; the microkernel case (fault isolation,
formal verifiability — seL4 has a machine-checked proof) remains technically strong and is
where safety-critical systems actually go. Note the irony that Linux has been steadily
absorbing microkernel-ish ideas: FUSE, uio/vfio userspace drivers, and eBPF are all "run
this in a constrained context instead of ring 0."

**16.6 Stable in-kernel ABI.** *For:* out-of-tree drivers wouldn't need constant
rebuilding; vendors could ship binaries. *Against (the kernel's position, in
`Documentation/process/stable-api-nonsense.rst`):* a stable internal ABI freezes bad
designs forever, prevents whole-tree refactoring, and the correct answer is to upstream
your driver — at which point someone else fixes it for you when the interface changes.
This is settled in the kernel and permanently contested by hardware vendors.

**16.7 bcachefs's removal.** §17. A dispute about development process, not about the
filesystem's technical merit — which is generally acknowledged.

**16.8 Which shell.** §9.3 → `linux-shell-scripting-and-userland`. Genuinely low-stakes for interactive use, genuinely
high-stakes for scripts, and people persistently conflate the two.

**16.9 `set -e`.** Some argue it's essential defensive practice; others (the BashFAQ 105
position) that its exception list makes it actively misleading and that explicit error
checking is the only honest approach. Both camps write correct scripts; neither writes
them by relying on `set -e` alone.

---
