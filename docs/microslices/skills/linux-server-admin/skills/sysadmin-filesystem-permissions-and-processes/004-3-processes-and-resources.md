---
id: skill-3-processes-and-resources-69096eaf8e
purpose: 3 processes and resources
source: src/vibey_tools/skills/plugins/linux-server-admin/skills/sysadmin-filesystem-permissions-and-processes/SKILL.md
requires: ["skill-2-users-permissions-capabilities-4d0880b5e5"]
links: []
---

## §3. Processes and Resources

**States**: R (running/runnable), S (interruptible sleep), **D (uninterruptible sleep —
⚠️ usually blocked on I/O, and cannot be killed; a pile of D-state processes means a
storage problem)**, Z (zombie — ⚠️ **exited, parent hasn't reaped; harmless unless
numerous, and the fix is fixing or restarting the parent**), T (stopped).

**Signals worth knowing**:
```
SIGTERM (15)  ⚠️ polite: "shut down" — catchable, the default for kill and systemd
SIGKILL  (9)  ⚠️ uncatchable, no cleanup — data loss risk, use last
SIGHUP   (1)  traditionally "reload config"
SIGINT   (2)  Ctrl-C
SIGSTOP/SIGCONT  pause/resume
SIGUSR1/2     application-defined (⚠️ nginx: reopen logs / graceful)
```
**⚠️ `kill -9` as a first move is a bad habit.** It skips flush-and-close. Try TERM, wait,
then KILL.

**Load average** is **runnable + uninterruptible (D-state)** processes averaged over
1/5/15 min. ⚠️ **Because D-state counts, high load on Linux can mean I/O wait, not CPU
saturation — this differs from other Unixes and is a persistent source of misdiagnosis.**
**Divide by core count for a rough utilization read.**

**Limits**: `ulimit -a` for the shell, ⚠️ **`/proc/PID/limits` for reality**, and
`LimitNOFILE=` etc. in unit files for services (§4.3 → `sysadmin-systemd-storage-and-networking`).

**⚠️ The OOM killer**: when memory is exhausted, the kernel picks a victim by `oom_score`.
Check `dmesg | grep -i oom` or `journalctl -k | grep -i oom`. **Tune with
`oom_score_adj`; in systemd, `OOMScoreAdjust=` and `MemoryMax=`.** ⚠️ **Overcommit
(`vm.overcommit_memory`) means malloc can succeed and the OOM killer fires later — the
allocation is not the failure point.**
