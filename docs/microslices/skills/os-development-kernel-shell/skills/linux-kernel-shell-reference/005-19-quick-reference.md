---
id: skill-19-quick-reference-2dd61e90a8
purpose: 19 quick reference
source: src/vibey_tools/skills/plugins/os-development-kernel-shell/skills/linux-kernel-shell-reference/SKILL.md
requires: ["skill-18-the-canon-9b5a2f6566"]
links: ["skill-20-sources-and-method-509813b24b"]
---

## §19. Quick Reference

### 19.1 Kernel numbers
- x86-64 kernel stack: **16 KB** (`THREAD_SIZE`), shared with IRQ frames on some configs.
- Page size: **4 KiB** typical; 2 MiB / 1 GiB huge pages; arm64 supports 4/16/64 KiB.
- `kmalloc` max: order-limited, a few MB — use `vmalloc` above that.
- Default `HZ`: 250 or 1000 (`CONFIG_HZ`); tickless (`NO_HZ_FULL`) for RT.
- `sched_rt_runtime_us`: **950000** of 1000000 µs — the RT throttle.
- Kernel release cadence: **~9–10 weeks**; merge window **2 weeks**; ~7 `rc`s.
- New LTS projected EOL: **~2 years**, extended on industry demand.

### 19.2 Diagnostic first moves
| Symptom | First command |
|---|---|
| System slow | `top` / `htop`, then `cat /proc/pressure/*` (PSI) |
| High iowait / D-state processes | `iostat -xz 1`, `biolatency`, `cat /proc/PID/stack` |
| Which syscalls | `strace -f -c -p PID` (dev only) or `bpftrace` |
| Where is CPU going | `perf top`, then `perf record -g` → flame graph |
| Kernel oops | `dmesg -T`, `journalctl -k -b -1`, `faddr2line` |
| Out of memory | `dmesg \| grep -i oom`, `/sys/fs/cgroup/*/memory.events` |
| Network | `ss -tanp`, `ip -s link`, `tcpdump`, `bpftrace` on tcp tracepoints |
| Disk full but `du` disagrees | `lsof +L1` (deleted-but-open files) |
| Module won't load | `dmesg`, `modinfo`, check signature + taint + kernel version |

### 19.3 Kernel patch checklist
- [ ] Builds clean with `W=1` and no new warnings
- [ ] `checkpatch.pl --strict` clean (or deviations justified)
- [ ] `make C=1` (Sparse) clean — especially `__user`/`__iomem` annotations
- [ ] Tested with KASAN + lockdep enabled
- [ ] Locking documented; no sleeping in atomic context
- [ ] All error paths unwind correctly (test them with fault injection)
- [ ] No `uapi` changes, or an explicitly compatible extension
- [ ] `Fixes:` tag if it's a fix; `Cc: stable@` if it should be backported
- [ ] Commit message explains **why**
- [ ] Sent as plain text to the right list per `get_maintainer.pl`

### 19.4 Shell script checklist
- [ ] `set -Eeuo pipefail` and `IFS=$'\n\t'`
- [ ] `shellcheck` clean
- [ ] Every expansion quoted; `"$@"` not `$@`
- [ ] `local` in every function
- [ ] `trap cleanup EXIT`; `mktemp` for temp files
- [ ] Required inputs validated with `${VAR:?}`
- [ ] Dependencies checked with `command -v`
- [ ] Logs to stderr, data to stdout, meaningful exit codes
- [ ] Idempotent, or documented as not
- [ ] Correct shebang for the features used; tested on the target's `/bin/sh` if POSIX

---
