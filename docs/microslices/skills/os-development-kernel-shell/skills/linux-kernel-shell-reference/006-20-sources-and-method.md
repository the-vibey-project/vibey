---
id: skill-20-sources-and-method-509813b24b
purpose: 20 sources and method
source: src/vibey_tools/skills/plugins/os-development-kernel-shell/skills/linux-kernel-shell-reference/SKILL.md
requires: ["skill-19-quick-reference-2dd61e90a8"]
links: []
---

## §20. Sources and Method

**Method.** Narrative (not systematic) review. Durable material — §1 → `linux-kernel-architecture-and-code` (architecture),
§3 → `linux-kernel-architecture-and-code` (concurrency), §4.1 → `linux-syscalls-ebpf-boot-and-init` (the ABI contract), §8 → `linux-shell-scripting-and-userland` (shell semantics), §10 → `linux-shell-scripting-and-userland` (defensive
scripting), §12 → `linux-kernel-debugging-process-and-hardening` (debugging technique), §15 (anti-patterns) — is synthesized from the
kernel's own documentation, the POSIX specification, and the canonical texts in §18.
Every **time-sensitive** claim (versions, EOL dates, feature status, policy changes) was
verified against a primary or near-primary source in **August 2026** and is flagged in
§17 with a decay-risk rating. Where the kernel community itself disagrees, §16 presents
both cases rather than adjudicating.

**Search log** (August 2026): Linux kernel current version and LTS support timelines ·
Rust for Linux status after 7.0 · bash/zsh/fish/nushell versions and adoption · bash 5.3
features · eBPF and sched_ext status · Linux kernel CNA and CVE volume · bcachefs removal
· POSIX.1-2024 / Issue 8 · systemd v258–v261 changes · io_uring security posture.

**Primary and near-primary sources consulted (selected):**
- kernel.org releases and **docs.kernel.org** — `scheduler/sched-ext.rst`, `bpf/verifier`,
  `process/cve.rst`
- **LWN.net** — bcachefs removal; systemd v258/v259 highlights; kernel CVE assignment
  process; bash-5.3 release
- **Greg Kroah-Hartman** — `kroah.com/log` on the Linux CVE assignment process; LTS
  extension announcements; Open Source Summit India keynote coverage (July 2026)
- **Rust for Linux** project site and kernel Rust policy documentation
- **Phoronix** — Linux 7.0 driver core / Rust; bcachefs "externally maintained"; systemd
  259; Google restricting io_uring
- **The Open Group** — Base Specifications Issue 8 (POSIX.1-2024); IEEE 1003.1-2024
- **GNU** — bash release announcement and `NEWS`/`CHANGES` (Chet Ramey), bash home page
- **systemd** GitHub release notes v258 / v259
- **Google Security Blog** coverage of kCTF VRP io_uring findings (via Phoronix and
  contemporaneous reporting); ARMO io_uring rootkit disclosure
- **The Register** — "Linux kernel team publishes 432 CVEs in two days" (July 2026)
- European Commission — Cyber Resilience Act reporting obligations

**Confidence statement.** **High confidence** in §1–§8 → `linux-kernel-architecture-and-code`, `linux-shell-scripting-and-userland`, §10–§15 → `linux-shell-scripting-and-userland`, §18–§19 — these rest on
kernel documentation, the POSIX standard, and long-established practice. **High
confidence** in §17's verified items as of the stated date. **Moderate confidence** in the
2026 Rust-policy specifics (§2.6 → `linux-kernel-architecture-and-code`) and the sched_ext distro-status details (§5.2 → `linux-syscalls-ebpf-boot-and-init`) — these
rest partly on conference reporting and practitioner blogs rather than primary project
documentation, and subsystem-level policy in particular is being decided maintainer by
maintainer rather than by a single announcement. Where a figure comes from a vendor's own
program (Google's VRP payout percentages in §4.3 → `linux-syscalls-ebpf-boot-and-init`), it is attributed as such; the direction
of that evidence is much more reliable than its precision.
