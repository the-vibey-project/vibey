---
id: skill-15-anti-patterns-3b715e7079
purpose: 15 anti patterns
source: src/vibey_tools/skills/plugins/os-development-kernel-shell/skills/linux-kernel-shell-reference/SKILL.md
requires: []
links: ["skill-16-contested-questions-0ab2d6f525"]
---

## §15. Anti-Patterns

### 15.1 Kernel

| Anti-pattern | Why | Instead |
|---|---|---|
| `GFP_KERNEL` in atomic context | Sleeping under a spinlock/IRQ → deadlock | `GFP_ATOMIC`, or restructure |
| Large stack arrays / recursion | 16 KB stack, no guard in older configs | `kmalloc`, iteration |
| `volatile` for concurrency | Provides neither atomicity nor ordering | `READ_ONCE`/`WRITE_ONCE` + locks/barriers |
| `atomic_t` for reference counts | No overflow/UAF detection | **`refcount_t`** |
| Manual `kfree` in a driver probe path | Leaks on every error branch | **`devm_*`** |
| Inconsistent lock ordering | Deadlock, found in production | Document + lockdep |
| Floating point in kernel | FPU state not saved | Fixed point; or `kernel_fpu_begin/end` if you truly must |
| Dereferencing `__user` pointers | Bug and security hole | `copy_from_user` + Sparse (`make C=1`) |
| Reading a userspace value twice | TOCTOU → privesc | Copy once, validate the copy |
| `copy_to_user` of an unzeroed struct | Info leak via padding | `memset` first |
| Ignoring `-EPROBE_DEFER` | Spinning or failing on a not-yet-ready dependency | Return it |
| Busy-waiting in a driver | Burns a CPU | `wait_event`, completions, threaded IRQ |
| New `/proc` file for arbitrary data | Wrong interface, becomes ABI | sysfs (stable) or debugfs (unstable) |
| Changing a `uapi` struct | Breaks userspace forever | New syscall/flag; size-and-flags pattern |
| Out-of-tree module as a long-term plan | No stable ABI; DKMS forever | Upstream it |
| Shipping on a non-LTS kernel | EOL in ~10 weeks | Anchor to LTS |

### 15.2 Shell

| Anti-pattern | Why | Instead |
|---|---|---|
| Unquoted `$var` | Word splitting + globbing → wrong files | `"$var"` |
| Parsing `ls` | Breaks on spaces, newlines, glob chars | Globs, `find -print0` |
| `rm -rf $DIR/` | Empty/typo'd var → catastrophe | `set -u` + `"${DIR:?}"` |
| Relying on `set -e` alone | Full of exceptions (§8.2 → `linux-shell-scripting-and-userland`) | Check returns that matter |
| `cd dir; do_thing` | `cd` can fail | `cd dir \|\| exit 1` |
| Predictable `/tmp/file.$$` | Symlink attack | `mktemp` |
| `cmd \| while read` expecting side effects | Subshell in bash | `while read … done < <(cmd)` |
| Bash-isms in `#!/bin/sh` | `/bin/sh` is dash/ash on many systems | `#!/usr/bin/env bash`, or write POSIX |
| Cleanup code at the end of the script | Skipped on error/signal | `trap cleanup EXIT` |
| Missing `local` in functions | Global by default; corrupts caller | `local` everything |
| `echo` for arbitrary data | Interprets escapes inconsistently across shells | `printf '%s\n'` |
| Data on stdout mixed with logs | Breaks composition | Logs to stderr |
| A 900-line bash script | Unmaintainable, untestable | Python at ~200 lines |
| No `shellcheck` | Every quoting bug is mechanically detectable | Run it in CI |
| `sudo` inside a script without checking | Prompts mid-run, or runs unexpectedly as root | Check `EUID`, fail fast |

---
